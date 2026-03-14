// ============================================================================
// Jhaveri Intelligence Platform — Constants
// Ported from dashboard.py (lines 629–738)
// ============================================================================

// Tracked NSE indices — only those with reliable yfinance historical data for all periods
// Names are exact nse_name values returned by nsetools or NSE_DISPLAY_MAP
export const TOP_25_INDICES: string[] = [
  "NIFTY 50",
  "NIFTY NEXT 50",
  "NIFTY BANK",
  "NIFTY FINANCIAL SERVICES",
  "NIFTY 200",
  "NIFTY 500",
  "NIFTY AUTO",
  "NIFTY FMCG",
  "NIFTY IT",
  "NIFTY METAL",
  "NIFTY PHARMA",
  "NIFTY PSU BANK",
  "NIFTY PRIVATE BANK",
  "NIFTY REALTY",
  "NIFTY ENERGY",
  "NIFTY INFRASTRUCTURE",
  "NIFTY MNC",
  "NIFTY PSE",
  "NIFTY SERVICES SECTOR",
  "NIFTY MIDCAP 150",
  "NIFTY SMALLCAP 250",
  "NIFTY MIDSMALLCAP 400",
  "NIFTY OIL & GAS",
  "NIFTY CHEMICALS",
  "NIFTY HEALTHCARE INDEX",
  "NIFTY INDIA DEFENCE",
  "NIFTY INDIA MANUFACTURING",
  "NIFTY MICROCAP 250",
];

// Non-NSE instruments served from DB (BSE, commodities, currencies)
// These use the internal key (index_name) not display name
export const NON_NSE_KEYS = new Set([
  "SENSEX", "BSE500", "GOLD", "SILVER", "CRUDEOIL", "COPPER", "USDINR",
]);

