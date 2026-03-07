"""
Tests for price_service.py — pure data/mapping functions.

These tests cover ticker normalization, symbol mappings, and data constants
WITHOUT making actual API calls to Yahoo Finance or NSE.
"""


from price_service import (
    FALLBACK_MAP,
    NON_NSETOOLS_KEYS,
    NSE_DISPLAY_MAP,
    NSE_ETF_UNIVERSE,
    NSE_INDEX_KEYS,
    NSE_TICKER_MAP,
    SECTOR_ETF_MAP,
    SECTOR_INDICES_FOR_RECO,
    _safe_float,
    normalize_ticker,
    normalize_ticker_for_yfinance,
)

# ═══════════════════════════════════════════════════════════
#  TICKER NORMALIZATION
# ═══════════════════════════════════════════════════════════


class TestNormalizeTicker:
    """Tests for normalize_ticker (internal ticker -> Yahoo Finance symbol)."""

    def test_should_map_nifty_to_nsei(self):
        """NIFTY maps to ^NSEI (Yahoo Finance index symbol)."""
        assert normalize_ticker("NIFTY") == "^NSEI"

    def test_should_map_nifty50_to_nsei(self):
        """NIFTY50 is an alias for ^NSEI."""
        assert normalize_ticker("NIFTY50") == "^NSEI"

    def test_should_map_banknifty_to_nsebank(self):
        """BANKNIFTY maps to ^NSEBANK."""
        assert normalize_ticker("BANKNIFTY") == "^NSEBANK"

    def test_should_map_sensex_to_bsesn(self):
        """SENSEX maps to ^BSESN."""
        assert normalize_ticker("SENSEX") == "^BSESN"

    def test_should_map_gold_to_futures(self):
        """GOLD maps to GC=F (gold futures)."""
        assert normalize_ticker("GOLD") == "GC=F"

    def test_should_map_crudeoil_to_futures(self):
        """CRUDEOIL maps to CL=F (crude oil futures)."""
        assert normalize_ticker("CRUDEOIL") == "CL=F"

    def test_should_map_crude_alias_to_futures(self):
        """CRUDE is an alias for CL=F."""
        assert normalize_ticker("CRUDE") == "CL=F"

    def test_should_map_usdinr_to_forex(self):
        """USDINR maps to USDINR=X (forex pair)."""
        assert normalize_ticker("USDINR") == "USDINR=X"

    def test_should_map_indiavix_to_vix_index(self):
        """INDIAVIX maps to ^INDIAVIX."""
        assert normalize_ticker("INDIAVIX") == "^INDIAVIX"

    def test_should_add_ns_suffix_for_regular_stock(self):
        """Regular stock ticker gets .NS suffix for NSE."""
        assert normalize_ticker("RELIANCE") == "RELIANCE.NS"

    def test_should_add_ns_suffix_for_unknown_ticker(self):
        """Unknown ticker defaults to .NS suffix."""
        assert normalize_ticker("HDFCBANK") == "HDFCBANK.NS"

    def test_should_not_double_suffix_ns(self):
        """Ticker already ending in .NS should not get double suffix."""
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE.NS"

    def test_should_not_double_suffix_bo(self):
        """Ticker already ending in .BO should not get double suffix."""
        assert normalize_ticker("RELIANCE.BO") == "RELIANCE.BO"

    def test_should_preserve_caret_prefix(self):
        """Ticker starting with ^ should be returned as-is."""
        assert normalize_ticker("^NSEI") == "^NSEI"

    def test_should_preserve_equals_symbol(self):
        """Ticker with = (forex/futures) should be returned as-is."""
        assert normalize_ticker("USDINR=X") == "USDINR=X"

    def test_should_preserve_futures_suffix(self):
        """Ticker ending with =F (futures) should be returned as-is."""
        assert normalize_ticker("GC=F") == "GC=F"

    def test_should_handle_empty_string(self):
        """Empty string should return empty string."""
        assert normalize_ticker("") == ""

    def test_should_handle_case_insensitive_lookup(self):
        """Ticker lookup should be case-insensitive (uppercased internally)."""
        assert normalize_ticker("nifty") == "^NSEI"
        assert normalize_ticker("Banknifty") == "^NSEBANK"

    def test_should_strip_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        assert normalize_ticker("  NIFTY  ") == "^NSEI"

    def test_should_handle_colon_prefixed_ticker(self):
        """Ticker with exchange prefix (NSE:RELIANCE) should extract the symbol."""
        assert normalize_ticker("NSE:RELIANCE") == "RELIANCE.NS"

    def test_should_handle_niftybank_alias(self):
        """NIFTYBANK is an alias for BANKNIFTY => ^NSEBANK."""
        assert normalize_ticker("NIFTYBANK") == "^NSEBANK"

    def test_should_be_aliased_as_normalize_ticker_for_yfinance(self):
        """normalize_ticker_for_yfinance should be the same function."""
        assert normalize_ticker_for_yfinance("NIFTY") == normalize_ticker("NIFTY")
        assert normalize_ticker_for_yfinance("RELIANCE") == normalize_ticker("RELIANCE")


