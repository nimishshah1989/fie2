"""
Import PMS Portfolio Statements from HTML into SQLite.
Parses Jhaveri Securities portfolio statement HTML files and populates
the portfolio tables (ModelPortfolio, PortfolioHolding, PortfolioTransaction, PortfolioNAV).

Usage:
    python3 import_portfolios.py
"""

import re
import sys
import os
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

# Ensure the script runs from its own directory so relative imports work
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from portfolio_models import (
    ModelPortfolio, PortfolioHolding, PortfolioTransaction, PortfolioNAV,
    PortfolioStatus, TransactionType, init_portfolio_db
)
from models import SessionLocal


# ─── Constants ────────────────────────────────────────────────

HTML_FILES = [
    {
        "path": "/Users/nimishshah/Downloads/PORTFOLIOSUM__JR100PASS_PMS_20260222.htm",
        "benchmark": "NIFTY",
    },
    {
        "path": "/Users/nimishshah/Downloads/PORTFOLIOSUM__BJ53_PMS_20260222.htm",
        "benchmark": "NIFTY",
    },
]

STATEMENT_DATE = "2026-02-20"  # 20th February 2026

# Mapping: raw HTML name -> (NSE ticker, sector)
SECTOR_MAP = {
    "GOLDBEES": "Commodities",
    "SILVERBEES": "Commodities",
    "NIFTYBEES": "Index",
    "JUNIORBEES": "Index",
    "BANKBEES": "Banking",
    "PSUBNKBEES": "Banking",
    "HNGSNGBEES": "Banking",
    "CPSEETF": "PSU",
    "FMCGIETF": "FMCG",
    "LIQUIDCASE": "Liquid",
    "PHARMABEES": "Pharma",
    # Equity stocks — sector from context
    "LUPIN": "Pharma",
    "NTPC": "Power",
    "OIL": "Oil & Gas",
    "ONGC": "Oil & Gas",
    "PFC": "Power",
    "SUNDARMFIN": "Finance",
    "TATASTEEL": "Metals",
    "UNIONBANK": "Banking",
}

# Special name mappings where the HTML name doesn't trivially map to an NSE ticker
TICKER_OVERRIDES = {
    "ICICI Prudential BSE Sensex ET": ("SENSEXETF", "Index"),
    "NIPPON INDIA ETF NIFTY MIDCAP 150": ("NETFMID150", "Smallcap/Midcap"),
    "Mirae Smallcap ETF": ("MASPTOP50", "Smallcap/Midcap"),
    "Metal ETF": ("METALETF", "Commodities"),
    "GROWWAMC - GROWWDEFNC": ("GROWWDEFNC", "Defence"),
    "INDUS TOWERS LIMITED": ("INDUSTOWER", "Telecom"),
}


# ─── Helpers ──────────────────────────────────────────────────

def parse_indian_number(text: str) -> float:
    """Parse an Indian-formatted number string like '3,53,93,069.15' into a float.
    Handles negative values in parentheses or with a minus sign.
    Returns 0.0 for empty/whitespace strings.
    """
    if text is None:
        return 0.0
    cleaned = text.strip().replace("\xa0", "").replace("&nbsp;", "").replace("%", "").strip()
    if not cleaned:
        return 0.0
    # Handle display artefacts like "****.**"
    if "*" in cleaned:
        return 0.0
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith("-"):
        negative = True
        cleaned = cleaned[1:].strip()
    # Remove all commas (Indian number system: 1,00,000 = 100000)
    cleaned = cleaned.replace(",", "")
    if not cleaned:
        return 0.0
    try:
        value = float(cleaned)
    except ValueError:
        return 0.0
    return -value if negative else value


def clean_name(raw_name: str) -> str:
    """Strip whitespace, &nbsp;, and leading/trailing spaces from an HTML holding name."""
    name = raw_name.strip().replace("\xa0", " ").strip()
    # Remove trailing " EQ" suffix (with possible extra spaces)
    name = re.sub(r'\s+EQ$', '', name).strip()
    return name