export const INDEX_SECTOR_MAP: Record<string, string> = {
  // Broad Market
  "NIFTY 50": "Broad Market",
  "NIFTY NEXT 50": "Broad Market",
  "NIFTY 100": "Broad Market",
  "NIFTY 200": "Broad Market",
  "NIFTY 500": "Broad Market",
  "NIFTY TOTAL MARKET": "Broad Market",
  "NIFTY MIDCAP SELECT": "Broad Market",
  "NIFTY500 MULTICAP 50:25:25": "Broad Market",
  "NIFTY LARGEMIDCAP 250": "Broad Market",
  // Banking & Financial
  "NIFTY BANK": "Banking & Financial",
  "NIFTY FINANCIAL SERVICES": "Banking & Financial",
  "NIFTY PSU BANK": "Banking & Financial",
  "NIFTY PRIVATE BANK": "Banking & Financial",
  "NIFTY FINANCIAL SERVICES 25/50": "Banking & Financial",
  "NIFTY FINANCIAL SERVICES EX-BANK": "Banking & Financial",
  "NIFTY MIDSMALL FINANCIAL SERVICES": "Banking & Financial",
  "NIFTY CAPITAL MARKETS": "Banking & Financial",
  // IT & Technology
  "NIFTY IT": "IT & Technology",
  "NIFTY MIDSMALL IT & TELECOM": "IT & Technology",
  "NIFTY INDIA DIGITAL": "IT & Technology",
  "NIFTY INDIA INTERNET": "IT & Technology",
  // Pharma & Healthcare
  "NIFTY PHARMA": "Pharma & Healthcare",
  "NIFTY HEALTHCARE INDEX": "Pharma & Healthcare",
  "NIFTY MIDSMALL HEALTHCARE": "Pharma & Healthcare",
  "NIFTY500 HEALTHCARE": "Pharma & Healthcare",
  // Auto & Mobility
  "NIFTY AUTO": "Auto & Mobility",
  "NIFTY EV & NEW AGE AUTOMOTIVE": "Auto & Mobility",
  "NIFTY MOBILITY": "Auto & Mobility",
  "NIFTY TRANSPORTATION & LOGISTICS": "Auto & Mobility",
  // Consumer & FMCG
  "NIFTY FMCG": "Consumer & FMCG",
  "NIFTY CONSUMER DURABLES": "Consumer & FMCG",
  "NIFTY INDIA CONSUMPTION": "Consumer & FMCG",
  "NIFTY INDIA NEW AGE CONSUMPTION": "Consumer & FMCG",
  "NIFTY MIDSMALL INDIA CONSUMPTION": "Consumer & FMCG",
  "NIFTY NON-CYCLICAL CONSUMER": "Consumer & FMCG",
  // Commodities & Energy
  "NIFTY METAL": "Commodities & Energy",
  "NIFTY ENERGY": "Commodities & Energy",
  "NIFTY OIL & GAS": "Commodities & Energy",
  "NIFTY COMMODITIES": "Commodities & Energy",
  "NIFTY CHEMICALS": "Commodities & Energy",
  // Infra & Realty
  "NIFTY REALTY": "Infra & Realty",
  "NIFTY INFRASTRUCTURE": "Infra & Realty",
  "NIFTY CORE HOUSING": "Infra & Realty",
  "NIFTY HOUSING": "Infra & Realty",
  "NIFTY INDIA INFRASTRUCTURE & LOGISTICS": "Infra & Realty",
  "NIFTY500 MULTICAP INFRASTRUCTURE 50:30:20": "Infra & Realty",
  // Mid & Small Cap
  "NIFTY MIDCAP 50": "Mid & Small Cap",
  "NIFTY MIDCAP 100": "Mid & Small Cap",
  "NIFTY MIDCAP 150": "Mid & Small Cap",
  "NIFTY SMALLCAP 250": "Mid & Small Cap",
  "NIFTY SMALLCAP 50": "Mid & Small Cap",
  "NIFTY SMALLCAP 100": "Mid & Small Cap",
  "NIFTY MIDSMALLCAP 400": "Mid & Small Cap",
  "NIFTY MICROCAP 250": "Mid & Small Cap",
  // Thematic
  "NIFTY MEDIA": "Thematic",
  "NIFTY MNC": "Thematic",
  "NIFTY CPSE": "Thematic",
  "NIFTY PSE": "Thematic",
  "NIFTY SERVICES SECTOR": "Thematic",
  "NIFTY INDIA MANUFACTURING": "Thematic",
  "NIFTY500 MULTICAP INDIA MANUFACTURING 50:30:20": "Thematic",
  "NIFTY INDIA DEFENCE": "Thematic",
  "NIFTY INDIA TOURISM": "Thematic",
  "NIFTY RURAL": "Thematic",
  "NIFTY INDIA RAILWAYS PSU": "Thematic",
  "NIFTY CONGLOMERATE 50": "Thematic",
  "NIFTY IPO": "Thematic",
  "NIFTY INDIA CORPORATE GROUP INDEX - TATA GROUP 25% CAP": "Thematic",
  "NIFTY INDIA SELECT 5 CORPORATE GROUPS (MAATR)": "Thematic",
  // Strategy & Factor
  "NIFTY ALPHA 50": "Strategy",
  "NIFTY50 VALUE 20": "Strategy",
  "NIFTY100 QUALITY 30": "Strategy",
  "NIFTY50 EQUAL WEIGHT": "Strategy",
  "NIFTY100 EQUAL WEIGHT": "Strategy",
  "NIFTY100 LOW VOLATILITY 30": "Strategy",
  "NIFTY200 QUALITY 30": "Strategy",
  "NIFTY200 MOMENTUM 30": "Strategy",
  "NIFTY200 ALPHA 30": "Strategy",
  "NIFTY200 VALUE 30": "Strategy",
  "NIFTY ALPHA LOW-VOLATILITY 30": "Strategy",
  "NIFTY MIDCAP150 QUALITY 50": "Strategy",
  "NIFTY MIDCAP150 MOMENTUM 50": "Strategy",
  "NIFTY500 MOMENTUM 50": "Strategy",
  "NIFTY DIVIDEND OPPORTUNITIES 50": "Strategy",
  "NIFTY GROWTH SECTORS 15": "Strategy",
  "NIFTY HIGH BETA 50": "Strategy",
  "NIFTY LOW VOLATILITY 50": "Strategy",
  "NIFTY QUALITY LOW-VOLATILITY 30": "Strategy",
  "NIFTY SMALLCAP250 QUALITY 50": "Strategy",
  "NIFTY SMALLCAP250 MOMENTUM QUALITY 100": "Strategy",
  "NIFTY MIDSMALLCAP400 MOMENTUM QUALITY 100": "Strategy",
  "NIFTY500 EQUAL WEIGHT": "Strategy",
  "NIFTY500 VALUE 50": "Strategy",
  "NIFTY500 QUALITY 50": "Strategy",
  "NIFTY500 LOW VOLATILITY 50": "Strategy",
  "NIFTY WAVES": "Strategy",
  "NIFTY TOP 10 EQUAL WEIGHT": "Strategy",
  "NIFTY TOP 15 EQUAL WEIGHT": "Strategy",
  "NIFTY TOP 20 EQUAL WEIGHT": "Strategy",
  "NIFTY500 MULTICAP MOMENTUM QUALITY 50": "Strategy",
  "NIFTY ALPHA QUALITY LOW-VOLATILITY 30": "Strategy",
  "NIFTY ALPHA QUALITY VALUE LOW-VOLATILITY 30": "Strategy",
  "NIFTY100 ALPHA 30": "Strategy",
  "NIFTY500 MULTIFACTOR MQVLV 50": "Strategy",
  "NIFTY500 FLEXICAP QUALITY 30": "Strategy",
  "NIFTY TOTAL MARKET MOMENTUM QUALITY 50": "Strategy",
  // Fixed Income
  "NIFTY 8-13 YR G-SEC": "Fixed Income",
  "NIFTY 10 YR BENCHMARK G-SEC": "Fixed Income",
  "NIFTY 10 YR BENCHMARK G-SEC (CLEAN PRICE)": "Fixed Income",
  "NIFTY 4-8 YR G-SEC INDEX": "Fixed Income",
  "NIFTY 11-15 YR G-SEC INDEX": "Fixed Income",
  "NIFTY 15 YR AND ABOVE G-SEC INDEX": "Fixed Income",
  "NIFTY COMPOSITE G-SEC INDEX": "Fixed Income",
  "NIFTY BHARAT BOND INDEX - APRIL 2030": "Fixed Income",
  "NIFTY BHARAT BOND INDEX - APRIL 2031": "Fixed Income",
  "NIFTY BHARAT BOND INDEX - APRIL 2032": "Fixed Income",
  "NIFTY BHARAT BOND INDEX - APRIL 2033": "Fixed Income",
  // Volatility
  "INDIA VIX": "Volatility",
  // BSE Indices
  "SENSEX": "BSE",
  "BSE 500": "BSE",
  "BSE500": "BSE",
  // Commodities (Global)
  "Gold (USD)": "Commodities",
  "GOLD": "Commodities",
  "Silver (USD)": "Commodities",
  "SILVER": "Commodities",
  "Crude Oil (USD)": "Commodities",
  "CRUDEOIL": "Commodities",
  "Copper (USD)": "Commodities",
  "COPPER": "Commodities",
  // Currency
  "USD/INR": "Currency",
  "USDINR": "Currency",
  // ESG & Shariah
  "NIFTY100 ESG SECTOR LEADERS": "ESG & Shariah",
  "NIFTY100 ESG": "ESG & Shariah",
  "NIFTY100 ENHANCED ESG": "ESG & Shariah",
  "NIFTY SHARIAH 25": "ESG & Shariah",
  "NIFTY50 SHARIAH": "ESG & Shariah",
  "NIFTY500 SHARIAH": "ESG & Shariah",
  // Leveraged / Derived
  "NIFTY50 TR 2X LEVERAGE": "Leveraged",
  "NIFTY50 PR 2X LEVERAGE": "Leveraged",
  "NIFTY50 TR 1X INVERSE": "Leveraged",
  "NIFTY50 PR 1X INVERSE": "Leveraged",
  "NIFTY50 DIVIDEND POINTS": "Leveraged",
  "NIFTY50 USD": "Leveraged",
};

