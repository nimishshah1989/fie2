"""
FIE -- Index Constants
Centralized constant data for all tracked NSE/BSE indices, ETFs, commodities, and currencies.
Used by price_service.py, routers/indices.py, and other modules that need index metadata.

No imports required -- this file contains only pure data structures.
"""

# --- Yahoo Finance Ticker Map ------------------------------------------------
# Maps internal key -> yfinance symbol for historical price fetching.
# Not all NSE indices have yfinance equivalents; those without entries
# are fetched via NSE website API or nsetools instead.

NSE_TICKER_MAP = {
    # -- NSE Broad Market --
    "NIFTY":            "^NSEI",
    "NIFTY50":          "^NSEI",
    "NIFTY100":         "^CNX100",
    "NIFTY200":         "^CNX200",
    "NIFTY500":         "^CRSLDX",
    "NIFTYNEXT50":      "^NSMIDCP",
    "NIFTYMIDCAP":      "^NSEMDCP50",
    "NIFTYMIDCAP50":    "^NSEMDCP50",
    "MIDCPNIFTY":       "^NSEMDCP50",
    "NIFTYSMALLCAP":    "^CNXSC",
    # -- NSE Sectoral --
    "BANKNIFTY":        "^NSEBANK",
    "NIFTYBANK":        "^NSEBANK",
    "NIFTYIT":          "^CNXIT",
    "NIFTYPHARMA":      "^CNXPHARMA",
    "NIFTYFMCG":        "^CNXFMCG",
    "NIFTYAUTO":        "^CNXAUTO",
    "NIFTYMETAL":       "^CNXMETAL",
    "NIFTYREALTY":      "^CNXREALTY",
    "NIFTYENERGY":      "^CNXENERGY",
    "NIFTYPSUBANK":     "^CNXPSUBANK",
    "NIFTYPVTBANK":     "NIFTY_PVT_BANK.NS",
    "NIFTYINFRA":       "^CNXINFRA",
    "NIFTYMEDIA":       "^CNXMEDIA",
    "NIFTYFINSERVICE":  "NIFTY_FIN_SERVICE.NS",
    "FINNIFTY":         "NIFTY_FIN_SERVICE.NS",
    "NIFTYMNC":         "^CNXMNC",
    "NIFTYPSE":         "^CNXPSE",
    "NIFTYSERVICE":     "^CNXSERVICE",
    "NIFTYCONSUMPTION": "^CNXCONSUM",
    "NIFTYCOMMODITIES": "^CNXCMDT",
    # -- NSE Thematic (live price, limited yfinance history) --
    "NIFTYCPSE":        "NIFTY_CPSE.NS",
    "NIFTYHEALTHCARE":  "NIFTY_HEALTHCARE.NS",
    "NIFTYCONSUMER":    "NIFTY_CONSR_DURBL.NS",
    # -- India VIX --
    "INDIAVIX":         "^INDIAVIX",
    # -- BSE --
    "SENSEX":           "^BSESN",
    "BSE500":           "BSE-500.BO",
    "BSEIT":            "BSE-IT.BO",
    "BSEBANK":          "BSE-BANKEX.BO",
    # -- Commodities --
    "GOLD":             "GC=F",
    "SILVER":           "SI=F",
    "CRUDEOIL":         "CL=F",
    "CRUDE":            "CL=F",
    "NATURALGAS":       "NG=F",
    "COPPER":           "HG=F",
    # -- Currency --
    "USDINR":           "USDINR=X",
    "EURINR":           "EURINR=X",
    "GBPINR":           "GBPINR=X",
}

# --- Yahoo Finance Fallback Symbols ------------------------------------------
# When primary yfinance symbol fails, try these alternatives.

FALLBACK_MAP = {
    "^NSEI":    ["NIFTY_50.NS"],
    "^NSEBANK": ["BANKBEES.NS"],
    "^CNXIT":   ["NIFTYIT.NS"],
    "^BSESN":   ["^BSESN"],
}

# --- NSE Index Keys for EOD Fetch --------------------------------------------
# All tracked instruments for yfinance backfill + pulse page display.
# Order: Broad Market -> Sectoral -> Thematic -> BSE/Global -> Fixed Income

