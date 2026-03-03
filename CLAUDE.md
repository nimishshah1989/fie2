# FIE v3 — Jhaveri Intelligence Platform

## What This Is
FastAPI backend + Next.js 16 frontend for Indian market intelligence, portfolio tracking, trading alert management, and sector recommendations. Deployed on AWS EC2 Mumbai.

---

## Architecture — MODULAR, NOT MONOLITHIC

### Backend (Python/FastAPI)
```
server.py              — Slim orchestrator ONLY (app setup, CORS, auth, scheduler, router mounting)
routers/
  alerts.py            — Webhook ingestion, alert CRUD, FM actions, performance, actionables
  indices.py           — Market data: EOD fetch, historical, live indices, period returns
  portfolios.py        — Portfolio CRUD, transactions, holdings, NAV, export, bulk import
  baskets.py           — Microbasket CRUD, CSV upload, live data, portfolio size
  recommendations.py   — Sector recommendation engine
  health.py            — Health check, status
services/
  portfolio_service.py — Live prices, XIRR, drawdown, NAV computation
  basket_service.py    — Basket NAV, backfill, constituent units
  claude_service.py    — Claude Vision & text analysis
  data_helpers.py      — Shared DB upsert helpers
models.py              — ALL SQLAlchemy models (single source of truth for DB schema)
price_service.py       — ALL price fetching (nsetools, yfinance, NSE API)
```

### Frontend (Next.js 16 / App Router)
```
web/src/
  app/                 — Pages (one folder per route)
  components/
    ui/                — shadcn/ui primitives (DO NOT MODIFY)
    portfolio/         — Portfolio feature components
    [feature]/         — Other feature-specific components
  hooks/               — Custom React hooks (data fetching, SWR wrappers)
  lib/
    constants.ts       — ALL constants, color systems, sector maps
    utils.ts           — Formatters, helpers
    types.ts           — Alert/index types
    portfolio-types.ts — Portfolio types
    portfolio-api.ts   — Portfolio API client
    api.ts             — Alert API client
```

---

## MANDATORY RULES — Read Before Writing ANY Code

### 1. File Size Limits
- **No file over 300 lines.** If a file is approaching 300, extract into a new module.
- `server.py` stays under 400 lines — it is an orchestrator, not a dumping ground.
- Router files: max 600 lines. If growing, split by sub-domain.
- Frontend components: max 250 lines. Extract sub-components.

### 2. No Duplicate Logic
- Price fetching: ONLY in `price_service.py`
- DB models: ONLY in `models.py`
- Sector colors: ONLY in `constants.ts` (use `getSectorDisplayColor` / `getSectorHex`)
- API base URL: ONLY from `NEXT_PUBLIC_API_URL` env var
- Never create a second source of truth for anything.

### 3. Single Responsibility
- Each router handles ONE domain (alerts, portfolios, indices, baskets, recommendations)
- Each service handles ONE concern (prices, portfolio math, basket math, Claude AI)
- Each frontend component does ONE thing
- If a function is used by 2+ routers, it goes in `services/` or `price_service.py`

### 4. New Feature Checklist
Before writing code for any new feature:
1. **Plan first** — use EnterPlanMode for anything touching 3+ files
2. **Check existing patterns** — read similar existing code before writing new code
3. **Identify the right file** — never create a new file if the logic belongs in an existing one
4. **Keep the same patterns** — if portfolios use SWR hooks, new features use SWR hooks too

### 5. Backend Conventions
- All endpoints in `routers/` — never add routes to `server.py`
- All Pydantic models defined in the router that uses them
- Use `Depends(get_db)` for database sessions — never create sessions manually
- Logging: `logger = logging.getLogger("fie_v3.<module>")` at top of each file
- Error handling: `HTTPException` for client errors, `logger.error` + raise for server errors

### 6. Frontend Conventions
- Data fetching: SWR hooks in `hooks/` directory (pattern: `use-<resource>.ts`)
- API calls: dedicated API client files in `lib/` (pattern: `<resource>-api.ts`)
- State: React useState/useCallback for local state. No global state library unless needed.
- Types: dedicated type files in `lib/` — never inline complex types

---

## UI DESIGN SYSTEM — MANDATORY

**Every frontend component MUST follow the Jhaveri Intelligence Platform design system.**
The full specification is in `~/.claude/skills/ui-design-system/SKILL.md`.

### Key Rules (non-negotiable)
- **Light theme ONLY** — page bg `slate-50`, cards `white`. NEVER dark backgrounds.
- **Primary color: teal-600** (`#0d9488`) — active states, primary buttons, positive accents
- **Font: Inter** — via Google Fonts. `font-mono tabular-nums` for ALL financial numbers.
- **Indian number formatting** — `₹1,00,000` (lakhs), `₹1,00,00,000` (crores). Use `formatPrice()` from `lib/utils.ts`.
- **Profit = emerald-600, Loss = red-600** — never reverse.
- **Cards: `rounded-xl border border-border`** — no heavy shadows, no gradients.
- **Loading: Skeleton components** — never spinners.
- **Empty states: centered message** with helpful description.
- **Hover actions: `opacity-0 group-hover:opacity-100`** pattern for edit/delete icons.

