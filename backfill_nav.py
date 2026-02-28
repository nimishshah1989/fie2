"""
Backfill Historical NAV — Jhaveri Intelligence Platform
Computes and stores daily NAV for both model portfolios from inception to today.
Uses Yahoo Finance via curl (bypasses Python LibreSSL issues) for historical
prices, forward-fills missing days, and stores one PortfolioNAV row per
(portfolio_id, date).

Usage:
    cd /Users/nimishshah/Downloads/tradingviewalerts
    python3 backfill_nav.py
"""

import os
import sys
import json
import subprocess
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# Ensure working directory is the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from models import SessionLocal, IndexPrice
from portfolio_models import (
    ModelPortfolio, PortfolioHolding, PortfolioTransaction,
    PortfolioNAV, TransactionType, init_portfolio_db
)


# ─── Configuration ─────────────────────────────────────────────

PORTFOLIO_INCEPTION = {
    1: "2021-08-02",  # PASSIVE PORTFOLIO
    2: "2020-09-28",  # MOMENTUM LEADERS
}

# Portfolio ticker -> Yahoo Finance symbol mapping
YAHOO_SYMBOL_MAP = {
    # ETFs
    "NIFTYBEES": "NIFTYBEES.NS",
    "GOLDBEES": "GOLDBEES.NS",
    "BANKBEES": "BANKBEES.NS",
    "LIQUIDCASE": "LIQUIDBEES.NS",
    "CPSEETF": "CPSEETF.NS",
    "METALETF": "METALIETF.NS",
    "SENSEXETF": "SENSEXETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "NETFMID150.NS",
    "GROWWDEFNC": None,             # Recently listed, skip
    "FMCGIETF": "FMCGIETF.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "HNGSNGBEES": "HNGSNGBEES.NS",
    "PSUBNKBEES": "PSUBNKBEES.NS",
    "SILVERBEES": "SILVERBEES.NS",
    "INFRABEES": "INFRABEES.NS",
    "PHARMABEES": "PHARMABEES.NS",
    "OIL ETF": "OILIETF.NS",
    "NIPPONAMC - NETFAUTO": "NETFAUTO.NS",
    # Stocks (default .NS suffix works for all)
}

# NIFTY 50 symbol on Yahoo Finance
NIFTY_YAHOO_SYMBOL = "%5ENSEI"


def get_yahoo_symbol(ticker):
    """Map a portfolio ticker to its Yahoo Finance symbol."""
    if ticker in YAHOO_SYMBOL_MAP:
        return YAHOO_SYMBOL_MAP[ticker]
    # Default: append .NS for NSE tickers
    return f"{ticker}.NS"


# ─── Step 1: Fetch Prices via curl + Yahoo Finance ─────────────