def resolve_ticker_and_sector(clean_holding_name: str) -> tuple:
    """Given a cleaned holding name, return (nse_ticker, sector).
    Uses TICKER_OVERRIDES for special names, then falls back to
    uppercasing the name and looking up SECTOR_MAP.
    """
    # Check overrides first (case-sensitive match for known special names)
    if clean_holding_name in TICKER_OVERRIDES:
        return TICKER_OVERRIDES[clean_holding_name]

    # Default: uppercase the clean name as ticker
    ticker = clean_holding_name.upper().strip()
    sector = SECTOR_MAP.get(ticker, "Other")
    return ticker, sector


def parse_inception_date(text: str) -> Optional[str]:
    """Parse inception date text like '2nd August,2021' or '28th September,2020'
    into ISO format YYYY-MM-DD.
    """
    text = text.strip()
    # Remove ordinal suffixes: 1st, 2nd, 3rd, 4th, etc.
    text = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', text)
    # Remove comma between month and year if present
    text = text.replace(",", " ").strip()
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    try:
        parsed = datetime.strptime(text, "%d %B %Y")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return None


# ─── HTML Parsing ─────────────────────────────────────────────

def extract_portfolio_data(html_path: str) -> dict:
    """Parse the HTML portfolio statement and return a structured dict."""
    with open(html_path, "r", encoding="iso-8859-1") as fh:
        soup = BeautifulSoup(fh, "html.parser")

    data = {
        "client_name": "",
        "strategy": "",
        "client_id": "",
        "inception_date": "",
        "equity_holdings": [],
        "etf_holdings": [],
        "investment_summary": {},
        "realized_gains": [],
        "nav_summary": {},
    }

    # --- Client Information ---
    info_table = None
    for tbl in soup.find_all("table"):
        cells = tbl.find_all("td")
        for cell in cells:
            if "Client Name" in (cell.get_text() or ""):
                info_table = tbl
                break
        if info_table:
            break

    if info_table:
        rows = info_table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            for idx, cell in enumerate(cells):
                txt = cell.get_text(strip=True)
                if "Client Name" in txt and idx + 1 < len(cells):
                    data["client_name"] = cells[idx + 1].get_text(strip=True)
                if "Strategy" in txt and idx + 1 < len(cells):
                    data["strategy"] = cells[idx + 1].get_text(strip=True)
                if "Client ID" in txt and idx + 1 < len(cells):
                    data["client_id"] = cells[idx + 1].get_text(strip=True)
                if "Inception Date" in txt and idx + 1 < len(cells):
                    data["inception_date"] = cells[idx + 1].get_text(strip=True)

    # --- Find captioned tables ---
    def find_table_by_caption(caption_text: str):
        """Find a <table> whose <caption> contains caption_text."""
        for tbl in soup.find_all("table"):
            cap = tbl.find("caption")
            if cap and caption_text.lower() in cap.get_text().lower():
                return tbl
        return None

    # --- Equity Holdings ---
    equity_table = find_table_by_caption("Equity Holdings as on")
    if equity_table:
        data["equity_holdings"] = parse_holdings_table(equity_table)

    # --- ETF Holdings ---
    etf_table = find_table_by_caption("ETF Holdings as on")
    if etf_table:
        data["etf_holdings"] = parse_holdings_table(etf_table)

    # --- Investment Summary (Since Inception) ---
    inv_table = find_table_by_caption("Investment Summary")
    if inv_table:
        data["investment_summary"] = parse_investment_summary(inv_table)

    # --- Net Asset Value ---
    nav_table = find_table_by_caption("Net Asset Value as on")
    if nav_table:
        data["nav_summary"] = parse_nav_summary(nav_table)

    # --- Realized Gain/Loss ---
    realized_table = find_table_by_caption("Realised Gain / Loss")
    if realized_table:
        data["realized_gains"] = parse_realized_gains(realized_table)

    return data