export const SECTOR_ORDER: string[] = [
  "Broad Market",
  "Banking & Financial",
  "IT & Technology",
  "Pharma & Healthcare",
  "Auto & Mobility",
  "Consumer & FMCG",
  "Commodities & Energy",
  "Infra & Realty",
  "Mid & Small Cap",
  "Thematic",
  "Strategy",
  "Fixed Income",
  "Volatility",
  "ESG & Shariah",
  "Leveraged",
  "BSE",
  "Commodities",
  "Currency",
  "Other",
];

export const BASE_INDEX_OPTIONS = [
  "NIFTY",
  "SENSEX",
  "BANKNIFTY",
  "NIFTYIT",
  "NIFTYPHARMA",
  "NIFTYFMCG",
  "NIFTYAUTO",
  "NIFTYMETAL",
];

export const PERIOD_OPTIONS = ["1D", "1W", "1M", "3M", "6M", "12M"];

export const ACTION_OPTIONS = [
  "BUY",
  "SELL",
  "HOLD",
  "RATIO",
  "ACCUMULATE",
  "REDUCE",
  "SWITCH",
  "WATCH",
];

export const PRIORITY_OPTIONS = [
  { label: "Immediately", value: "IMMEDIATELY" },
  { label: "Within a Week", value: "WITHIN_A_WEEK" },
  { label: "Within a Month", value: "WITHIN_A_MONTH" },
];

