"""
FIE v3 -- Global Market Constants
Centralized constant data for global indices, sector ETFs, and top constituents.
Used by routers/global_pulse.py and price_service.py for global RS analysis.

No imports required -- this file contains only pure data structures.
"""

# --- Global Index Universe ----------------------------------------------------
# Maps internal key -> metadata for each tracked global index.
# All prices fetched via yfinance.

GLOBAL_INDICES = {
    # -- US --
    "SP500":    {"symbol": "^GSPC",   "name": "S&P 500",            "region": "US",      "currency": "USD"},
    "NASDAQ":   {"symbol": "^IXIC",   "name": "NASDAQ Composite",   "region": "US",      "currency": "USD"},
    "DJIA":     {"symbol": "^DJI",    "name": "Dow Jones",          "region": "US",      "currency": "USD"},
    "RUSSELL":  {"symbol": "^RUT",    "name": "Russell 2000",       "region": "US",      "currency": "USD"},
    # -- Europe --
    "FTSE100":  {"symbol": "^FTSE",   "name": "FTSE 100",           "region": "Europe",  "currency": "GBP"},
    "DAX":      {"symbol": "^GDAXI",  "name": "DAX",                "region": "Europe",  "currency": "EUR"},
    "CAC40":    {"symbol": "^FCHI",   "name": "CAC 40",             "region": "Europe",  "currency": "EUR"},
    "STOXX600": {"symbol": "^STOXX",  "name": "STOXX 600",          "region": "Europe",  "currency": "EUR"},
    "AEX":      {"symbol": "^AEX",    "name": "AEX (Netherlands)",  "region": "Europe",  "currency": "EUR"},
    # -- Asia --
    "NIKKEI":   {"symbol": "^N225",   "name": "Nikkei 225",         "region": "Asia",    "currency": "JPY"},
    "HANGSENG": {"symbol": "^HSI",    "name": "Hang Seng",          "region": "Asia",    "currency": "HKD"},
    "SHANGHAI": {"symbol": "000001.SS", "name": "Shanghai Composite", "region": "Asia",  "currency": "CNY"},
    "KOSPI":    {"symbol": "^KS11",   "name": "KOSPI",              "region": "Asia",    "currency": "KRW"},
    "ASX200":   {"symbol": "^AXJO",   "name": "ASX 200",            "region": "Asia",    "currency": "AUD"},
    "TAIEX":    {"symbol": "^TWII",   "name": "Taiwan TAIEX",       "region": "Asia",    "currency": "TWD"},
    "STI":      {"symbol": "^STI",    "name": "Straits Times",      "region": "Asia",    "currency": "SGD"},
    # -- Americas (ex-US) --
    "BOVESPA":  {"symbol": "^BVSP",   "name": "IBOVESPA",           "region": "Americas", "currency": "BRL"},
    "TSX":      {"symbol": "^GSPTSE", "name": "TSX Composite",      "region": "Americas", "currency": "CAD"},
    # -- India (for self-reference) --
    "NIFTY50":  {"symbol": "^NSEI",   "name": "NIFTY 50",           "region": "India",   "currency": "INR"},
    "NIFTY500": {"symbol": "^CRSLDX", "name": "NIFTY 500",          "region": "India",   "currency": "INR"},
}

GLOBAL_REGION_ORDER = ["US", "Europe", "Asia", "Americas", "India"]

# Quick lookup: internal key -> yfinance symbol
GLOBAL_TICKER_MAP = {k: v["symbol"] for k, v in GLOBAL_INDICES.items()}


# --- Sector ETFs per Market ---------------------------------------------------
# Maps parent index key -> dict of sector keys with yfinance symbols.
# Sector RS is computed vs the parent index.