def parse_holdings_table(table) -> list:
    """Parse an Equity/ETF holdings table into a list of dicts."""
    holdings = []
    # Skip thead rows and tfoot rows
    thead = table.find("thead")
    tfoot = table.find("tfoot")

    for row in table.find_all("tr"):
        # Skip if row is inside thead or tfoot
        if thead and row in thead.find_all("tr"):
            continue
        if tfoot and row in tfoot.find_all("tr"):
            continue

        cells = row.find_all("td")
        # Holdings rows have 11 cells: serial, name, shares, avg_cost, avg_buy_value, cmp, current_value, gain_loss, return_pct, holding_pct, xirr_pct
        if len(cells) < 11:
            continue

        serial_text = cells[0].get_text(strip=True)
        # Skip total/summary rows
        if "total" in serial_text.lower():
            continue
        # Serial number should be a digit
        try:
            int(serial_text)
        except ValueError:
            continue

        name_raw = cells[1].get_text()
        name = clean_name(name_raw)
        ticker, sector = resolve_ticker_and_sector(name)

        holding = {
            "raw_name": name,
            "ticker": ticker,
            "sector": sector,
            "quantity": int(parse_indian_number(cells[2].get_text())),
            "avg_cost": parse_indian_number(cells[3].get_text()),
            "avg_buy_value": parse_indian_number(cells[4].get_text()),
            "cmp": parse_indian_number(cells[5].get_text()),
            "current_value": parse_indian_number(cells[6].get_text()),
            "gain_loss": parse_indian_number(cells[7].get_text()),
            "return_pct": parse_indian_number(cells[8].get_text()),
            "holding_pct": parse_indian_number(cells[9].get_text()),
            "xirr_pct": parse_indian_number(cells[10].get_text()),
        }
        holdings.append(holding)

    return holdings


def parse_investment_summary(table) -> dict:
    """Parse the Investment Summary table (Since Inception sub-table)."""
    summary = {}

    # The investment summary has nested tables. The first nested table
    # with caption containing "Since Inception" has the data we need.
    since_inception_table = None
    for sub_table in table.find_all("table"):
        cap = sub_table.find("caption")
        if cap and "since inception" in cap.get_text().lower():
            since_inception_table = sub_table
            break

    if not since_inception_table:
        # Fallback: just use the outer table
        since_inception_table = table

    for row in since_inception_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True).lower()
        value_text = cells[1].get_text(strip=True)

        if "starting corpus" in label:
            summary["starting_corpus"] = parse_indian_number(value_text)
        elif "further contribution" in label:
            summary["further_contribution"] = parse_indian_number(value_text)
        elif "corpus withdrawal" in label:
            summary["corpus_withdrawal"] = parse_indian_number(value_text)
        elif "net contribution" in label:
            summary["net_contribution"] = parse_indian_number(value_text)
        elif "average corpus" in label:
            summary["average_corpus"] = parse_indian_number(value_text)
        elif "current value" in label:
            summary["current_value"] = parse_indian_number(value_text)
        elif "absolute profit" in label or "absolute loss" in label:
            summary["absolute_profit"] = parse_indian_number(value_text)
        elif "xirr return" in label:
            summary["xirr_return"] = parse_indian_number(value_text)
        elif "absolute return %" in label and "nifty" not in label and "cnx" not in label and "bse" not in label:
            summary["absolute_return_pct"] = parse_indian_number(value_text)
        elif "adjusted return" in label:
            summary["adjusted_return_pct"] = parse_indian_number(value_text)

    return summary


def parse_nav_summary(table) -> dict:
    """Parse the NAV summary table for asset class breakdown."""
    nav = {}
    tfoot = table.find("tfoot")

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        label = cells[0].get_text(strip=True).lower()

        if "net asset value" in label:
            nav["total_nav"] = parse_indian_number(cells[4].get_text())
        elif "equity holdings" in label:
            nav["equity_value"] = parse_indian_number(cells[4].get_text())
            nav["equity_pct"] = parse_indian_number(cells[1].get_text())
        elif label == "etf":
            nav["etf_value"] = parse_indian_number(cells[4].get_text())
            nav["etf_pct"] = parse_indian_number(cells[1].get_text())
        elif "cash" in label and "equivalent" in label:
            nav["cash_value"] = parse_indian_number(cells[4].get_text())
            nav["cash_pct"] = parse_indian_number(cells[1].get_text())

    return nav