NSE_INDEX_KEYS = [
    # Broad Market
    "NIFTY", "NIFTY100", "NIFTY200", "NIFTY500", "NIFTYNEXT50",
    "MIDCPNIFTY", "NIFTYMIDCAP100", "NIFTYMIDCAP150",
    "NIFTYSMALLCAP50", "NIFTYSMALLCAP100", "NIFTYSMALLCAP250",
    "NIFTYMIDSMALL400", "NIFTYLARGEMIDCAP250", "NIFTYMICROCAP250",
    "NIFTYTOTALMARKET", "NIFTY500MULTICAP",
    # India VIX
    "INDIAVIX",
    # Sectoral
    "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG", "NIFTYAUTO",
    "NIFTYMETAL", "NIFTYREALTY", "NIFTYENERGY", "NIFTYPSUBANK", "NIFTYPVTBANK",
    "NIFTYINFRA", "NIFTYMEDIA", "FINNIFTY", "NIFTYFINSERVICE",
    "NIFTYMNC", "NIFTYPSE", "NIFTYSERVICE",
    "NIFTYCONSUMERDURABLES", "NIFTYOILGAS", "NIFTYCHEMICALS",
    # New Sectoral
    "NIFTYCAPITALMARKETS", "NIFTYFINSERVEXBANK",
    "NIFTYMIDSMALLFINSERV", "NIFTYMIDSMALLHC",
    "NIFTYMIDSMALLITTEL", "NIFTYMIDSMALLCONS",
    # Thematic
    "NIFTYHEALTHCARE", "NIFTYCONSUMPTION", "NIFTYCOMMODITIES",
    "NIFTYINDIAMFG", "NIFTYINDIADEFENCE", "NIFTYINDIGITAL",
    "NIFTYCPSE",
    # New Thematic
    "NIFTYHOUSING", "NIFTYCOREHOUSING", "NIFTYIPO", "NIFTYMOBILITY",
    "NIFTYINDIATOURISM", "NIFTYINDIARAILWAYS", "NIFTYEVNEWAGE",
    "NIFTYNONCYCLICAL", "NIFTYRURAL", "NIFTYCONGLOMERATE",
    "NIFTYTRANSLOGISTICS", "NIFTYINDIANEWAGE", "NIFTYINDIAFPI",
    "NIFTYINDIAINFRALOG", "NIFTYINDIAINTERNET",
    # BSE
    "SENSEX", "BSE500",
    # Commodities & Currency
    "GOLD", "SILVER", "CRUDEOIL", "COPPER", "USDINR",
    # Fixed Income
    "NIFTYLIQUID15", "NIFTYGSEC10YR", "NIFTYGSEC813",
    "NIFTYGSEC48", "NIFTYGSEC1115", "NIFTYGSEC15PLUS",
    "NIFTYGSECCOMPOSITE",
]

# --- Category Map for Pulse Page Tab Grouping --------------------------------
# Maps internal key -> category string for frontend filtering.

