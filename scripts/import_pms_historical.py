"""
FIE v3 — Import PMS Historical Data
One-time script to import BJ53 NAV + transaction data from Excel files.

Usage:
    python3 scripts/import_pms_historical.py

Reads files from project root:
    - BJ53-NAV report[1].xlsx
    - BJ53-Transaction.xlsx
"""

import os
import sys
from pathlib import Path

# Add parent dir to path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import init_db, SessionLocal, ModelPortfolio, PmsNavDaily, PmsTransaction
from services.pms_service import (
    parse_nav_excel, parse_transaction_excel,
    recalculate_portfolio_metrics, detect_drawdown_events,
)

PROJECT_ROOT = Path(__file__).parent.parent

# Portfolio configurations — each entry maps to a file set
PORTFOLIOS = [
    {
        'name': 'Multi Asset Alpha - Leaders',
        'old_name': 'Momentum Leaders',
        'ucc_code': 'BJ53',
        'inception_date': '2020-09-28',
        'description': 'PMS Equity — Multi Asset Alpha Leaders strategy',
        'nav_file': PROJECT_ROOT / "BJ53-NAV report[1].xlsx",
        'txn_file': PROJECT_ROOT / "BJ53-Transaction.xlsx",
    },
    {
        'name': 'Multi Asset Alpha - Passive',
        'old_name': 'Momentum Passive',
        'ucc_code': 'BJ53MF',
        'inception_date': '2021-05-02',
        'description': 'PMS Equity — Multi Asset Alpha Passive strategy',
        'nav_file': PROJECT_ROOT / "BJ53-NAV report[1].xlsx",
        'txn_file': PROJECT_ROOT / "BJ53-Transaction.xlsx",
    },
    {
        'name': 'Multi Asset Alpha - Passive (JR100)',
        'ucc_code': 'JR100PASS',
        'inception_date': '2021-08-02',
        'description': 'PMS Passive — JR100 ETF-based strategy',
        'nav_file': PROJECT_ROOT / "JR100-NAV report.xlsx",
        'txn_file': PROJECT_ROOT / "JR100-Transaction.xlsx",
    },
]


def _safe(val):
    """Convert NaN/None to None for DB storage."""
    if val is None:
        return None
    import math
    if isinstance(val, float) and math.isnan(val):
        return None
    return val