# ═══════════════════════════════════════════════════════════
#  NSE TICKER MAP COMPLETENESS
# ═══════════════════════════════════════════════════════════


class TestNseTickerMap:
    """Tests for the NSE_TICKER_MAP dictionary structure and completeness."""

    def test_should_contain_all_major_nse_broad_indices(self):
        """All major NSE broad market indices should be mapped."""
        broad_indices = ["NIFTY", "NIFTY50", "NIFTY100", "NIFTY200", "NIFTY500",
                         "NIFTYNEXT50", "NIFTYMIDCAP", "NIFTYSMALLCAP"]
        for idx in broad_indices:
            assert idx in NSE_TICKER_MAP, f"Missing broad index: {idx}"

    def test_should_contain_all_major_sectoral_indices(self):
        """Key sector indices should be mapped."""
        sectors = ["BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG",
                   "NIFTYAUTO", "NIFTYMETAL", "NIFTYREALTY", "NIFTYENERGY"]
        for idx in sectors:
            assert idx in NSE_TICKER_MAP, f"Missing sector index: {idx}"

    def test_should_contain_commodities(self):
        """Commodity tickers should be mapped to futures contracts."""
        assert NSE_TICKER_MAP["GOLD"] == "GC=F"
        assert NSE_TICKER_MAP["SILVER"] == "SI=F"
        assert NSE_TICKER_MAP["CRUDEOIL"] == "CL=F"
        assert NSE_TICKER_MAP["COPPER"] == "HG=F"

    def test_should_contain_currency_pairs(self):
        """Currency pairs should be mapped to forex symbols."""
        assert NSE_TICKER_MAP["USDINR"] == "USDINR=X"
        assert NSE_TICKER_MAP["EURINR"] == "EURINR=X"
        assert NSE_TICKER_MAP["GBPINR"] == "GBPINR=X"

    def test_should_contain_bse_indices(self):
        """BSE indices should be mapped."""
        assert "SENSEX" in NSE_TICKER_MAP
        assert "BSE500" in NSE_TICKER_MAP

    def test_all_values_should_be_strings(self):
        """All mapped values should be non-empty strings."""
        for key, value in NSE_TICKER_MAP.items():
            assert isinstance(value, str), f"{key} maps to non-string: {type(value)}"
            assert len(value) > 0, f"{key} maps to empty string"


# ═══════════════════════════════════════════════════════════
#  NSE INDEX KEYS
# ═══════════════════════════════════════════════════════════


class TestNseIndexKeys:
    """Tests for the NSE_INDEX_KEYS list (all tracked instruments)."""

    def test_should_contain_nifty(self):
        """NIFTY must be in the tracked indices."""
        assert "NIFTY" in NSE_INDEX_KEYS

    def test_should_contain_sensex(self):
        """SENSEX (BSE) must be tracked."""
        assert "SENSEX" in NSE_INDEX_KEYS

    def test_should_contain_gold(self):
        """GOLD commodity must be tracked."""
        assert "GOLD" in NSE_INDEX_KEYS

    def test_should_contain_usdinr(self):
        """USD/INR forex must be tracked."""
        assert "USDINR" in NSE_INDEX_KEYS

    def test_should_have_no_duplicates(self):
        """No duplicate entries in the index keys list."""
        assert len(NSE_INDEX_KEYS) == len(set(NSE_INDEX_KEYS))

    def test_all_index_keys_should_have_ticker_map_entry(self):
        """Every tracked index should have a corresponding NSE_TICKER_MAP entry."""
        for key in NSE_INDEX_KEYS:
            assert key in NSE_TICKER_MAP, (
                f"Index key '{key}' is tracked but has no NSE_TICKER_MAP entry"
            )

    def test_non_nsetools_keys_should_be_subset_of_index_keys(self):
        """NON_NSETOOLS_KEYS should all be in NSE_INDEX_KEYS."""
        for key in NON_NSETOOLS_KEYS:
            assert key in NSE_INDEX_KEYS, (
                f"NON_NSETOOLS_KEYS entry '{key}' is not in NSE_INDEX_KEYS"
            )


# ═══════════════════════════════════════════════════════════
#  ETF UNIVERSE
# ═══════════════════════════════════════════════════════════