NSE_INDEX_CATEGORIES: dict = {
    # Broad Market
    "NIFTY": "broad", "NIFTY100": "broad", "NIFTY200": "broad",
    "NIFTY500": "broad", "NIFTYNEXT50": "broad", "MIDCPNIFTY": "broad",
    "NIFTYMIDCAP100": "broad", "NIFTYMIDCAP150": "broad",
    "NIFTYSMALLCAP50": "broad", "NIFTYSMALLCAP100": "broad",
    "NIFTYSMALLCAP250": "broad", "NIFTYMIDSMALL400": "broad",
    "NIFTYLARGEMIDCAP250": "broad", "NIFTYMICROCAP250": "broad",
    "NIFTYTOTALMARKET": "broad", "NIFTY500MULTICAP": "broad",
    "INDIAVIX": "broad",
    # Sectoral
    "BANKNIFTY": "sectoral", "NIFTYIT": "sectoral", "NIFTYPHARMA": "sectoral",
    "NIFTYFMCG": "sectoral", "NIFTYAUTO": "sectoral", "NIFTYMETAL": "sectoral",
    "NIFTYREALTY": "sectoral", "NIFTYENERGY": "sectoral", "NIFTYPSUBANK": "sectoral",
    "NIFTYPVTBANK": "sectoral", "NIFTYINFRA": "sectoral", "NIFTYMEDIA": "sectoral",
    "FINNIFTY": "sectoral", "NIFTYFINSERVICE": "sectoral",
    "NIFTYMNC": "sectoral", "NIFTYPSE": "sectoral", "NIFTYSERVICE": "sectoral",
    "NIFTYCONSUMERDURABLES": "sectoral", "NIFTYOILGAS": "sectoral",
    "NIFTYCHEMICALS": "sectoral",
    # New Sectoral
    "NIFTYCAPITALMARKETS": "sectoral", "NIFTYFINSERVEXBANK": "sectoral",
    "NIFTYMIDSMALLFINSERV": "sectoral", "NIFTYMIDSMALLHC": "sectoral",
    "NIFTYMIDSMALLITTEL": "sectoral", "NIFTYMIDSMALLCONS": "sectoral",
    # Thematic
    "NIFTYHEALTHCARE": "thematic", "NIFTYCONSUMPTION": "thematic",
    "NIFTYCOMMODITIES": "thematic", "NIFTYINDIAMFG": "thematic",
    "NIFTYINDIADEFENCE": "thematic", "NIFTYINDIGITAL": "thematic",
    "NIFTYCPSE": "thematic",
    # New Thematic
    "NIFTYHOUSING": "thematic", "NIFTYCOREHOUSING": "thematic",
    "NIFTYIPO": "thematic", "NIFTYMOBILITY": "thematic",
    "NIFTYINDIATOURISM": "thematic", "NIFTYINDIARAILWAYS": "thematic",
    "NIFTYEVNEWAGE": "thematic", "NIFTYNONCYCLICAL": "thematic",
    "NIFTYRURAL": "thematic", "NIFTYCONGLOMERATE": "thematic",
    "NIFTYTRANSLOGISTICS": "thematic", "NIFTYINDIANEWAGE": "thematic",
    "NIFTYINDIAFPI": "thematic", "NIFTYINDIAINFRALOG": "thematic",
    "NIFTYINDIAINTERNET": "thematic",
    # BSE & Global
    "SENSEX": "global", "BSE500": "global",
    "GOLD": "global", "SILVER": "global", "CRUDEOIL": "global",
    "COPPER": "global", "USDINR": "global",
    # Fixed Income
    "NIFTYLIQUID15": "fixed_income", "NIFTYGSEC10YR": "fixed_income",
    "NIFTYGSEC813": "fixed_income", "NIFTYGSEC48": "fixed_income",
    "NIFTYGSEC1115": "fixed_income", "NIFTYGSEC15PLUS": "fixed_income",
    "NIFTYGSECCOMPOSITE": "fixed_income",
}

# --- Non-nsetools Instruments ------------------------------------------------
# These do NOT have nsetools live quotes; served from DB prices on pulse page
# (BSE & Global tab, Fixed Income tab).

NON_NSETOOLS_KEYS = [
    "SENSEX", "BSE500", "GOLD", "SILVER", "CRUDEOIL", "COPPER", "USDINR",
    # Fixed Income (no nsetools live quotes -- served from DB)
    "NIFTYLIQUID15", "NIFTYGSEC10YR", "NIFTYGSEC813",
    "NIFTYGSEC48", "NIFTYGSEC1115", "NIFTYGSEC15PLUS", "NIFTYGSECCOMPOSITE",
]

# --- Fixed Income Keys -------------------------------------------------------

FIXED_INCOME_KEYS = [
    "NIFTYLIQUID15",
    "NIFTYGSEC10YR",
    "NIFTYGSEC813",
    "NIFTYGSEC48",
    "NIFTYGSEC1115",
    "NIFTYGSEC15PLUS",
    "NIFTYGSECCOMPOSITE",
]

# --- ETF Universe for EOD Tracking -------------------------------------------
# Maps our internal ETF key -> yfinance symbol.