GLOBAL_SECTOR_MAP = {
    "SP500": {
        "SP500_TECH":       {"symbol": "XLK",  "name": "Technology"},
        "SP500_FIN":        {"symbol": "XLF",  "name": "Financials"},
        "SP500_HEALTH":     {"symbol": "XLV",  "name": "Healthcare"},
        "SP500_ENERGY":     {"symbol": "XLE",  "name": "Energy"},
        "SP500_CDISC":      {"symbol": "XLY",  "name": "Consumer Discretionary"},
        "SP500_CSTAP":      {"symbol": "XLP",  "name": "Consumer Staples"},
        "SP500_INDU":       {"symbol": "XLI",  "name": "Industrials"},
        "SP500_MATL":       {"symbol": "XLB",  "name": "Materials"},
        "SP500_UTIL":       {"symbol": "XLU",  "name": "Utilities"},
        "SP500_RLST":       {"symbol": "XLRE", "name": "Real Estate"},
        "SP500_COMM":       {"symbol": "XLC",  "name": "Communication Services"},
    },
    "FTSE100": {
        "FTSE_ENERGY":      {"symbol": "ISF.L",   "name": "Energy (iShares UK)"},
        "FTSE_FIN":         {"symbol": "XLFN.L",  "name": "Financials (iShares UK)"},
        "FTSE_HEALTH":      {"symbol": "IUKD.L",  "name": "Healthcare (iShares UK)"},
    },
    "DAX": {
        "DAX_TECH":         {"symbol": "EXV8.DE", "name": "Technology"},
        "DAX_INDU":         {"symbol": "EXV4.DE", "name": "Industrials"},
        "DAX_HEALTH":       {"symbol": "EXH1.DE", "name": "Healthcare"},
        "DAX_AUTO":         {"symbol": "EXV5.DE", "name": "Auto & Parts"},
        "DAX_BANK":         {"symbol": "EXV1.DE", "name": "Banks"},
        "DAX_CHEM":         {"symbol": "EXV6.DE", "name": "Basic Resources"},
        "DAX_UTIL":         {"symbol": "EXH8.DE", "name": "Utilities"},
        "DAX_OIL":          {"symbol": "EXH4.DE", "name": "Oil & Gas"},
        "DAX_TELE":         {"symbol": "EXV2.DE", "name": "Telecom"},
    },
    "NIKKEI": {
        "NIKKEI_BANK":      {"symbol": "1615.T",  "name": "Banks (TOPIX)"},
        "NIKKEI_PHARMA":    {"symbol": "1613.T",  "name": "Pharma (TOPIX)"},
        "NIKKEI_AUTO":      {"symbol": "1622.T",  "name": "Transport Equip (TOPIX)"},
        "NIKKEI_TECH":      {"symbol": "1627.T",  "name": "Electrical Equip (TOPIX)"},
        "NIKKEI_REAL":      {"symbol": "1618.T",  "name": "Real Estate (TOPIX)"},
    },
    "HANGSENG": {
        "HSI_TECH":         {"symbol": "3067.HK", "name": "Hang Seng TECH"},
        "HSI_FIN":          {"symbol": "3143.HK", "name": "Hang Seng Financials"},
    },
}

# Flat lookup: sector_key -> { symbol, name, parent_index }
GLOBAL_SECTOR_FLAT = {}
for parent_key, sectors in GLOBAL_SECTOR_MAP.items():
    for sec_key, sec_info in sectors.items():
        GLOBAL_SECTOR_FLAT[sec_key] = {
            **sec_info,
            "parent_index": parent_key,
        }


# --- Top Constituents per Sector ----------------------------------------------
# Curated top stocks for each sector ETF. Prices fetched via yfinance.
# These are the most liquid, highest-weight holdings.