class TestNseEtfUniverse:
    """Tests for the NSE_ETF_UNIVERSE mapping."""

    def test_should_contain_major_etfs(self):
        """Key broad market ETFs should be mapped."""
        assert "NIFTYBEES" in NSE_ETF_UNIVERSE
        assert "BANKBEES" in NSE_ETF_UNIVERSE
        assert "GOLDBEES" in NSE_ETF_UNIVERSE

    def test_should_map_niftybees_correctly(self):
        """NIFTYBEES maps to NIFTYBEES.NS."""
        assert NSE_ETF_UNIVERSE["NIFTYBEES"] == "NIFTYBEES.NS"

    def test_should_map_liquidcase_correctly(self):
        """LIQUIDCASE maps to LIQUIDCASE.NS."""
        assert NSE_ETF_UNIVERSE["LIQUIDCASE"] == "LIQUIDCASE.NS"

    def test_should_map_sensexetf_to_sensexietf(self):
        """SENSEXETF maps to SENSEXIETF.NS (note the I)."""
        assert NSE_ETF_UNIVERSE["SENSEXETF"] == "SENSEXIETF.NS"

    def test_should_map_netfmid150_to_mid150bees(self):
        """NETFMID150 maps to MID150BEES.NS."""
        assert NSE_ETF_UNIVERSE["NETFMID150"] == "MID150BEES.NS"

    def test_all_etf_symbols_should_end_with_ns(self):
        """All ETF Yahoo symbols should end with .NS (NSE listed)."""
        for etf, symbol in NSE_ETF_UNIVERSE.items():
            assert symbol.endswith(".NS"), (
                f"ETF '{etf}' symbol '{symbol}' does not end with .NS"
            )

    def test_should_have_no_duplicate_symbols(self):
        """No two ETFs should map to the same Yahoo symbol."""
        symbols = list(NSE_ETF_UNIVERSE.values())
        assert len(symbols) == len(set(symbols)), "Duplicate ETF symbols found"


# ═══════════════════════════════════════════════════════════
#  NSE DISPLAY MAP
# ═══════════════════════════════════════════════════════════


class TestNseDisplayMap:
    """Tests for the NSE display name mapping."""

    def test_should_map_nifty_to_nifty_50(self):
        """NIFTY internal key maps to display name 'NIFTY 50'."""
        assert NSE_DISPLAY_MAP["NIFTY"] == "NIFTY 50"

    def test_should_map_banknifty_to_nifty_bank(self):
        """BANKNIFTY maps to display name 'NIFTY BANK'."""
        assert NSE_DISPLAY_MAP["BANKNIFTY"] == "NIFTY BANK"

    def test_should_map_sensex_to_sensex(self):
        """SENSEX maps to itself."""
        assert NSE_DISPLAY_MAP["SENSEX"] == "SENSEX"

    def test_should_map_gold_to_gold_usd(self):
        """GOLD maps to 'Gold (USD)'."""
        assert NSE_DISPLAY_MAP["GOLD"] == "Gold (USD)"

    def test_should_map_usdinr_to_usd_inr(self):
        """USDINR maps to 'USD/INR'."""
        assert NSE_DISPLAY_MAP["USDINR"] == "USD/INR"

    def test_finnifty_and_niftyfinservice_should_have_same_display(self):
        """FINNIFTY and NIFTYFINSERVICE are aliases for the same index."""
        assert NSE_DISPLAY_MAP["FINNIFTY"] == NSE_DISPLAY_MAP["NIFTYFINSERVICE"]
        assert NSE_DISPLAY_MAP["FINNIFTY"] == "NIFTY FINANCIAL SERVICES"


# ═══════════════════════════════════════════════════════════
#  SECTOR ETF MAP
# ═══════════════════════════════════════════════════════════


class TestSectorEtfMap:
    """Tests for the sector-to-ETF mapping used by the recommendation engine."""

    def test_should_map_banknifty_to_bankbees(self):
        """Banking sector maps to BANKBEES ETF."""
        assert "BANKBEES" in SECTOR_ETF_MAP["BANKNIFTY"]

    def test_should_map_niftyit_to_itbees(self):
        """IT sector maps to ITBEES ETF."""
        assert "ITBEES" in SECTOR_ETF_MAP["NIFTYIT"]

    def test_should_map_niftypharma_to_pharmabees(self):
        """Pharma sector maps to PHARMABEES ETF."""
        assert "PHARMABEES" in SECTOR_ETF_MAP["NIFTYPHARMA"]

    def test_all_etf_values_should_be_lists(self):
        """All values in SECTOR_ETF_MAP should be lists."""
        for sector, etfs in SECTOR_ETF_MAP.items():
            assert isinstance(etfs, list), f"{sector} value is not a list"
            assert len(etfs) > 0, f"{sector} has empty ETF list"

    def test_all_sector_keys_should_exist_in_ticker_map(self):
        """All sector keys should be valid entries in NSE_TICKER_MAP."""
        for sector in SECTOR_ETF_MAP.keys():
            assert sector in NSE_TICKER_MAP, (
                f"Sector '{sector}' not found in NSE_TICKER_MAP"
            )