def parse_realized_gains(table) -> list:
    """Parse the Realised Gain/Loss table."""
    gains = []
    thead = table.find("thead")
    tfoot = table.find("tfoot")

    for row in table.find_all("tr"):
        if thead and row in thead.find_all("tr"):
            continue
        if tfoot and row in tfoot.find_all("tr"):
            continue

        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        name_text = cells[0].get_text(strip=True).lower()
        if "total" in name_text or not name_text:
            continue

        name = clean_name(cells[0].get_text())
        ticker, sector = resolve_ticker_and_sector(name)

        gain = {
            "raw_name": name,
            "ticker": ticker,
            "quantity": int(parse_indian_number(cells[1].get_text())),
            "buy_value": parse_indian_number(cells[2].get_text()),
            "sell_value": parse_indian_number(cells[3].get_text()),
            "gain_loss": parse_indian_number(cells[4].get_text()),
            "return_pct": parse_indian_number(cells[5].get_text()),
        }
        gains.append(gain)

    return gains


# ─── Database Operations ─────────────────────────────────────

def clear_portfolio_data(db):
    """Delete all existing portfolio data from all portfolio tables."""
    db.query(PortfolioNAV).delete()
    db.query(PortfolioTransaction).delete()
    db.query(PortfolioHolding).delete()
    db.query(ModelPortfolio).delete()
    db.commit()
    print("Cleared all existing portfolio data.")


def insert_portfolio(db, portfolio_data: dict, benchmark: str) -> int:
    """Insert a ModelPortfolio and all its holdings, transactions, NAV.
    Returns the new portfolio ID.
    """
    strategy = portfolio_data["strategy"]
    client_name = portfolio_data["client_name"]
    inception_date_raw = portfolio_data["inception_date"]
    inception_date_iso = parse_inception_date(inception_date_raw) or "2021-01-01"

    # Build description from client info
    description = f"Client: {client_name} | ID: {portfolio_data['client_id']} | Inception: {inception_date_raw}"

    # Create ModelPortfolio
    portfolio = ModelPortfolio(
        name=strategy,
        description=description,
        benchmark=benchmark,
        status=PortfolioStatus.ACTIVE,
        tenant_id="jhaveri",
    )
    db.add(portfolio)
    db.flush()  # get the ID
    portfolio_id = portfolio.id

    # Combine equity + ETF holdings
    all_holdings = portfolio_data["equity_holdings"] + portfolio_data["etf_holdings"]

    total_cost = 0.0
    total_current_value = 0.0
    holding_count = 0

    for holding_data in all_holdings:
        ticker = holding_data["ticker"]
        quantity = holding_data["quantity"]
        avg_cost = holding_data["avg_cost"]
        total_buy_value = holding_data["avg_buy_value"]
        sector = holding_data["sector"]

        # Create PortfolioHolding
        holding = PortfolioHolding(
            portfolio_id=portfolio_id,
            ticker=ticker,
            exchange="NSE",
            quantity=quantity,
            avg_cost=avg_cost,
            total_cost=total_buy_value,
            sector=sector,
        )
        db.add(holding)

        # Create a BUY transaction as the initial position record
        txn = PortfolioTransaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            exchange="NSE",
            txn_type=TransactionType.BUY,
            quantity=quantity,
            price=avg_cost,
            total_value=total_buy_value,
            txn_date=inception_date_iso,
            notes=f"Imported from PMS statement dated {STATEMENT_DATE}. Avg cost basis.",
        )
        db.add(txn)

        total_cost += total_buy_value
        total_current_value += holding_data["current_value"]
        holding_count += 1

    # Create SELL transactions for realized gains
    for realized in portfolio_data["realized_gains"]:
        ticker = realized["ticker"]
        sell_txn = PortfolioTransaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            exchange="NSE",
            txn_type=TransactionType.SELL,
            quantity=realized["quantity"],
            price=realized["sell_value"] / realized["quantity"] if realized["quantity"] > 0 else 0.0,
            total_value=realized["sell_value"],
            txn_date=STATEMENT_DATE,
            notes=f"Realized gain/loss from PMS statement. P&L: {realized['gain_loss']:.2f}",
            realized_pnl=realized["gain_loss"],
            realized_pnl_pct=realized["return_pct"],
            cost_basis_at_sell=realized["buy_value"],
        )
        db.add(sell_txn)

    # NAV entry for the statement date
    inv_summary = portfolio_data["investment_summary"]
    nav_total = inv_summary.get("current_value", total_current_value)
    nav_cost = inv_summary.get("net_contribution", total_cost)
    unrealized_pnl = nav_total - nav_cost if nav_total and nav_cost else total_current_value - total_cost

    # Compute realized P&L cumulative from realized gains
    realized_pnl_cumulative = sum(r["gain_loss"] for r in portfolio_data["realized_gains"])

    nav_entry = PortfolioNAV(
        portfolio_id=portfolio_id,
        date=STATEMENT_DATE,
        total_value=nav_total,
        total_cost=nav_cost,
        unrealized_pnl=unrealized_pnl,
        realized_pnl_cumulative=realized_pnl_cumulative,
        num_holdings=holding_count,
    )
    db.add(nav_entry)

    db.commit()
    return portfolio_id