def main():
    print("Initializing database...")
    init_db()
    db = SessionLocal()

    try:
        for config in PORTFOLIOS:
            nav_file = config['nav_file']
            txn_file = config['txn_file']

            if not nav_file.exists():
                print(f"SKIP: NAV file not found: {nav_file}")
                continue

            nav_bytes = nav_file.read_bytes()
            txn_bytes = txn_file.read_bytes() if txn_file.exists() else None

            print(f"\n{'='*60}")
            print(f"Processing: {config['name']} (UCC: {config['ucc_code']})")
            print(f"{'='*60}")

            # Find by old name (for renaming) or current name
            portfolio = (
                db.query(ModelPortfolio)
                .filter(ModelPortfolio.name == config['name'])
                .first()
            )
            if not portfolio and config.get('old_name'):
                portfolio = (
                    db.query(ModelPortfolio)
                    .filter(ModelPortfolio.name == config['old_name'])
                    .first()
                )
                if portfolio:
                    print(f"  Renaming '{config['old_name']}' → '{config['name']}'")

            if not portfolio:
                portfolio = ModelPortfolio(
                    name=config['name'],
                    description=config['description'],
                    benchmark='NIFTY',
                    portfolio_type='pms',
                    ucc_code=config['ucc_code'],
                    inception_date=config['inception_date'],
                )
                db.add(portfolio)
                db.commit()
                db.refresh(portfolio)
                print(f"  Created portfolio ID {portfolio.id}")
            else:
                # Update fields
                portfolio.name = config['name']
                portfolio.description = config['description']
                portfolio.portfolio_type = 'pms'
                portfolio.ucc_code = config['ucc_code']
                if not portfolio.inception_date:
                    portfolio.inception_date = config['inception_date']
                db.commit()
                print(f"  Updated existing portfolio ID {portfolio.id}")

            # Import NAV data
            print(f"  Parsing NAV data for UCC {config['ucc_code']}...")
            try:
                nav_df = parse_nav_excel(nav_bytes, config['ucc_code'])
                print(f"  Parsed {len(nav_df)} NAV records ({nav_df['date'].iloc[0]} to {nav_df['date'].iloc[-1]})")

                # Check existing records
                existing_count = db.query(PmsNavDaily).filter(
                    PmsNavDaily.portfolio_id == portfolio.id
                ).count()
                print(f"  Existing NAV records: {existing_count}")

                existing_dates = set(
                    r[0] for r in db.query(PmsNavDaily.date)
                    .filter(PmsNavDaily.portfolio_id == portfolio.id).all()
                )

                new_count = 0
                for _, row in nav_df.iterrows():
                    if row['date'] in existing_dates:
                        continue
                    db.add(PmsNavDaily(
                        portfolio_id=portfolio.id,
                        date=row['date'],
                        corpus=_safe(row.get('corpus')),
                        equity_holding=_safe(row.get('equity_holding')),
                        etf_investment=_safe(row.get('etf_investment')),
                        cash_equivalent=_safe(row.get('cash_equivalent')),
                        bank_balance=_safe(row.get('bank_balance')),
                        nav=row['nav'],
                        liquidity_pct=_safe(row.get('liquidity_pct')),
                        high_water_mark=_safe(row.get('high_water_mark')),
                    ))
                    new_count += 1
                db.commit()
                print(f"  Inserted {new_count} new NAV records")
            except Exception as e:
                print(f"  ERROR parsing NAV: {e}")
                continue

            # Import transactions
            if txn_bytes:
                print(f"  Parsing transactions for UCC {config['ucc_code']}...")
                try:
                    txn_df = parse_transaction_excel(txn_bytes, config['ucc_code'])
                    print(f"  Parsed {len(txn_df)} transactions")

                    # Delete existing and re-insert
                    deleted = db.query(PmsTransaction).filter(
                        PmsTransaction.portfolio_id == portfolio.id
                    ).delete()
                    if deleted:
                        print(f"  Deleted {deleted} existing transactions")

                    for _, row in txn_df.iterrows():
                        db.add(PmsTransaction(
                            portfolio_id=portfolio.id,
                            date=row['date'],
                            script=row['script'],
                            exchange=row.get('exchange', ''),
                            stno=row.get('stno', ''),
                            buy_qty=_safe(row.get('buy_qty')),
                            buy_rate=_safe(row.get('buy_rate')),
                            buy_gst=_safe(row.get('buy_gst')),
                            buy_other_charges=_safe(row.get('buy_other_charges')),
                            buy_stt=_safe(row.get('buy_stt')),
                            buy_cost_rate=_safe(row.get('buy_cost_rate')),
                            buy_amt_with_cost=_safe(row.get('buy_amt_with_cost')),
                            buy_amt_without_stt=_safe(row.get('buy_amt_without_stt')),
                            sale_qty=_safe(row.get('sale_qty')),
                            sale_rate=_safe(row.get('sale_rate')),
                            sale_gst=_safe(row.get('sale_gst')),
                            sale_stt=_safe(row.get('sale_stt')),
                            sale_other_charges=_safe(row.get('sale_other_charges')),
                            sale_cost_rate=_safe(row.get('sale_cost_rate')),
                            sale_amt_with_cost=_safe(row.get('sale_amt_with_cost')),
                            sale_amt_without_stt=_safe(row.get('sale_amt_without_stt')),
                        ))
                    db.commit()
                    print(f"  Inserted {len(txn_df)} transactions")
                except Exception as e:
                    print(f"  ERROR parsing transactions: {e}")

            # Recalculate metrics
            print(f"  Calculating risk/return metrics...")
            try:
                metric_count = recalculate_portfolio_metrics(portfolio.id, db)
                print(f"  Stored {metric_count} period metrics")
            except Exception as e:
                print(f"  ERROR calculating metrics: {e}")

            # Detect drawdowns
            print(f"  Detecting drawdown events...")
            try:
                dd_count = detect_drawdown_events(portfolio.id, db)
                print(f"  Detected {dd_count} drawdown events")
            except Exception as e:
                print(f"  ERROR detecting drawdowns: {e}")

        print(f"\n{'='*60}")
        print("Import complete!")
        print(f"{'='*60}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