# ═══════════════════════════════════════════════════════════
#  SECTOR INDICES FOR RECO
# ═══════════════════════════════════════════════════════════


class TestSectorIndicesForReco:
    """Tests for the SECTOR_INDICES_FOR_RECO list used by recommendation engine."""

    def test_should_be_a_list_of_tuples(self):
        """Each entry should be a (key, display_name) tuple."""
        for entry in SECTOR_INDICES_FOR_RECO:
            assert isinstance(entry, tuple), f"Entry is not a tuple: {entry}"
            assert len(entry) == 2, f"Tuple should have 2 elements: {entry}"

    def test_should_contain_major_sectors(self):
        """Major sector internal keys should be present."""
        keys = [t[0] for t in SECTOR_INDICES_FOR_RECO]
        assert "BANKNIFTY" in keys
        assert "NIFTYIT" in keys
        assert "NIFTYPHARMA" in keys
        assert "NIFTYMETAL" in keys
        assert "NIFTYAUTO" in keys

    def test_display_names_should_match_nse_display_map(self):
        """Display names in SECTOR_INDICES_FOR_RECO should match NSE_DISPLAY_MAP."""
        for key, display_name in SECTOR_INDICES_FOR_RECO:
            if key in NSE_DISPLAY_MAP:
                assert display_name == NSE_DISPLAY_MAP[key], (
                    f"Display name mismatch for {key}: "
                    f"'{display_name}' vs '{NSE_DISPLAY_MAP[key]}'"
                )

    def test_should_have_15_sector_indices(self):
        """There should be exactly 15 sector indices for the recommendation engine."""
        assert len(SECTOR_INDICES_FOR_RECO) == 15


# ═══════════════════════════════════════════════════════════
#  FALLBACK MAP
# ═══════════════════════════════════════════════════════════


class TestFallbackMap:
    """Tests for the Yahoo Finance fallback symbol mapping."""

    def test_should_have_nsei_fallback(self):
        """^NSEI (NIFTY) should have a fallback symbol."""
        assert "^NSEI" in FALLBACK_MAP
        assert len(FALLBACK_MAP["^NSEI"]) > 0

    def test_should_have_nsebank_fallback(self):
        """^NSEBANK (Bank NIFTY) should have a BANKBEES fallback."""
        assert "^NSEBANK" in FALLBACK_MAP
        assert "BANKBEES.NS" in FALLBACK_MAP["^NSEBANK"]

    def test_all_fallback_values_should_be_lists(self):
        """All fallback values should be non-empty lists."""
        for key, fallbacks in FALLBACK_MAP.items():
            assert isinstance(fallbacks, list), f"{key} fallback is not a list"
            assert len(fallbacks) > 0, f"{key} has empty fallback list"


# ═══════════════════════════════════════════════════════════
#  _safe_float UTILITY
# ═══════════════════════════════════════════════════════════


class TestSafeFloat:
    """Tests for the _safe_float utility function."""

    def test_should_convert_integer_to_float(self):
        """Integer input should be converted to float."""
        assert _safe_float(42) == 42.0

    def test_should_convert_float_to_float(self):
        """Float input should be returned as-is."""
        assert _safe_float(3.14) == 3.14

    def test_should_convert_string_number_to_float(self):
        """Numeric string should be parsed to float."""
        assert _safe_float("123.45") == 123.45

    def test_should_handle_comma_formatted_string(self):
        """Indian comma-formatted number should be parsed correctly."""
        assert _safe_float("1,23,456.78") == 123456.78

    def test_should_handle_western_comma_format(self):
        """Western comma-formatted number should also work."""
        assert _safe_float("1,234,567.89") == 1234567.89

    def test_should_return_none_for_none(self):
        """None input should return None."""
        assert _safe_float(None) is None

    def test_should_return_none_for_empty_string(self):
        """Empty string should return None."""
        assert _safe_float("") is None

    def test_should_return_none_for_dash(self):
        """Dash character should return None."""
        assert _safe_float("-") is None

    def test_should_return_none_for_em_dash(self):
        """Em dash character should return None."""
        assert _safe_float("\u2014") is None

    def test_should_return_none_for_non_numeric_string(self):
        """Non-numeric string should return None."""
        assert _safe_float("abc") is None

    def test_should_handle_negative_number(self):
        """Negative number should be parsed correctly."""
        assert _safe_float("-123.45") == -123.45

    def test_should_handle_zero(self):
        """Zero should be returned as 0.0."""
        assert _safe_float(0) == 0.0
        assert _safe_float("0") == 0.0

    def test_should_strip_whitespace(self):
        """Leading/trailing whitespace should be stripped before parsing."""
        assert _safe_float("  123.45  ") == 123.45