GLOBAL_CONSTITUENTS = {
    # -- US S&P 500 Sectors --
    "SP500_TECH": [
        {"ticker": "AAPL",  "name": "Apple"},
        {"ticker": "MSFT",  "name": "Microsoft"},
        {"ticker": "NVDA",  "name": "NVIDIA"},
        {"ticker": "AVGO",  "name": "Broadcom"},
        {"ticker": "ADBE",  "name": "Adobe"},
        {"ticker": "CRM",   "name": "Salesforce"},
        {"ticker": "ORCL",  "name": "Oracle"},
        {"ticker": "AMD",   "name": "AMD"},
        {"ticker": "CSCO",  "name": "Cisco"},
        {"ticker": "INTC",  "name": "Intel"},
    ],
    "SP500_FIN": [
        {"ticker": "JPM",   "name": "JPMorgan Chase"},
        {"ticker": "BAC",   "name": "Bank of America"},
        {"ticker": "WFC",   "name": "Wells Fargo"},
        {"ticker": "GS",    "name": "Goldman Sachs"},
        {"ticker": "MS",    "name": "Morgan Stanley"},
        {"ticker": "BLK",   "name": "BlackRock"},
        {"ticker": "SCHW",  "name": "Charles Schwab"},
        {"ticker": "C",     "name": "Citigroup"},
        {"ticker": "AXP",   "name": "American Express"},
        {"ticker": "USB",   "name": "US Bancorp"},
    ],
    "SP500_HEALTH": [
        {"ticker": "UNH",   "name": "UnitedHealth"},
        {"ticker": "JNJ",   "name": "Johnson & Johnson"},
        {"ticker": "LLY",   "name": "Eli Lilly"},
        {"ticker": "PFE",   "name": "Pfizer"},
        {"ticker": "ABBV",  "name": "AbbVie"},
        {"ticker": "MRK",   "name": "Merck"},
        {"ticker": "TMO",   "name": "Thermo Fisher"},
        {"ticker": "ABT",   "name": "Abbott Labs"},
        {"ticker": "DHR",   "name": "Danaher"},
        {"ticker": "AMGN",  "name": "Amgen"},
    ],
    "SP500_ENERGY": [
        {"ticker": "XOM",   "name": "Exxon Mobil"},
        {"ticker": "CVX",   "name": "Chevron"},
        {"ticker": "COP",   "name": "ConocoPhillips"},
        {"ticker": "SLB",   "name": "Schlumberger"},
        {"ticker": "EOG",   "name": "EOG Resources"},
        {"ticker": "MPC",   "name": "Marathon Petroleum"},
        {"ticker": "PSX",   "name": "Phillips 66"},
        {"ticker": "VLO",   "name": "Valero Energy"},
        {"ticker": "OXY",   "name": "Occidental"},
        {"ticker": "HAL",   "name": "Halliburton"},
    ],
    "SP500_CDISC": [
        {"ticker": "AMZN",  "name": "Amazon"},
        {"ticker": "TSLA",  "name": "Tesla"},
        {"ticker": "HD",    "name": "Home Depot"},
        {"ticker": "MCD",   "name": "McDonald's"},
        {"ticker": "NKE",   "name": "Nike"},
        {"ticker": "LOW",   "name": "Lowe's"},
        {"ticker": "SBUX",  "name": "Starbucks"},
        {"ticker": "TJX",   "name": "TJX Companies"},
        {"ticker": "BKNG",  "name": "Booking Holdings"},
        {"ticker": "CMG",   "name": "Chipotle"},
    ],
    "SP500_CSTAP": [
        {"ticker": "PG",    "name": "Procter & Gamble"},
        {"ticker": "KO",    "name": "Coca-Cola"},
        {"ticker": "PEP",   "name": "PepsiCo"},
        {"ticker": "COST",  "name": "Costco"},
        {"ticker": "WMT",   "name": "Walmart"},
        {"ticker": "PM",    "name": "Philip Morris"},
        {"ticker": "MDLZ",  "name": "Mondelez"},
        {"ticker": "CL",    "name": "Colgate-Palmolive"},
        {"ticker": "MO",    "name": "Altria"},
        {"ticker": "KHC",   "name": "Kraft Heinz"},
    ],
    "SP500_INDU": [
        {"ticker": "CAT",   "name": "Caterpillar"},
        {"ticker": "GE",    "name": "GE Aerospace"},
        {"ticker": "HON",   "name": "Honeywell"},
        {"ticker": "UNP",   "name": "Union Pacific"},
        {"ticker": "BA",    "name": "Boeing"},
        {"ticker": "RTX",   "name": "RTX Corp"},
        {"ticker": "DE",    "name": "Deere & Company"},
        {"ticker": "LMT",   "name": "Lockheed Martin"},
        {"ticker": "UPS",   "name": "UPS"},
        {"ticker": "MMM",   "name": "3M"},
    ],
    "SP500_MATL": [
        {"ticker": "LIN",   "name": "Linde"},
        {"ticker": "APD",   "name": "Air Products"},
        {"ticker": "SHW",   "name": "Sherwin-Williams"},
        {"ticker": "ECL",   "name": "Ecolab"},
        {"ticker": "NEM",   "name": "Newmont"},
        {"ticker": "FCX",   "name": "Freeport-McMoRan"},
        {"ticker": "DOW",   "name": "Dow Inc"},
        {"ticker": "NUE",   "name": "Nucor"},
        {"ticker": "CTVA",  "name": "Corteva"},
        {"ticker": "VMC",   "name": "Vulcan Materials"},
    ],
    "SP500_UTIL": [
        {"ticker": "NEE",   "name": "NextEra Energy"},
        {"ticker": "DUK",   "name": "Duke Energy"},
        {"ticker": "SO",    "name": "Southern Company"},
        {"ticker": "D",     "name": "Dominion Energy"},
        {"ticker": "AEP",   "name": "American Electric"},
        {"ticker": "EXC",   "name": "Exelon"},
        {"ticker": "SRE",   "name": "Sempra"},
        {"ticker": "XEL",   "name": "Xcel Energy"},
        {"ticker": "WEC",   "name": "WEC Energy"},
        {"ticker": "ED",    "name": "Consolidated Edison"},
    ],
    "SP500_RLST": [
        {"ticker": "PLD",   "name": "Prologis"},
        {"ticker": "AMT",   "name": "American Tower"},
        {"ticker": "EQIX",  "name": "Equinix"},
        {"ticker": "CCI",   "name": "Crown Castle"},
        {"ticker": "SPG",   "name": "Simon Property"},
        {"ticker": "PSA",   "name": "Public Storage"},
        {"ticker": "O",     "name": "Realty Income"},
        {"ticker": "WELL",  "name": "Welltower"},
        {"ticker": "DLR",   "name": "Digital Realty"},
        {"ticker": "AVB",   "name": "AvalonBay"},
    ],
    "SP500_COMM": [
        {"ticker": "META",  "name": "Meta Platforms"},
        {"ticker": "GOOG",  "name": "Alphabet"},
        {"ticker": "NFLX",  "name": "Netflix"},
        {"ticker": "DIS",   "name": "Walt Disney"},
        {"ticker": "CMCSA", "name": "Comcast"},
        {"ticker": "T",     "name": "AT&T"},
        {"ticker": "VZ",    "name": "Verizon"},
        {"ticker": "TMUS",  "name": "T-Mobile US"},
        {"ticker": "CHTR",  "name": "Charter Comm"},
        {"ticker": "EA",    "name": "Electronic Arts"},
    ],
}

# --- All Global yfinance Symbols (for batch fetching) -------------------------

def get_all_global_symbols() -> dict:
    """Return {internal_key: yfinance_symbol} for every global instrument."""
    symbols = {}
    # Level 1: Global indices
    for k, v in GLOBAL_INDICES.items():
        symbols[k] = v["symbol"]
    # Level 2: Sector ETFs
    for sectors in GLOBAL_SECTOR_MAP.values():
        for sec_key, sec_info in sectors.items():
            symbols[sec_key] = sec_info["symbol"]
    # Level 3: Individual stocks
    for constituents in GLOBAL_CONSTITUENTS.values():
        for stock in constituents:
            symbols[stock["ticker"]] = stock["ticker"]
    return symbols