// ─── Unified Sector Display Colors ──────────────────────
// Single source of truth for sector colors across the platform:
// holdings table badges, allocation pie, recommendation cards

interface SectorDisplayColor {
  bg: string;
  border: string;
  text: string;
  light: string;
  bar: string;
  hex: string;
}

const DEFAULT_SECTOR_COLOR: SectorDisplayColor = {
  bg: "bg-gray-50", border: "border-gray-300", text: "text-gray-600",
  light: "bg-gray-100", bar: "bg-gray-400", hex: "#9ca3af",
};

export const SECTOR_DISPLAY_COLORS: Record<string, SectorDisplayColor> = {
  "Banking":            { bg: "bg-blue-50",    border: "border-blue-300",    text: "text-blue-700",    light: "bg-blue-100",    bar: "bg-blue-400",    hex: "#2563eb" },
  "IT":                 { bg: "bg-violet-50",  border: "border-violet-300",  text: "text-violet-700",  light: "bg-violet-100",  bar: "bg-violet-400",  hex: "#7c3aed" },
  "Pharma":             { bg: "bg-pink-50",    border: "border-pink-300",    text: "text-pink-700",    light: "bg-pink-100",    bar: "bg-pink-400",    hex: "#db2777" },
  "Energy":             { bg: "bg-amber-50",   border: "border-amber-300",   text: "text-amber-700",   light: "bg-amber-100",   bar: "bg-amber-400",   hex: "#d97706" },
  "Auto":               { bg: "bg-cyan-50",    border: "border-cyan-300",    text: "text-cyan-700",    light: "bg-cyan-100",    bar: "bg-cyan-400",    hex: "#0891b2" },
  "FMCG":               { bg: "bg-green-50",   border: "border-green-300",   text: "text-green-700",   light: "bg-green-100",   bar: "bg-green-400",   hex: "#16a34a" },
  "Metal":              { bg: "bg-slate-100",  border: "border-slate-400",   text: "text-slate-700",   light: "bg-slate-200",   bar: "bg-slate-400",   hex: "#64748b" },
  "Realty":             { bg: "bg-orange-50",  border: "border-orange-300",  text: "text-orange-700",  light: "bg-orange-100",  bar: "bg-orange-400",  hex: "#ea580c" },
  "Infra":              { bg: "bg-stone-50",   border: "border-stone-300",   text: "text-stone-700",   light: "bg-stone-100",   bar: "bg-stone-400",   hex: "#78716c" },
  "Telecom":            { bg: "bg-indigo-50",  border: "border-indigo-300",  text: "text-indigo-700",  light: "bg-indigo-100",  bar: "bg-indigo-400",  hex: "#4f46e5" },
  "Media":              { bg: "bg-fuchsia-50", border: "border-fuchsia-300", text: "text-fuchsia-700", light: "bg-fuchsia-100", bar: "bg-fuchsia-400", hex: "#c026d3" },
  "Financial Services": { bg: "bg-teal-50",    border: "border-teal-300",    text: "text-teal-700",    light: "bg-teal-100",    bar: "bg-teal-400",    hex: "#0d9488" },
  "Healthcare":         { bg: "bg-lime-50",    border: "border-lime-300",    text: "text-lime-700",    light: "bg-lime-100",    bar: "bg-lime-400",    hex: "#65a30d" },
  "Consumer":           { bg: "bg-rose-50",    border: "border-rose-300",    text: "text-rose-700",    light: "bg-rose-100",    bar: "bg-rose-400",    hex: "#e11d48" },
  "Cash":               { bg: "bg-neutral-50", border: "border-neutral-300", text: "text-neutral-600", light: "bg-neutral-100", bar: "bg-neutral-400", hex: "#737373" },
  "Cash & Liquid":      { bg: "bg-neutral-50", border: "border-neutral-300", text: "text-neutral-600", light: "bg-neutral-100", bar: "bg-neutral-400", hex: "#737373" },
  "ETF":                { bg: "bg-sky-50",     border: "border-sky-300",     text: "text-sky-700",     light: "bg-sky-100",     bar: "bg-sky-400",     hex: "#0284c7" },
  "Index ETF":          { bg: "bg-sky-50",     border: "border-sky-300",     text: "text-sky-700",     light: "bg-sky-100",     bar: "bg-sky-400",     hex: "#0284c7" },
  "Gold ETF":           { bg: "bg-amber-50",   border: "border-amber-300",   text: "text-amber-700",   light: "bg-amber-100",   bar: "bg-amber-400",   hex: "#d97706" },
  "Silver ETF":         { bg: "bg-slate-50",   border: "border-slate-300",   text: "text-slate-600",   light: "bg-slate-100",   bar: "bg-slate-400",   hex: "#94a3b8" },
  "Other":              { bg: "bg-gray-50",    border: "border-gray-300",    text: "text-gray-600",    light: "bg-gray-100",    bar: "bg-gray-400",    hex: "#9ca3af" },
};

