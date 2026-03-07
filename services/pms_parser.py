"""
FIE v3 — PMS Excel Parser
Parsing for PMS NAV reports and transaction log Excel files from brokers.
"""

import logging
import re

import pandas as pd

logger = logging.getLogger("fie_v3.pms_parser")


def _clean_column_name(name: str) -> str:
    """Strip _x000D_\\n artifacts from Excel multi-line headers."""
    return re.sub(r'_x000D_\n|\r\n|\n', ' ', str(name)).strip()


def parse_nav_excel(file_bytes: bytes, ucc_code: str) -> pd.DataFrame:
    """Parse PMS NAV report Excel into clean DataFrame.

    Args:
        file_bytes: Raw .xlsx file contents
        ucc_code: UCC code to filter by (e.g. 'BJ53')

    Returns:
        DataFrame with columns: date, corpus, equity_holding, etf_investment,
        cash_equivalent, bank_balance, nav, liquidity_pct, high_water_mark
    """
    from io import BytesIO
    df = pd.read_excel(BytesIO(file_bytes), skiprows=0)

    # Clean column names (strip _x000D_\n artifacts)
    df.columns = [_clean_column_name(c) for c in df.columns]

    # Normalize column name mapping via keyword matching
    col_map: dict[str, str] = {}
    for col in df.columns:
        lower = col.lower()
        if 'ucc' in lower:
            col_map['ucc'] = col
        elif lower == 'date':
            col_map['date'] = col
        elif lower == 'corpus':
            col_map['corpus'] = col
        elif 'equity' in lower and 'hold' in lower:
            col_map['equity_holding'] = col
        elif 'etf' in lower and 'invest' in lower:
            col_map['etf_investment'] = col
        elif 'cash' in lower and 'equiv' in lower:
            col_map['cash_equivalent'] = col
        elif 'bank' in lower and 'bal' in lower:
            col_map['bank_balance'] = col
        elif lower == 'nav':
            col_map['nav'] = col
        elif 'liquidity' in lower:
            col_map['liquidity_pct'] = col
        elif 'water' in lower and 'mark' in lower:
            col_map['high_water_mark'] = col

    if 'ucc' not in col_map or 'nav' not in col_map:
        raise ValueError("Missing required columns: UCC and NAV")

    # Filter by UCC code (strip trailing spaces)
    df['_ucc_clean'] = df[col_map['ucc']].astype(str).str.strip()
    df = df[df['_ucc_clean'] == ucc_code.strip()].copy()

    if df.empty:
        raise ValueError(f"No data found for UCC code '{ucc_code}'")

    # Parse dates
    df['date'] = pd.to_datetime(df[col_map['date']], format='%d-%b-%Y', errors='coerce')
    df = df.dropna(subset=['date'])

    def _get_col(key: str) -> pd.Series:
        col_name = col_map.get(key, '')
        if col_name and col_name in df.columns:
            return pd.to_numeric(df[col_name], errors='coerce')
        return pd.Series([None] * len(df), index=df.index)

    result = pd.DataFrame({
        'date': df['date'].dt.date,
        'corpus': _get_col('corpus'),
        'equity_holding': _get_col('equity_holding'),
        'etf_investment': _get_col('etf_investment'),
        'cash_equivalent': _get_col('cash_equivalent'),
        'bank_balance': _get_col('bank_balance'),
        'nav': _get_col('nav'),
        'liquidity_pct': _get_col('liquidity_pct'),
        'high_water_mark': _get_col('high_water_mark'),
    })

    result = result.dropna(subset=['nav']).sort_values('date').reset_index(drop=True)
    logger.info("Parsed %d NAV records for UCC %s", len(result), ucc_code)
    return result


def parse_transaction_excel(file_bytes: bytes, ucc_code: str) -> pd.DataFrame:
    """Parse PMS transaction log Excel into clean DataFrame.

    The file has 2 header rows, date separator rows ('Date :DD/MM/YY'),
    daily subtotal rows, and section/grand total rows.

    Returns:
        DataFrame with columns: date, script, exchange, stno,
        buy_qty..buy_amt_without_stt, sale_qty..sale_amt_without_stt
    """
    from io import BytesIO

    COLUMN_NAMES = [
        'ucc', 'script', 'exchange', 'stno',
        'buy_qty', 'buy_rate', 'buy_gst', 'buy_other_charges',
        'buy_stt', 'buy_cost_rate', 'buy_amt_with_cost', 'buy_amt_without_stt',
        'sale_qty', 'sale_rate', 'sale_gst', 'sale_stt',
        'sale_other_charges', 'sale_cost_rate', 'sale_amt_with_cost', 'sale_amt_without_stt',
    ]

    df = pd.read_excel(BytesIO(file_bytes), header=None, skiprows=2)
    df.columns = COLUMN_NAMES[:len(df.columns)]

    # Extract current date from "Date :DD/MM/YY" separator rows
    current_date = None
    dates: list = []
    keep_mask: list[bool] = []

    for _, row in df.iterrows():
        cell0 = str(row.get('ucc', '')).strip()

        # Date separator row (may have leading spaces)
        date_match = re.match(r'^Date\s*:\s*(\d{2}/\d{2}/\d{2})$', cell0)
        if date_match:
            current_date = pd.to_datetime(date_match.group(1), format='%d/%m/%y').date()
            keep_mask.append(False)
            dates.append(None)
            continue

        # Client header (contains brackets like [BJ53]), subtotal, grand total rows
        if ('[' in cell0 and ']' in cell0) or cell0 == 'GRAND TOTALS' \
                or cell0 == '' or cell0 == 'nan':
            keep_mask.append(False)
            dates.append(None)
            continue

        # Filter by UCC
        if cell0.strip() == ucc_code.strip():
            keep_mask.append(True)
            dates.append(current_date)
        else:
            keep_mask.append(False)
            dates.append(None)

    df = df[keep_mask].copy()
    df['date'] = [d for d, keep in zip(dates, keep_mask) if keep]

    if df.empty:
        raise ValueError(f"No transactions found for UCC code '{ucc_code}'")

    # Script column may contain "TICKER   EQ" merged format — split them
    def _split_script_exchange(val: str) -> tuple[str, str]:
        val = val.strip()
        parts = val.rsplit(None, 1)
        if len(parts) == 2 and parts[1] in ('EQ', 'BE', 'BZ', 'MF'):
            return parts[0].strip(), parts[1]
        return val, ''

    scripts = []
    exchanges = []
    for val in df['script'].astype(str):
        s, e = _split_script_exchange(val)
        scripts.append(s)
        exchanges.append(e)
    df['script'] = scripts
    df['exchange'] = exchanges
    df['stno'] = df['stno'].astype(str).str.strip()

    # Convert numeric columns
    numeric_cols = [c for c in COLUMN_NAMES[4:] if c in df.columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    result = df.drop(columns=['ucc']).sort_values('date').reset_index(drop=True)
    logger.info("Parsed %d transactions for UCC %s", len(result), ucc_code)
    return result