NSE_ETF_UNIVERSE = {
    # Broad Market
    "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "BANKBEES": "BANKBEES.NS",
    # Sector
    "ITBEES": "ITBEES.NS",
    "PHARMABEES": "PHARMABEES.NS",
    "PSUBNKBEES": "PSUBNKBEES.NS",
    # Commodity
    "GOLDBEES": "GOLDBEES.NS",
    "SILVERBEES": "SILVERBEES.NS",
    # Portfolio-held ETFs
    "CPSEETF": "CPSEETF.NS",
    "LIQUIDCASE": "LIQUIDCASE.NS",
    "SENSEXETF": "SENSEXIETF.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "NETFMID150": "MID150BEES.NS",
    "FMCGIETF": "FMCGIETF.NS",
    "OILIETF": "OILIETF.NS",
    "NETFAUTO": "NETFAUTO.NS",
    "METALIETF": "METALIETF.NS",
}

# --- NSE Display Name Map ----------------------------------------------------
# Maps our internal key -> NSE display name as returned by nsetools.
# This is the canonical source of truth for display names across the platform.

NSE_DISPLAY_MAP = {
    # -- Broad Market --
    "NIFTY":                "NIFTY 50",
    "NIFTY100":             "NIFTY 100",
    "NIFTY200":             "NIFTY 200",
    "NIFTY500":             "NIFTY 500",
    "NIFTYNEXT50":          "NIFTY NEXT 50",
    "MIDCPNIFTY":           "NIFTY MIDCAP 50",
    "NIFTYMIDCAP100":       "NIFTY MIDCAP 100",
    "NIFTYMIDCAP150":       "NIFTY MIDCAP 150",
    "NIFTYSMALLCAP":        "NIFTY SMALLCAP 250",
    "NIFTYSMALLCAP50":      "NIFTY SMALLCAP 50",
    "NIFTYSMALLCAP100":     "NIFTY SMALLCAP 100",
    "NIFTYSMALLCAP250":     "NIFTY SMALLCAP 250",
    "NIFTYMIDSMALL400":     "NIFTY MIDSMALLCAP 400",
    "NIFTYLARGEMIDCAP250":  "NIFTY LARGEMIDCAP 250",
    "NIFTYMICROCAP250":     "NIFTY MICROCAP 250",
    "NIFTYTOTALMARKET":     "NIFTY TOTAL MARKET",
    "NIFTY500MULTICAP":     "NIFTY500 MULTICAP 50:25:25",
    "INDIAVIX":             "INDIA VIX",
    # -- Sectoral --
    "BANKNIFTY":            "NIFTY BANK",
    "NIFTYIT":              "NIFTY IT",
    "NIFTYPHARMA":          "NIFTY PHARMA",
    "NIFTYFMCG":            "NIFTY FMCG",
    "NIFTYAUTO":            "NIFTY AUTO",
    "NIFTYMETAL":           "NIFTY METAL",
    "NIFTYREALTY":          "NIFTY REALTY",
    "NIFTYENERGY":          "NIFTY ENERGY",
    "NIFTYPSUBANK":         "NIFTY PSU BANK",
    "NIFTYPVTBANK":         "NIFTY PRIVATE BANK",
    "NIFTYINFRA":           "NIFTY INFRASTRUCTURE",
    "NIFTYMEDIA":           "NIFTY MEDIA",
    "FINNIFTY":             "NIFTY FINANCIAL SERVICES",
    "NIFTYFINSERVICE":      "NIFTY FINANCIAL SERVICES 25/50",
    "NIFTYMNC":             "NIFTY MNC",
    "NIFTYPSE":             "NIFTY PSE",
    "NIFTYSERVICE":         "NIFTY SERVICES SECTOR",
    "NIFTYCONSUMERDURABLES": "NIFTY CONSUMER DURABLES",
    "NIFTYOILGAS":          "NIFTY OIL & GAS",
    "NIFTYCHEMICALS":       "NIFTY CHEMICALS",
    # New Sectoral
    "NIFTYCAPITALMARKETS":  "NIFTY CAPITAL MARKETS",
    "NIFTYFINSERVEXBANK":   "NIFTY FINANCIAL SERVICES EX-BANK",
    "NIFTYMIDSMALLFINSERV": "NIFTY MIDSMALL FINANCIAL SERVICES",
    "NIFTYMIDSMALLHC":      "NIFTY MIDSMALL HEALTHCARE",
    "NIFTYMIDSMALLITTEL":   "NIFTY MIDSMALL IT & TELECOM",
    "NIFTYMIDSMALLCONS":    "NIFTY MIDSMALL INDIA CONSUMPTION",
    # -- Thematic --
    "NIFTYHEALTHCARE":      "NIFTY HEALTHCARE INDEX",
    "NIFTYCONSUMPTION":     "NIFTY INDIA CONSUMPTION",
    "NIFTYCOMMODITIES":     "NIFTY COMMODITIES",
    "NIFTYINDIAMFG":        "NIFTY INDIA MANUFACTURING",
    "NIFTYINDIADEFENCE":    "NIFTY INDIA DEFENCE",
    "NIFTYINDIGITAL":       "NIFTY INDIA DIGITAL",
    "NIFTYCPSE":            "NIFTY CPSE",
    # New Thematic
    "NIFTYHOUSING":         "NIFTY HOUSING",
    "NIFTYCOREHOUSING":     "NIFTY CORE HOUSING",
    "NIFTYIPO":             "NIFTY IPO",
    "NIFTYMOBILITY":        "NIFTY MOBILITY",
    "NIFTYINDIATOURISM":    "NIFTY INDIA TOURISM",
    "NIFTYINDIARAILWAYS":   "NIFTY INDIA RAILWAYS PSU",
    "NIFTYEVNEWAGE":        "NIFTY EV & NEW AGE AUTOMOTIVE",
    "NIFTYNONCYCLICAL":     "NIFTY NON-CYCLICAL CONSUMER",
    "NIFTYRURAL":           "NIFTY RURAL",
    "NIFTYCONGLOMERATE":    "NIFTY CONGLOMERATE 50",
    "NIFTYTRANSLOGISTICS":  "NIFTY TRANSPORTATION & LOGISTICS",
    "NIFTYINDIANEWAGE":     "NIFTY INDIA NEW AGE CONSUMPTION",
    "NIFTYINDIAFPI":        "NIFTY INDIA FPI 150",
    "NIFTYINDIAINFRALOG":   "NIFTY INDIA INFRASTRUCTURE & LOGISTICS",
    "NIFTYINDIAINTERNET":   "NIFTY INDIA INTERNET",
    # -- Fixed Income --
    "NIFTYLIQUID15":        "NIFTY LIQUID 15",
    "NIFTYGSEC10YR":        "NIFTY 10 YR BENCHMARK G-SEC",
    "NIFTYGSEC813":         "NIFTY 8-13 YR G-SEC",
    "NIFTYGSEC48":          "NIFTY 4-8 YR G-SEC INDEX",
    "NIFTYGSEC1115":        "NIFTY 11-15 YR G-SEC INDEX",
    "NIFTYGSEC15PLUS":      "NIFTY 15 YR AND ABOVE G-SEC INDEX",
    "NIFTYGSECCOMPOSITE":   "NIFTY COMPOSITE G-SEC INDEX",
    # -- BSE & Global --
    "SENSEX":               "SENSEX",
    "BSE500":               "BSE 500",
    "GOLD":                 "Gold (USD)",
    "SILVER":               "Silver (USD)",
    "CRUDEOIL":             "Crude Oil (USD)",
    "COPPER":               "Copper (USD)",
    "USDINR":               "USD/INR",
}

