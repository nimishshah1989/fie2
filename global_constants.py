"""
FIE — Global Market Constants
Benchmarks + sector ETFs per country for the Global Markets tab.
All data sourced from yfinance. Focus on reliable, liquid instruments.

Structure:
  GLOBAL_MARKETS: dict of market_key -> {benchmark, sector_etfs}
  Each sector ETF is measured against its country's benchmark for relative performance.
"""

# ─── Global Market Definitions ────────────────────────────────────────────
# Each market has:
#   - benchmark: the main country index (yfinance symbol + display name)
#   - sector_etfs: list of sector ETFs with yfinance symbol + sector label
#
# Only includes ETFs with reliable yfinance data. No individual stocks.

GLOBAL_MARKETS: dict = {
    "US": {
        "name": "United States",
        "flag": "🇺🇸",
        "benchmark": {"key": "SP500", "symbol": "^GSPC", "name": "S&P 500"},
        "sector_etfs": [
            {"key": "US_XLK",  "symbol": "XLK",  "name": "Technology"},
            {"key": "US_XLF",  "symbol": "XLF",  "name": "Financials"},
            {"key": "US_XLV",  "symbol": "XLV",  "name": "Health Care"},
            {"key": "US_XLE",  "symbol": "XLE",  "name": "Energy"},
            {"key": "US_XLY",  "symbol": "XLY",  "name": "Consumer Discretionary"},
            {"key": "US_XLP",  "symbol": "XLP",  "name": "Consumer Staples"},
            {"key": "US_XLI",  "symbol": "XLI",  "name": "Industrials"},
            {"key": "US_XLB",  "symbol": "XLB",  "name": "Materials"},
            {"key": "US_XLU",  "symbol": "XLU",  "name": "Utilities"},
            {"key": "US_XLRE", "symbol": "XLRE", "name": "Real Estate"},
            {"key": "US_XLC",  "symbol": "XLC",  "name": "Communication Services"},
        ],
    },
    "UK": {
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "benchmark": {"key": "FTSE100", "symbol": "^FTSE", "name": "FTSE 100"},
        "sector_etfs": [
            {"key": "UK_MIDD", "symbol": "^FTMC", "name": "FTSE 250 (Mid Cap)"},
            {"key": "UK_ISF",  "symbol": "ISF.L",  "name": "FTSE 100 ETF"},
        ],
    },
    "EU": {
        "name": "Europe",
        "flag": "🇪🇺",
        "benchmark": {"key": "STOXX50", "symbol": "^STOXX50E", "name": "Euro Stoxx 50"},
        "sector_etfs": [
            {"key": "EU_SXKP", "symbol": "EXV6.DE", "name": "Basic Resources"},
            {"key": "EU_SX8P", "symbol": "EXV8.DE", "name": "Technology"},
            {"key": "EU_SX7P", "symbol": "EXH1.DE", "name": "Banks"},
            {"key": "EU_SXEP", "symbol": "EXH9.DE", "name": "Auto & Parts"},
            {"key": "EU_SXDP", "symbol": "EXV5.DE", "name": "Health Care"},
        ],
    },
    "DE": {
        "name": "Germany",
        "flag": "🇩🇪",
        "benchmark": {"key": "DAX", "symbol": "^GDAXI", "name": "DAX"},
        "sector_etfs": [],
    },
    "FR": {
        "name": "France",
        "flag": "🇫🇷",
        "benchmark": {"key": "CAC40", "symbol": "^FCHI", "name": "CAC 40"},
        "sector_etfs": [],
    },
    "JP": {
        "name": "Japan",
        "flag": "🇯🇵",
        "benchmark": {"key": "NIKKEI", "symbol": "^N225", "name": "Nikkei 225"},
        "sector_etfs": [
            {"key": "JP_TOPIX", "symbol": "^TOPX", "name": "TOPIX (Broad)"},
        ],
    },
    "HK": {
        "name": "Hong Kong",
        "flag": "🇭🇰",
        "benchmark": {"key": "HSI", "symbol": "^HSI", "name": "Hang Seng"},
        "sector_etfs": [
            {"key": "HK_HSTECH", "symbol": "^HSTECH", "name": "HS Tech Index"},
        ],
    },
    "CN": {
        "name": "China",
        "flag": "🇨🇳",
        "benchmark": {"key": "CSI300", "symbol": "000300.SS", "name": "CSI 300"},
        "sector_etfs": [],
    },
    "KR": {
        "name": "South Korea",
        "flag": "🇰🇷",
        "benchmark": {"key": "KOSPI", "symbol": "^KS11", "name": "KOSPI"},
        "sector_etfs": [],
    },
    "AU": {
        "name": "Australia",
        "flag": "🇦🇺",
        "benchmark": {"key": "ASX200", "symbol": "^AXJO", "name": "ASX 200"},
        "sector_etfs": [],
    },
    "CA": {
        "name": "Canada",
        "flag": "🇨🇦",
        "benchmark": {"key": "TSX", "symbol": "^GSPTSE", "name": "S&P/TSX Composite"},
        "sector_etfs": [],
    },
    "BR": {
        "name": "Brazil",
        "flag": "🇧🇷",
        "benchmark": {"key": "BOVESPA", "symbol": "^BVSP", "name": "Bovespa"},
        "sector_etfs": [],
    },
}


# ─── Derived: All global instrument keys + yfinance symbols ──────────────
# Used by price_service for bulk fetch.

def get_all_global_symbols() -> dict[str, str]:
    """Return {internal_key: yfinance_symbol} for all global instruments."""
    symbols = {}
    for market in GLOBAL_MARKETS.values():
        bm = market["benchmark"]
        symbols[bm["key"]] = bm["symbol"]
        for etf in market["sector_etfs"]:
            symbols[etf["key"]] = etf["symbol"]
    return symbols


def get_all_global_keys() -> list[str]:
    """Return flat list of all global instrument internal keys."""
    return list(get_all_global_symbols().keys())


# ─── Derived: Display name map ───────────────────────────────────────────

def get_global_display_map() -> dict[str, str]:
    """Return {internal_key: display_name} for all global instruments."""
    names = {}
    for market in GLOBAL_MARKETS.values():
        bm = market["benchmark"]
        names[bm["key"]] = bm["name"]
        for etf in market["sector_etfs"]:
            names[etf["key"]] = etf["name"]
    return names


# ─── Derived: key -> market mapping ──────────────────────────────────────

def get_key_to_market() -> dict[str, str]:
    """Return {internal_key: market_key} e.g. {'US_XLK': 'US', 'SP500': 'US'}."""
    mapping = {}
    for market_key, market in GLOBAL_MARKETS.items():
        mapping[market["benchmark"]["key"]] = market_key
        for etf in market["sector_etfs"]:
            mapping[etf["key"]] = market_key
    return mapping


def get_benchmark_for_key(instrument_key: str) -> str | None:
    """Given an instrument key, return its market's benchmark key."""
    key_to_market = get_key_to_market()
    market_key = key_to_market.get(instrument_key)
    if not market_key:
        return None
    return GLOBAL_MARKETS[market_key]["benchmark"]["key"]