// Aliases for common variations
const SECTOR_ALIASES: Record<string, string> = {
  "Technology": "IT",
  "Metals": "Metal",
  "Infrastructure": "Infra",
};

/** Get Tailwind classes for a sector name (holdings badges, allocation bars) */
export function getSectorDisplayColor(name: string | null): SectorDisplayColor {
  if (!name) return DEFAULT_SECTOR_COLOR;
  return SECTOR_DISPLAY_COLORS[name]
    || SECTOR_DISPLAY_COLORS[SECTOR_ALIASES[name] ?? ""]
    || DEFAULT_SECTOR_COLOR;
}

/** Get hex color for Recharts pie slices */
export function getSectorHex(label: string): string {
  return getSectorDisplayColor(label).hex;
}

// Broad sector category for each sector key (used in recommendations table)
export const SECTOR_CATEGORY: Record<string, string> = {
  BANKNIFTY:       "Banking",
  NIFTYPVTBANK:    "Banking",
  NIFTYPSUBANK:    "Banking",
  FINNIFTY:        "Financial Services",
  NIFTYIT:         "Technology",
  NIFTYPHARMA:     "Pharma",
  NIFTYHEALTHCARE: "Healthcare",
  NIFTYFMCG:       "FMCG",
  NIFTYCONSUMER:   "Consumer",
  NIFTYAUTO:       "Auto",
  NIFTYMETAL:      "Metals",
  NIFTYENERGY:     "Energy",
  NIFTYINFRA:      "Infrastructure",
  NIFTYREALTY:     "Realty",
  NIFTYMEDIA:      "Media",
};

// Derive SECTOR_COLORS (NIFTY-keyed) from unified map via SECTOR_CATEGORY — recommendation components use this
export const SECTOR_COLORS: Record<string, { bg: string; border: string; text: string; light: string }> = (() => {
  const result: Record<string, { bg: string; border: string; text: string; light: string }> = {};
  for (const [key, category] of Object.entries(SECTOR_CATEGORY)) {
    const color = getSectorDisplayColor(category);
    result[key] = { bg: color.bg, border: color.border, text: color.text, light: color.light };
  }
  return result;
})();

// Derived helpers
export const TOP_25_SET = new Set(TOP_25_INDICES);

export function getSector(nseName: string): string {
  return INDEX_SECTOR_MAP[nseName] ?? "Other";
}