# --- Reverse Map: NSE Display Name -> Internal Key ---------------------------
# Built from NSE_DISPLAY_MAP. Used by nsetools live fetch to convert
# display names back to our internal keys.

_NSE_REVERSE_MAP = {}
for _k, _v in NSE_DISPLAY_MAP.items():
    _NSE_REVERSE_MAP[_v.upper()] = _k

# --- Sector Indices for Recommendation Engine --------------------------------
# Auto-generated from NSE_INDEX_CATEGORIES: all sectoral + thematic indices.
# Returns list of (internal_key, NSE display name) tuples.
# Used by routers/recommendations.py + EOD constituent refresh.

# Sectors/themes to SKIP (no constituent data or too broad)
_RECO_SKIP: set = {
    "NIFTY50",
    "NIFTYNEXT50",
    "NIFTY100",
    "NIFTY200",
    "NIFTY500",
    "NIFTYMIDCAP50",
    "NIFTYMIDCAP100",
    "NIFTYMIDCAP150",
    "NIFTYSMALLCAP50",
    "NIFTYSMALLCAP100",
    "NIFTYSMALLCAP250",
    "NIFTYLARGEMIDCAP250",
    "NIFTYMIDSML400",
    "NIFTYTOTALMARKET",
}

# Old hardcoded list (15 sectors) — replaced by programmatic generation below:
# SECTOR_INDICES_FOR_RECO = [
#     ("BANKNIFTY", "NIFTY BANK"), ("NIFTYIT", "NIFTY IT"),
#     ("NIFTYPHARMA", "NIFTY PHARMA"), ("NIFTYFMCG", "NIFTY FMCG"),
#     ("NIFTYAUTO", "NIFTY AUTO"), ("NIFTYMETAL", "NIFTY METAL"),
#     ("NIFTYREALTY", "NIFTY REALTY"), ("NIFTYENERGY", "NIFTY ENERGY"),
#     ("NIFTYPSUBANK", "NIFTY PSU BANK"), ("NIFTYPVTBANK", "NIFTY PRIVATE BANK"),
#     ("NIFTYINFRA", "NIFTY INFRASTRUCTURE"), ("NIFTYMEDIA", "NIFTY MEDIA"),
#     ("FINNIFTY", "NIFTY FINANCIAL SERVICES"), ("NIFTYHEALTHCARE", "NIFTY HEALTHCARE INDEX"),
#     ("NIFTYCPSE", "NIFTY CPSE"),
# ]