def _date_to_unix(date_str):
    """Convert YYYY-MM-DD to Unix timestamp."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def fetch_yahoo_history_curl(yf_symbol, start_date, end_date):
    """
    Fetch daily close prices from Yahoo Finance using curl (not Python requests).
    This bypasses Python's LibreSSL 2.8.3 SSL issues on macOS.
    Returns: {date_str: close_price} dict
    """
    period1 = _date_to_unix(start_date)
    period2 = _date_to_unix(end_date) + 86400  # include end date

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_symbol}"
        f"?period1={period1}&period2={period2}&interval=1d"
    )

    try:
        result = subprocess.run(
            ["curl", "-s", url, "-H", "User-Agent: Mozilla/5.0"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {}

        data = json.loads(result.stdout)
        chart_result = data.get("chart", {}).get("result", [])
        if not chart_result:
            return {}

        timestamps = chart_result[0].get("timestamp", [])
        quotes = chart_result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = quotes.get("close", [])

        prices = {}
        for ts, close in zip(timestamps, closes):
            if close is not None:
                dt_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                prices[dt_str] = round(float(close), 2)

        return prices

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
        return {}


def fetch_all_prices(tickers, start_date, end_date):
    """
    Fetch daily close prices for all tickers via Yahoo Finance (curl).
    Returns: {ticker: {date_str: close_price}}
    """
    prices = {}

    fetch_list = []
    for ticker in sorted(tickers):
        yf_sym = get_yahoo_symbol(ticker)
        if yf_sym is None:
            print(f"  [SKIP] {ticker} — no Yahoo symbol, will use cost basis")
            continue
        fetch_list.append((ticker, yf_sym))

    for idx, (ticker, yf_sym) in enumerate(fetch_list, 1):
        print(f"  [{idx}/{len(fetch_list)}] Fetching {ticker} ({yf_sym}) ...", end=" ", flush=True)

        price_dict = fetch_yahoo_history_curl(yf_sym, start_date, end_date)

        if price_dict:
            prices[ticker] = price_dict
            print(f"{len(price_dict)} days")
        else:
            print("NO DATA")

    return prices


# ─── Step 2: Build Transaction Timeline ───────────────────────

class PositionTracker:
    """
    Tracks running positions for a portfolio by replaying transactions.
    For tickers with SELL-only records (no BUY), infers initial position
    from the sell's cost_basis_at_sell and quantity.
    """

    def __init__(self, portfolio_id, db_session):
        self.portfolio_id = portfolio_id
        self.db = db_session
        self.positions = {}

        self.transactions = (
            self.db.query(PortfolioTransaction)
            .filter(PortfolioTransaction.portfolio_id == portfolio_id)
            .order_by(PortfolioTransaction.txn_date)
            .all()
        )

        self._infer_initial_positions()
        self._txn_idx = 0
        self.realized_pnl_cumulative = 0.0

    def _infer_initial_positions(self):
        """Infer initial positions for tickers with SELL-only transactions."""
        buy_qty = defaultdict(int)
        buy_cost = defaultdict(float)
        sell_qty = defaultdict(int)
        sell_cost = defaultdict(float)

        for txn in self.transactions:
            if txn.txn_type == TransactionType.BUY:
                buy_qty[txn.ticker] += txn.quantity
                buy_cost[txn.ticker] += txn.total_value
            else:
                sell_qty[txn.ticker] += txn.quantity
                if txn.cost_basis_at_sell is not None:
                    sell_cost[txn.ticker] += txn.cost_basis_at_sell

        all_tickers = set(list(buy_qty.keys()) + list(sell_qty.keys()))
        for ticker in all_tickers:
            total_sell = sell_qty.get(ticker, 0)
            total_buy = buy_qty.get(ticker, 0)

            if total_sell > total_buy:
                excess_qty = total_sell - total_buy
                total_sell_cost_basis = sell_cost.get(ticker, 0.0)
                avg_cost_per_share = (
                    total_sell_cost_basis / total_sell
                    if total_sell_cost_basis > 0 and total_sell > 0
                    else 0.0
                )
                inferred_cost = avg_cost_per_share * excess_qty
                self.positions[ticker] = {
                    "quantity": excess_qty,
                    "total_cost": inferred_cost,
                }
                print(
                    f"    [INFERRED] {ticker}: {excess_qty} shares @ "
                    f"avg {avg_cost_per_share:.2f} — portfolio {self.portfolio_id}"
                )

            elif total_sell > 0 and total_buy == 0:
                total_sell_cost_basis = sell_cost.get(ticker, 0.0)
                avg_cost = (
                    total_sell_cost_basis / total_sell
                    if total_sell_cost_basis > 0 and total_sell > 0
                    else 0.0
                )
                inferred_cost = avg_cost * total_sell
                self.positions[ticker] = {
                    "quantity": total_sell,
                    "total_cost": inferred_cost,
                }
                print(
                    f"    [INFERRED] {ticker}: {total_sell} shares @ "
                    f"avg {avg_cost:.2f} — portfolio {self.portfolio_id}"
                )

    def apply_transactions_up_to(self, target_date):
        """Apply all transactions with txn_date <= target_date."""
        while self._txn_idx < len(self.transactions):
            txn = self.transactions[self._txn_idx]
            if txn.txn_date > target_date:
                break

            ticker = txn.ticker
            if ticker not in self.positions:
                self.positions[ticker] = {"quantity": 0, "total_cost": 0.0}

            pos = self.positions[ticker]

            if txn.txn_type == TransactionType.BUY:
                pos["quantity"] += txn.quantity
                pos["total_cost"] += txn.total_value
            else:
                if pos["quantity"] > 0:
                    avg_cost = pos["total_cost"] / pos["quantity"]
                    cost_of_sold = avg_cost * txn.quantity
                    pos["quantity"] -= txn.quantity
                    pos["total_cost"] -= cost_of_sold

                    if txn.realized_pnl is not None:
                        self.realized_pnl_cumulative += txn.realized_pnl
                    else:
                        self.realized_pnl_cumulative += txn.total_value - cost_of_sold
                else:
                    pos["quantity"] -= txn.quantity
                    if txn.realized_pnl is not None:
                        self.realized_pnl_cumulative += txn.realized_pnl

                if pos["quantity"] <= 0:
                    pos["quantity"] = 0
                    pos["total_cost"] = 0.0

            self._txn_idx += 1

    def get_snapshot(self, prices, target_date, last_known_prices):
        """
        Calculate portfolio value on a given date.
        prices: {ticker: {date_str: close_price}}
        Returns: (total_value, total_cost, num_holdings, updated_last_known_prices)
        """
        total_value = 0.0
        total_cost = 0.0
        num_holdings = 0

        for ticker, pos in self.positions.items():
            qty = pos["quantity"]
            if qty <= 0:
                continue

            num_holdings += 1
            total_cost += pos["total_cost"]

            # Look up price for this date
            price = None
            if ticker in prices:
                price_dict = prices[ticker]
                if target_date in price_dict:
                    price = price_dict[target_date]
                    last_known_prices[ticker] = price

            # Forward-fill: use last known price if no price on this date
            if price is None:
                price = last_known_prices.get(ticker)

            if price is not None:
                total_value += qty * price
            else:
                # No price at all yet — use cost basis as estimate
                if pos["total_cost"] > 0 and qty > 0:
                    total_value += pos["total_cost"]

        return total_value, total_cost, num_holdings, last_known_prices


# ─── Step 3: Fetch NIFTY 50 Index ─────────────────────────────

def fetch_nifty_index(start_date, end_date):
    """Fetch NIFTY 50 daily close via Yahoo Finance (curl)."""
    print("\n  Fetching NIFTY 50 (^NSEI) via curl ...", end=" ", flush=True)
    nifty_dict = fetch_yahoo_history_curl(NIFTY_YAHOO_SYMBOL, start_date, end_date)
    if nifty_dict:
        print(f"{len(nifty_dict)} days")
    else:
        print("NO DATA")
    return nifty_dict


# ─── Step 4: Store Results ─────────────────────────────────────

def store_nav_history(db, portfolio_id, nav_rows):
    """Delete existing NAV rows for this portfolio and insert fresh ones."""
    deleted = (
        db.query(PortfolioNAV)
        .filter(PortfolioNAV.portfolio_id == portfolio_id)
        .delete()
    )
    print(f"  Deleted {deleted} existing NAV rows for portfolio {portfolio_id}")

    batch_size = 500
    for i in range(0, len(nav_rows), batch_size):
        batch = nav_rows[i : i + batch_size]
        for row in batch:
            nav = PortfolioNAV(
                portfolio_id=portfolio_id,
                date=row["date"],
                total_value=row["total_value"],
                total_cost=row["total_cost"],
                unrealized_pnl=row["unrealized_pnl"],
                realized_pnl_cumulative=row["realized_pnl_cumulative"],
                num_holdings=row["num_holdings"],
            )
            db.add(nav)
        db.flush()

    db.commit()
    print(f"  Inserted {len(nav_rows)} NAV rows for portfolio {portfolio_id}")


def store_index_prices(db, nifty_dict):
    """Store NIFTY 50 daily prices in the IndexPrice table."""
    deleted = (
        db.query(IndexPrice)
        .filter(IndexPrice.index_name == "NIFTY")
        .delete()
    )
    print(f"  Deleted {deleted} existing NIFTY index rows")

    count = 0
    batch_size = 500
    dates = sorted(nifty_dict.keys())
    for i in range(0, len(dates), batch_size):
        batch_dates = dates[i : i + batch_size]
        for d in batch_dates:
            row = IndexPrice(
                date=d,
                index_name="NIFTY",
                close_price=nifty_dict[d],
            )
            db.add(row)
            count += 1
        db.flush()

    db.commit()
    print(f"  Inserted {count} NIFTY index rows")


# ─── Main ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Backfill Historical NAV — Yahoo Finance via curl")
    print("=" * 60)

    init_portfolio_db()
    db = SessionLocal()

    try:
        # ── Load portfolios ──
        portfolios = db.query(ModelPortfolio).all()
        print(f"\nFound {len(portfolios)} portfolios:")
        for p in portfolios:
            inception = PORTFOLIO_INCEPTION.get(p.id, "unknown")
            print(f"  [{p.id}] {p.name} — inception {inception}")

        # ── Collect all unique tickers ──
        all_tickers = set()
        for h in db.query(PortfolioHolding).all():
            all_tickers.add(h.ticker)
        for t in db.query(PortfolioTransaction).all():
            all_tickers.add(t.ticker)

        print(f"\nTotal unique tickers: {len(all_tickers)}")
        for t in sorted(all_tickers):
            sym = get_yahoo_symbol(t)
            print(f"  {t} -> {sym if sym else 'SKIP'}")

        # ── Determine date range ──
        earliest_inception = min(PORTFOLIO_INCEPTION.values())
        today_str = date.today().strftime("%Y-%m-%d")
        print(f"\nDate range: {earliest_inception} to {today_str}")

        # ── Step 1: Fetch historical prices ──
        print("\n" + "\u2500" * 40)
        print("STEP 1: Fetching historical prices via Yahoo Finance (curl)")
        print("\u2500" * 40)

        prices = fetch_all_prices(
            tickers=all_tickers,
            start_date=earliest_inception,
            end_date=today_str,
        )
        print(f"\nSuccessfully fetched prices for {len(prices)} / {len(all_tickers)} tickers")

        for ticker in sorted(all_tickers):
            if ticker in prices:
                num_days = len(prices[ticker])
                dates = sorted(prices[ticker].keys())
                print(f"  {ticker}: {num_days} days ({dates[0]} to {dates[-1]})")
            else:
                print(f"  {ticker}: NO DATA (will use cost basis)")

        # ── Step 2: Fetch NIFTY 50 ──
        print("\n" + "\u2500" * 40)
        print("STEP 2: Fetching NIFTY 50 index data")
        print("\u2500" * 40)

        nifty_dict = fetch_nifty_index(
            start_date=earliest_inception,
            end_date=today_str,
        )

        if nifty_dict:
            trading_days = sorted(nifty_dict.keys())
        else:
            print("WARNING: No NIFTY data. Using all weekdays as trading days.")
            trading_days = []
            d = datetime.strptime(earliest_inception, "%Y-%m-%d").date()
            end_d = date.today()
            while d <= end_d:
                if d.weekday() < 5:
                    trading_days.append(d.strftime("%Y-%m-%d"))
                d += timedelta(days=1)

        print(f"Trading days in range: {len(trading_days)}")

        # ── Step 3: Compute daily NAV for each portfolio ──
        print("\n" + "\u2500" * 40)
        print("STEP 3: Computing daily NAV for each portfolio")
        print("\u2500" * 40)

        all_nav_rows = {}

        for portfolio in portfolios:
            pid = portfolio.id
            inception = PORTFOLIO_INCEPTION.get(pid)
            if inception is None:
                print(f"\n  [SKIP] Portfolio {pid} ({portfolio.name})")
                continue

            print(f"\n  Computing NAV for [{pid}] {portfolio.name} (inception: {inception})")
            tracker = PositionTracker(pid, db)

            portfolio_days = [d for d in trading_days if d >= inception]
            print(f"  Trading days for this portfolio: {len(portfolio_days)}")

            nav_rows = []
            last_known_prices = {}

            for day_idx, day in enumerate(portfolio_days):
                tracker.apply_transactions_up_to(day)

                total_value, total_cost, num_holdings, last_known_prices = (
                    tracker.get_snapshot(prices, day, last_known_prices)
                )

                unrealized_pnl = total_value - total_cost

                nav_rows.append({
                    "date": day,
                    "total_value": round(total_value, 2),
                    "total_cost": round(total_cost, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "realized_pnl_cumulative": round(tracker.realized_pnl_cumulative, 2),
                    "num_holdings": num_holdings,
                })

                if (day_idx + 1) % 250 == 0:
                    print(
                        f"    ... {day_idx + 1}/{len(portfolio_days)} days "
                        f"({day}) — value: {total_value:,.0f}, "
                        f"cost: {total_cost:,.0f}, "
                        f"holdings: {num_holdings}"
                    )

            if nav_rows:
                last = nav_rows[-1]
                print(
                    f"  Final day ({last['date']}): "
                    f"value={last['total_value']:,.0f}, "
                    f"cost={last['total_cost']:,.0f}, "
                    f"unrealized={last['unrealized_pnl']:,.0f}, "
                    f"realized={last['realized_pnl_cumulative']:,.0f}, "
                    f"holdings={last['num_holdings']}"
                )

            all_nav_rows[pid] = nav_rows

        # ── Step 4: Store results ──
        print("\n" + "\u2500" * 40)
        print("STEP 4: Storing NAV history and index data")
        print("\u2500" * 40)

        for pid, nav_rows in all_nav_rows.items():
            print(f"\n  Portfolio {pid}:")
            store_nav_history(db, pid, nav_rows)

        if nifty_dict:
            print(f"\n  NIFTY 50 index:")
            store_index_prices(db, nifty_dict)

        print("\n" + "=" * 60)
        print("DONE — Backfill complete!")
        total_nav = sum(len(rows) for rows in all_nav_rows.values())
        print(f"  Total NAV rows stored: {total_nav}")
        print(f"  NIFTY index rows stored: {len(nifty_dict)}")
        print("=" * 60)

    except Exception as exc:
        db.rollback()
        print(f"\n[FATAL ERROR] {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