### Component Patterns
```tsx
// Stat card
<div className="bg-white rounded-xl border border-slate-200 p-5">
  <p className="text-sm text-slate-500">Label</p>
  <p className="text-2xl font-bold font-mono text-teal-600 mt-1">₹561.92 Cr</p>
</div>

// Data table header
<th className="text-xs font-semibold text-slate-400 uppercase tracking-wider">

// Status badge
<span className="bg-emerald-100 text-emerald-700 rounded-full px-2.5 py-0.5 text-xs font-medium">ACTIVE</span>

// Primary button
<Button className="bg-teal-600 text-white hover:bg-teal-700">Action</Button>
```

### Sector Color System
All sector colors come from `SECTOR_DISPLAY_COLORS` in `constants.ts`:
- Use `getSectorDisplayColor(name)` for Tailwind classes (badges, bars)
- Use `getSectorHex(label)` for Recharts hex colors (pie slices)
- Use `SECTOR_COLORS[key]` for NIFTY-keyed recommendation components
- NEVER hardcode sector colors in components

---

## SKILL USAGE — When to Consult Which Skill

Claude MUST consult the relevant skill before implementing features in these domains:

| Domain | Skill | When |
|--------|-------|------|
| Portfolio features | `portfolio-management` | Any portfolio CRUD, position tracking, rebalancing, performance |
| Price/market data | `market-data` | Any price fetching, caching, EOD pipeline, index tracking |
| Trading alerts | `trading-alerts` | Webhook processing, alert management, signal analysis |
| Financial math | `financial-calculations` | XIRR, CAGR, returns, tax, risk metrics |
| Charts/viz | `financial-charts` | Any Recharts or TradingView chart work |
| UI components | `ui-design-system` | ANY frontend component, page, or layout |
| Frontend patterns | `frontend-conventions` | React hooks, state management, component structure |
| API design | `api-patterns` | New endpoints, request/response shapes |
| Database | `database-patterns` | Schema changes, migrations, query patterns |
| Compliance | `sebi-compliance` | Anything touching client data, advice, audit trails |
| Reports/export | `reporting-export` | PDF generation, Excel export, scheduled reports |
| Mutual funds | `mutual-fund-intelligence` | NAV tracking, scheme analysis, fund comparison |
| Client mgmt | `client-management` | Client onboarding, KYC, CRM features |

---

## BUILD & DEPLOY

### Local Development
```bash
# Backend
python3 server.py                    # Starts on port 8000

# Frontend
cd web && pnpm dev                   # Starts on port 3000
```

### Pre-Commit Checks (run before every commit)
```bash
# Frontend: must pass build
cd web && pnpm run build

# Backend: must pass import check
python3 -c "import models; import server; print('OK')"
```

### Deployment
- Push to `main` triggers GitHub Actions CI/CD
- Builds Docker image → pushes to ECR → deploys to EC2 Mumbai
- App URL: `http://13.206.50.251:8000`

### Environment
- `FIE_API_KEY` — optional API key for protected endpoints
- `CORS_ORIGINS` — comma-separated allowed origins
- `DATABASE_URL` — PostgreSQL connection string (RDS)
- `ANTHROPIC_API_KEY` — for Claude chart analysis
- `NEXT_PUBLIC_API_URL` — backend URL for frontend

---

## DATA FLOW

### Startup Sequence (background, non-blocking)
1. `init_db()` — create tables
2. Backfill 1Y indices (yfinance)
3. Backfill 1Y ETFs
4. Backfill portfolio instrument prices (from inception)
5. Backfill alert ticker prices (APPROVED + PENDING)
6. Backfill basket constituent prices + NAV
7. Fetch sector index constituents (NSE API) + 1Y stock prices

### Scheduled EOD (3:30 PM IST daily)
Same sequence as startup, targeting latest day's data.

### Price Sources (priority order)
1. **nsetools** — live NSE index prices (135+ indices)
2. **yfinance** — historical OHLCV, ETF prices, fallback for indices
3. **NSE API** — sector index constituents
4. **DB cache** — 60s TTL for live prices via httpx

---

## GIT CONVENTIONS

- Format: `type(scope): description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`
- Scope: `portfolio`, `alerts`, `pulse`, `baskets`, `reco`, `deploy`, `ui`
- Always include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- Commit after every working module — small, incremental commits
- Never commit `.env`, credentials, or `__pycache__`