SECTOR_INDICES_FOR_RECO = [
    (key, NSE_DISPLAY_MAP.get(key, key))
    for key, cat in NSE_INDEX_CATEGORIES.items()
    if cat in ("sectoral", "thematic") and key not in _RECO_SKIP
]

# --- Sector ETF Map ----------------------------------------------------------
# Maps sector index key -> list of ETFs tracking that sector.
# Used by recommendation engine to suggest ETF alternatives.

SECTOR_ETF_MAP = {
    "BANKNIFTY": ["BANKBEES"],
    "NIFTYIT": ["ITBEES"],
    "NIFTYPHARMA": ["PHARMABEES"],
    "NIFTYPSUBANK": ["PSUBNKBEES"],
    "NIFTYFMCG": ["FMCGIETF"],
    "NIFTYMETAL": ["METALIETF"],
    "NIFTYAUTO": ["NETFAUTO"],
}

# ═══════════════════════════════════════════════════════════
#  SECTOR COMPASS — ETF Universe + Sector-ETF Mapping
# ═══════════════════════════════════════════════════════════

# All NSE-traded sector/thematic ETFs with yfinance symbols
# Comprehensive list: 80+ ETFs across sectors, themes, broad market, commodities
COMPASS_ETF_UNIVERSE: dict[str, str] = {
    # ── Broad Market ──
    "NIFTYBEES": "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "BANKBEES": "BANKBEES.NS",
    "MON100": "MON100.NS",
    "NIFTY1": "NIFTY1.NS",
    "NETFNIF100": "NETFNIF100.NS",
    "UTINIFTETF": "UTINIFTETF.NS",
    "HDFCNIFETF": "HDFCNIFETF.NS",
    "LICNFNHGP": "LICNFNHGP.NS",
    "NEXT50": "NEXT50.NS",
    "MAFANG": "MAFANG.NS",
    # ── Sector ETFs ──
    "ITBEES": "ITBEES.NS",
    "PHARMABEES": "PHARMABEES.NS",
    "PSUBNKBEES": "PSUBNKBEES.NS",
    "FMCGIETF": "FMCGIETF.NS",
    "METALIETF": "METALIETF.NS",
    "NETFAUTO": "NETFAUTO.NS",
    "OILIETF": "OILIETF.NS",
    "CPSEETF": "CPSEETF.NS",
    "INFRAIETF": "INFRAIETF.NS",
    "CONSMETF": "CONSUMIETF.NS",
    "HEALTHIETF": "HEALTHIETF.NS",
    "PVTBANIETF": "PVTBANIETF.NS",
    "COMMOIETF": "COMMOIETF.NS",
    "REALTYIETF": "REALTYIETF.NS",
    "ENERGYIETF": "ENERGYIETF.NS",
    "MEDIAIETF": "MEDIAIETF.NS",
    "FINIETF": "FINIETF.NS",
    "TNIDETF": "TNIDETF.NS",
    "ALPHAETF": "ALPHAETF.NS",
    "HABORETF": "HABORETF.NS",
    "SETFNIF50": "SETFNIF50.NS",
    # ── Thematic / Strategy ETFs ──
    "DIVOPPBEES": "DIVOPPBEES.NS",
    "MOMETF": "MOMETF.NS",
    "MOM100": "MOM100.NS",
    "MOM30IETF": "MOM30IETF.NS",
    "MOMENTUM": "MOMENTUM.NS",
    "QUAL30IETF": "QUAL30IETF.NS",
    "LOWVOLIETF": "LOWVOLIETF.NS",
    "MOVALUE": "MOVALUE.NS",
    "GROWWETF": "GROWWETF.NS",
    "EQUAL50": "EQUAL50.NS",
    "EQWT50ETF": "EQWT50ETF.NS",
    "TOP10": "TOP10.NS",
    "DEFENETF": "DEFENETF.NS",
    "MFGIETF": "MFGIETF.NS",
    "MAKEINDIA": "MAKEINDIA.NS",
    "INDIAETF": "INDIAETF.NS",
    "MONIFTY500": "MONIFTY500.NS",
    "HNGSNGBEES": "HNGSNGBEES.NS",
    "NV20IETF": "NV20IETF.NS",
    "EVINDIA": "EVINDIA.NS",
    "CAPMARKET": "CAPMARKET.NS",
    "NIFTYTEES": "NIFTYTEES.NS",
    "HDFCSML250": "HDFCSML250.NS",
    "BFSI": "BFSI.NS",
    "CONSDURETF": "CONSDURETF.NS",
    "TECHIETF": "TECHIETF.NS",
    "TATAETF50": "TATAETF50.NS",
    # ── MidCap / SmallCap ──
    "MID150BEES": "MID150BEES.NS",
    "MIDCAPIETF": "MIDCAPIETF.NS",
    "SMALLCAPETF": "SMALLCAPETF.NS",
    "MIDQ50": "MIDQ50.NS",
    "MIDSELIETF": "MIDSELIETF.NS",
    "MIDCAPETF": "MIDCAPETF.NS",
    "MOSMALL250": "MOSMALL250.NS",
    "MOTILALM50": "MOTILALM50.NS",
    "SBIMCAP": "SBIMCAP.NS",
    "NIPMIDIETF": "NIPMIDIETF.NS",
    "ABSLNN50ET": "ABSLNN50ET.NS",
    # ── Commodity ETFs ──
    "GOLDBEES": "GOLDBEES.NS",
    "SILVERBEES": "SILVERBEES.NS",
    "GOLDIETF": "GOLDIETF.NS",
    "SILVERIETF": "SILVERIETF.NS",
    "AXISGOLD": "AXISGOLD.NS",
    "GOLDETF": "GOLDETF.NS",
    "HDFCGOLD": "HDFCGOLD.NS",
    "SBISILVER": "SBISILVER.NS",
    "GOLDSHARE": "GOLDSHARE.NS",
    # ── Debt / Liquid ETFs ──
    "LIQUIDCASE": "LIQUIDCASE.NS",
    "LIQUIDBEES": "LIQUIDBEES.NS",
    "LIQUIDIETF": "LIQUIDIETF.NS",
    "LIQUIDETF": "LIQUIDETF.NS",
    "ICICIB22": "ICICIB22.NS",
    "NETFGILT5Y": "NETFGILT5Y.NS",
    "GILT5YBEES": "GILT5YBEES.NS",
    "CPSEBOND": "CPSEBOND.NS",
    "BHARAT22": "BHARAT22.NS",
    # ── Sensex / BSE ETFs ──
    "SENSEXIETF": "SENSEXIETF.NS",
    "SENSEXBEES": "SENSEXBEES.NS",
    "UTISENSETF": "UTISENSETF.NS",
    # ── Factor / Strategy (newer) ──
    "HDFCVALUE": "HDFCVALUE.NS",
    "SBIETFQLTY": "SBIETFQLTY.NS",
    "MIDSMALL": "MIDSMALL.NS",
    "KOTAKNIFTY": "KOTAKNIFTY.NS",
    "SHARIABEES": "SHARIABEES.NS",
    # ── Additional Sector ETFs ──
    "KOTAKBKETF": "KOTAKBKETF.NS",
    "SETFNN50": "SETFNN50.NS",
    "UTINEXT50": "UTINEXT50.NS",
    # ── Bharat Bond Series ──
    "EBBETF0430": "EBBETF0430.NS",
    "EBBETF0431": "EBBETF0431.NS",
    "EBBETF0432": "EBBETF0432.NS",
    "EBBETF0433": "EBBETF0433.NS",
    # ── Additional Gilt / Debt ──
    "GSEC10YBEES": "GSEC10YBEES.NS",
    "LTGILTBEES": "LTGILTBEES.NS",
    # ── Additional Commodity ──
    "TATAGOLD": "TATAGOLD.NS",
    "KOTAKGOLD": "KOTAKGOLD.NS",
    "KOTAKSILVER": "KOTAKSILVER.NS",
    # ── International ──
    "N100": "N100.NS",
    "NASDAQ100": "NASDAQ100.NS",
    "MOUS500": "MOUS500.NS",
    "MASPTOP50": "MASPTOP50.NS",
    "MONQ50": "MONQ50.NS",
}

