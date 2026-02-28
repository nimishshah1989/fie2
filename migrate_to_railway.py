#!/usr/bin/env python3
"""
Migrate portfolio data from local SQLite to Railway production.
Reads all portfolio data from local DB, packages as JSON, and POSTs to the
bulk-import endpoint on Railway.

Usage:
    python3 migrate_to_railway.py
    python3 migrate_to_railway.py https://your-app.railway.app
"""

import sys
import json
import subprocess

from models import (
    SessionLocal, IndexPrice,
    ModelPortfolio, PortfolioHolding, PortfolioTransaction, PortfolioNAV,
    PortfolioStatus,
)

TARGET = sys.argv[1] if len(sys.argv) > 1 else "https://fie2-production.up.railway.app"


def post_json(path, data):
    """POST JSON to target API via curl."""
    payload = json.dumps(data)
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{TARGET}{path}",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True, timeout=120
    )
    return json.loads(result.stdout) if result.stdout else {"error": result.stderr}


def main():
    db = SessionLocal()

    portfolios = (
        db.query(ModelPortfolio)
        .filter(ModelPortfolio.status == PortfolioStatus.ACTIVE)
        .all()
    )

    # Collect all stock ticker names that have index prices (for NAV computation)
    stock_tickers = set()

    for p in portfolios:
        print(f"\n{'='*60}")
        print(f"  Migrating: {p.name}")
        print(f"{'='*60}")

        # Holdings
        holdings = (
            db.query(PortfolioHolding)
            .filter(PortfolioHolding.portfolio_id == p.id)
            .all()
        )
        holdings_data = [{
            "ticker": h.ticker, "exchange": h.exchange or "NSE",
            "quantity": h.quantity, "avg_cost": h.avg_cost,
            "total_cost": h.total_cost, "sector": h.sector,
        } for h in holdings]
        print(f"  Holdings: {len(holdings_data)}")

        # Collect tickers for stock price export
        for h in holdings:
            stock_tickers.add(h.ticker)

        # Transactions
        txns = (
            db.query(PortfolioTransaction)
            .filter(PortfolioTransaction.portfolio_id == p.id)
            .all()
        )
        txns_data = [{
            "ticker": t.ticker, "exchange": t.exchange or "NSE",
            "txn_type": t.txn_type.value if t.txn_type else "BUY",
            "quantity": t.quantity, "price": t.price,
            "total_value": t.total_value, "txn_date": t.txn_date,
            "notes": t.notes,
            "realized_pnl": t.realized_pnl,
            "realized_pnl_pct": t.realized_pnl_pct,
            "cost_basis_at_sell": t.cost_basis_at_sell,
        } for t in txns]
        print(f"  Transactions: {len(txns_data)}")

        # NAV History
        navs = (
            db.query(PortfolioNAV)
            .filter(PortfolioNAV.portfolio_id == p.id)
            .order_by(PortfolioNAV.date)
            .all()
        )
        nav_data = [{
            "date": n.date, "total_value": n.total_value,
            "total_cost": n.total_cost, "unrealized_pnl": n.unrealized_pnl,
            "realized_pnl_cumulative": n.realized_pnl_cumulative,
            "num_holdings": n.num_holdings,
        } for n in navs]
        print(f"  NAV rows: {len(nav_data)}")

        # Index prices: NIFTY benchmark + all stock prices for this portfolio's tickers
        tickers_for_this = [h.ticker for h in holdings]
        index_names = ["NIFTY"] + tickers_for_this
        idx_prices = (
            db.query(IndexPrice)
            .filter(IndexPrice.index_name.in_(index_names))
            .all()
        )
        idx_data = [{
            "date": ip.date, "index_name": ip.index_name,
            "close_price": ip.close_price, "open_price": ip.open_price,
            "high_price": ip.high_price, "low_price": ip.low_price,
            "volume": ip.volume,
        } for ip in idx_prices]
        print(f"  Index price rows: {len(idx_data)}")

        # POST everything
        payload = {
            "portfolio": {
                "name": p.name,
                "description": p.description,
                "benchmark": p.benchmark,
            },
            "holdings": holdings_data,
            "transactions": txns_data,
            "nav_history": nav_data,
            "index_prices": idx_data,
        }

        payload_size = len(json.dumps(payload))
        print(f"  Payload size: {payload_size:,} bytes")
        print(f"  Posting to {TARGET}...")

        result = post_json("/api/portfolios/bulk-import", payload)
        print(f"  Result: {json.dumps(result, indent=2)}")

    db.close()
    print(f"\n{'='*60}")
    print("  Migration complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