# ─── Main ─────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("Portfolio Import — Jhaveri Intelligence Platform")
    print("=" * 70)
    print()

    # Ensure portfolio tables exist
    init_portfolio_db()

    db = SessionLocal()

    try:
        # Clear existing portfolio data
        clear_portfolio_data(db)

        total_holdings = 0
        total_transactions = 0

        for file_config in HTML_FILES:
            html_path = file_config["path"]
            benchmark = file_config["benchmark"]

            if not os.path.exists(html_path):
                print(f"WARNING: File not found: {html_path}")
                continue

            print(f"Parsing: {os.path.basename(html_path)}")
            portfolio_data = extract_portfolio_data(html_path)

            strategy = portfolio_data["strategy"]
            client = portfolio_data["client_name"]
            inception = portfolio_data["inception_date"]
            num_equity = len(portfolio_data["equity_holdings"])
            num_etf = len(portfolio_data["etf_holdings"])
            num_realized = len(portfolio_data["realized_gains"])

            print(f"  Strategy:  {strategy}")
            print(f"  Client:    {client}")
            print(f"  Inception: {inception}")
            print(f"  Equity holdings: {num_equity}")
            print(f"  ETF holdings:    {num_etf}")
            print(f"  Realized trades: {num_realized}")

            inv = portfolio_data["investment_summary"]
            if inv:
                current_val = inv.get("current_value", 0)
                net_contrib = inv.get("net_contribution", 0)
                xirr = inv.get("xirr_return", 0)
                print(f"  Net Contribution:  {net_contrib:>15,.2f}")
                print(f"  Current Value:     {current_val:>15,.2f}")
                print(f"  XIRR:              {xirr:>10.2f}%")

            portfolio_id = insert_portfolio(db, portfolio_data, benchmark)

            num_holdings_inserted = num_equity + num_etf
            # BUY for each holding + SELL for each realized trade
            num_txns_inserted = num_holdings_inserted + num_realized

            total_holdings += num_holdings_inserted
            total_transactions += num_txns_inserted

            print(f"  -> Inserted as portfolio ID {portfolio_id}")
            print(f"     {num_holdings_inserted} holdings, {num_txns_inserted} transactions, 1 NAV entry")
            print()

        # Final summary
        print("-" * 70)
        print("IMPORT SUMMARY")
        print("-" * 70)
        portfolios_count = db.query(ModelPortfolio).count()
        holdings_count = db.query(PortfolioHolding).count()
        txn_count = db.query(PortfolioTransaction).count()
        nav_count = db.query(PortfolioNAV).count()
        print(f"  Portfolios:    {portfolios_count}")
        print(f"  Holdings:      {holdings_count}")
        print(f"  Transactions:  {txn_count}")
        print(f"  NAV entries:   {nav_count}")
        print()

        # Print all holdings per portfolio
        for p in db.query(ModelPortfolio).all():
            print(f"  [{p.name}] Holdings:")
            for h in db.query(PortfolioHolding).filter_by(portfolio_id=p.id).order_by(PortfolioHolding.ticker).all():
                print(f"    {h.ticker:<20s}  Qty: {h.quantity:>8,}  AvgCost: {h.avg_cost:>10,.2f}  Total: {h.total_cost:>14,.2f}  Sector: {h.sector}")
            print()

        print("Import complete.")

    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