# Maps sector index key -> list of ETFs that track it (for compass)
COMPASS_SECTOR_ETF_MAP: dict[str, list[str]] = {
    "BANKNIFTY": ["BANKBEES"],
    "NIFTYIT": ["ITBEES", "TECHIETF"],
    "NIFTYPHARMA": ["PHARMABEES"],
    "NIFTYPSUBANK": ["PSUBNKBEES"],
    "NIFTYFMCG": ["FMCGIETF"],
    "NIFTYMETAL": ["METALIETF"],
    "NIFTYAUTO": ["NETFAUTO"],
    "NIFTYOILGAS": ["OILIETF"],
    "NIFTYCPSE": ["CPSEETF"],
    "NIFTYINFRA": ["INFRAIETF"],
    "NIFTYCONSUMPTION": ["CONSMETF"],
    "NIFTYHEALTHCARE": ["HEALTHIETF"],
    "NIFTYPVTBANK": ["PVTBANIETF"],
    "NIFTYCOMMODITIES": ["COMMOIETF"],
    "NIFTYREALTY": ["REALTYIETF"],
    "NIFTYENERGY": ["ENERGYIETF"],
    "NIFTYMEDIA": ["MEDIAIETF"],
    "FINNIFTY": ["FINIETF", "BFSI"],
    "NIFTYFINSERVICE": ["FINIETF"],
    "NIFTYCONSUMERDURABLES": ["CONSDURETF"],
    "NIFTYINDIADEFENCE": ["DEFENETF"],
    "NIFTYINDIAMFG": ["MFGIETF", "MAKEINDIA"],
    "NIFTYEVNEWAGE": ["EVINDIA"],
    "NIFTYCAPITALMARKETS": ["CAPMARKET"],
}

# Sector indices used by compass (all sectoral + thematic with sufficient history)
COMPASS_SECTOR_INDICES: list[tuple[str, str]] = [
    (key, NSE_DISPLAY_MAP.get(key, key))
    for key, cat in NSE_INDEX_CATEGORIES.items()
    if cat in ("sectoral", "thematic") and key not in _RECO_SKIP
]
