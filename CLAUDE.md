# DataPulse — Business/Sales Analytics SaaS

## Project Overview

A Power BI-like analytics dashboard where users upload CSV/Excel files, clean data interactively, run aggregations and statistics, then build interactive dashboards with drag-and-drop chart layouts.

**Pipeline**: Import -> Clean -> Analyze -> Dashboard

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui (Radix primitives) |
| Icons | lucide-react |
| Backend | Supabase (Auth + PostgreSQL + Storage) |
| State (client) | Zustand |
| State (server) | Supabase queries via custom hooks |
| Validation | Zod |
| Forms | react-hook-form + @hookform/resolvers |
| Charts | Recharts |
| Dashboard Grid | react-grid-layout |
| Data Table | @tanstack/react-table |
| CSV Parsing | papaparse |
| Excel Parsing | xlsx (SheetJS) |
| Statistics | simple-statistics |
| Export PNG | html-to-image |
| Export PDF | jspdf |
| Toasts | sonner |
| Date Utils | date-fns |
| Testing | Vitest + @testing-library/react + Playwright |

## Folder Structure

```
src/
├── app/
│   ├── (auth)/           # Login, signup (public routes)
│   ├── (app)/            # Protected routes (sidebar layout)
│   │   ├── datasets/     # Upload, list, detail, clean, analyze
│   │   ├── dashboards/   # List, create, view, edit
│   │   └── settings/     # Account/org settings
│   └── api/              # API routes (datasets, dashboards)
├── components/
│   ├── ui/               # shadcn/ui primitives
│   ├── layout/           # Sidebar, topbar, breadcrumbs
│   ├── import/           # File dropzone, preview table, column selector
│   ├── cleaning/         # Cleaning operations UI
│   ├── analysis/         # Aggregation builder, filters, stats
│   ├── dashboard/        # Canvas, widget, chart builder
│   ├── charts/           # Bar, line, pie, scatter, area, KPI card
│   └── shared/           # Data table, empty state, loading skeleton
├── lib/
│   ├── supabase/         # client.ts, server.ts, middleware.ts, storage.ts
│   ├── parsers/          # csv-parser.ts, excel-parser.ts, type-detector.ts
│   ├── cleaning/         # operations.ts, missing-values.ts, duplicates.ts
│   ├── analysis/         # aggregations.ts, grouping.ts, filtering.ts, statistics.ts
│   ├── utils/            # format.ts, export.ts, validators.ts
│   └── constants.ts
├── hooks/                # use-dataset.ts, use-auth.ts, use-dashboard.ts, etc.
├── stores/               # Zustand stores (import, cleaning, analysis, dashboard)
└── types/                # dataset.ts, cleaning.ts, analysis.ts, dashboard.ts, supabase.ts
```

## Conventions

### Routing
- Route groups: `(auth)` for public auth pages, `(app)` for protected pages
- Auth middleware in `src/middleware.ts` — redirects unauthenticated users to `/login`
- API routes under `src/app/api/` — RESTful endpoints

### Supabase
- Browser client: `src/lib/supabase/client.ts`
- Server client: `src/lib/supabase/server.ts`
- All tables have RLS policies keyed to `organization_id`
- Generated types: `src/types/supabase.ts` via `supabase gen types typescript`

### State Management
- **Client state** (wizard steps, editor state): Zustand stores in `src/stores/`
- **Server state** (datasets, dashboards): Custom hooks wrapping Supabase queries
- **URL state** (filters, active tab): Next.js searchParams
- Immutable patterns — always create new objects, never mutate

### Data Model
- Dynamic dataset schemas via JSONB (`dataset_rows.data` column)
- Column schema stored in `datasets.column_schema` as JSON array
- Cleaning operations recorded as immutable log entries with sort order

### Code Style
- Strict TypeScript — no `any`, explicit return types on exported functions
- Zod schemas for all API input validation
- react-hook-form + Zod resolvers for all forms
- Small files (200-400 lines), extract when approaching 800
- Functions < 50 lines, no nesting > 4 levels
- Error handling at every level — never swallow errors silently

### Documentation Language
- Code and docs: English
- Inline comments: Arabic where helpful for clarity (mixed)

### Testing
- Unit tests: Vitest + Testing Library (`src/lib/` modules)
- Integration tests: API route testing
- E2E tests: Playwright (critical user flows)
- Target: 80%+ coverage on `src/lib/`

## Database

PostgreSQL via Supabase with 6 core tables:
- `organizations` — multi-tenant foundation
- `profiles` — user profiles linked to auth.users and organizations
- `datasets` + `dataset_rows` — uploaded data with JSONB dynamic schema
- `cleaning_operations` — immutable log of data cleaning steps
- `dashboards` + `dashboard_widgets` — saved dashboard layouts and chart configs

## Performance Limits (Phase 1)

| Limit | Value |
|-------|-------|
| Max file size | 50 MB |
| Max rows per dataset | 100,000 |
| Max columns | 100 |
| Max widgets per dashboard | 20 |
| Batch insert size | 1,000 rows |

## Future Phases

- **Phase 2**: Automation via n8n workflows
- **Phase 3**: AI-powered analysis via LangGraph
- **Phase 4**: Public website / landing page expansion
