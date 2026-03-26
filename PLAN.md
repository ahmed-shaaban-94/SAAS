# DataPulse — Phase 1 Plan (MVP)

> Business/Sales Analytics Dashboard SaaS
> Pipeline: Import -> Clean -> Analyze -> Dashboard

---

## Phase 1.1: Foundation

**Goal**: Skeleton app with auth, navigation, and database ready.

### Tasks
- [ ] Initialize Next.js 14 project with TypeScript, Tailwind CSS, App Router
- [ ] Install and configure shadcn/ui (default theme) with base components: button, input, card, dialog, dropdown-menu, toast, tabs, table, badge, skeleton, sheet, separator, label, form, select, popover, command
- [ ] Install core dependencies: zustand, zod, react-hook-form, @hookform/resolvers, sonner, lucide-react, date-fns
- [ ] Create Supabase project and configure `.env.local`
- [ ] Run database migrations:
  - `001_organizations.sql` — organizations + profiles tables
  - `002_datasets.sql` — datasets + dataset_rows tables
  - `003_cleaning_operations.sql` — cleaning operations table
  - `004_dashboards.sql` — dashboards + dashboard_widgets tables
  - `005_rls_policies.sql` — RLS policies on all tables
- [ ] Configure Supabase Storage bucket `raw-files` (private, 50MB limit)
- [ ] Create Supabase client helpers: `src/lib/supabase/client.ts`, `server.ts`, `middleware.ts`
- [ ] Generate TypeScript types from Supabase schema
- [ ] Build auth pages: login (`/login`), signup (`/signup` — creates org + profile)
- [ ] Add auth middleware: protect all `/(app)/*` routes
- [ ] Build app shell layout: sidebar + topbar + breadcrumbs
- [ ] Define TypeScript types: `dataset.ts`, `cleaning.ts`, `analysis.ts`, `dashboard.ts`

### Deliverable
User can sign up, log in, and see the app shell with sidebar navigation.

---

## Phase 1.2: Data Import

**Goal**: Upload CSV/Excel, preview, and persist to database.

### Tasks
- [ ] Install papaparse and xlsx (SheetJS)
- [ ] Build CSV parser wrapper (`src/lib/parsers/csv-parser.ts`) — streaming, encoding detection
- [ ] Build Excel parser wrapper (`src/lib/parsers/excel-parser.ts`) — read first sheet, handle multiple sheets
- [ ] Build type detector (`src/lib/parsers/type-detector.ts`) — sample first 100 rows, infer column types
- [ ] Install @tanstack/react-table
- [ ] Build import UI components:
  - File dropzone (drag-and-drop, file type + size validation)
  - Import preview table (first 100 rows)
  - Column selector (include/exclude columns)
  - Type detector badges (show detected type with override)
- [ ] Build import wizard page (`/datasets/new`) — multi-step: Upload -> Preview -> Confirm
- [ ] Create Zustand import store (file, parsed data, columns, selected columns, detected types)
- [ ] Build API route: POST `/api/datasets` — create dataset metadata, upload raw file to Storage, batch-insert rows (1K chunks with progress)
- [ ] Build dataset list page (`/datasets`) — name, row count, status, date
- [ ] Build dataset detail page (`/datasets/[id]`) — paginated data table + column schema
- [ ] Build API route: GET `/api/datasets/[id]/rows` — paginated rows (limit/offset)

### Deliverable
User uploads CSV/Excel, previews data, imports it, and sees it in a paginated table.

---

## Phase 1.3: Data Cleaning

**Goal**: Interactive cleaning workspace with undo support.

### Tasks
- [ ] Build cleaning logic modules:
  - `missing-values.ts` — detect nulls, fill strategies (value, mean, median, mode), drop rows
  - `duplicates.ts` — find duplicates by key columns, mark for removal
  - `type-cast.ts` — cast string to number/date with error handling
  - `operations.ts` — orchestrator: apply operation, return affected row IDs + count
- [ ] Build API route: POST `/api/datasets/[id]/clean` — apply operation, update rows, record in cleaning_operations
- [ ] Build cleaning workspace page (`/datasets/[id]/clean`) — split view: sidebar + data preview
- [ ] Build cleaning UI components:
  - Cleaning sidebar (list of available operations)
  - Missing values panel (select column, see null count, pick strategy)
  - Duplicates panel (select key columns, preview duplicates, confirm)
  - Type cast panel (select column, pick target type, preview)
  - Rename column dialog
  - Operation log (applied operations with undo button)
- [ ] Create Zustand cleaning store (current operation, preview data, operation history)
- [ ] Implement undo: delete last operation + replay remaining from raw data

### Deliverable
User cleans data interactively with undo, sees before/after stats.

---

## Phase 1.4: Data Analysis

**Goal**: Aggregation, grouping, filtering, pivot, and statistics.

### Tasks
- [ ] Build analysis engine (server-side SQL on JSONB):
  - `aggregations.ts` — build SQL for SUM, AVG, MIN, MAX, COUNT using JSONB operators
  - `grouping.ts` — GROUP BY with JSONB field extraction
  - `filtering.ts` — WHERE clause builder from filter config
  - `statistics.ts` — per-column descriptive stats (mean, median, std dev, min, max, null count, unique count)
  - `pivot.ts` — pivot query using conditional aggregation
- [ ] Install simple-statistics
- [ ] Build API route: POST `/api/datasets/[id]/analyze` — receives query config, builds SQL, returns results
- [ ] Build API route: GET `/api/datasets/[id]/export` — export filtered/aggregated results as CSV
- [ ] Build analysis workspace page (`/datasets/[id]/analyze`)
- [ ] Build analysis UI components:
  - Aggregation builder (pick columns + functions)
  - Group-by picker (multi-select columns)
  - Filter builder (column, operator, value conditions)
  - Results table
  - Stats card (per-column statistics)
  - Pivot table (row dimension, column dimension, value + aggregation)
- [ ] Create Zustand analysis store (query config, results, loading state)

### Deliverable
User runs aggregations, groups data, filters, views statistics, and exports results.

---

## Phase 1.5: Dashboard & Visualization

**Goal**: Create interactive dashboards with drag-and-drop chart widgets.

### Tasks
- [ ] Install recharts, react-grid-layout, html-to-image, jspdf
- [ ] Build chart components (with chart-container wrapper for loading/error/empty states):
  - Bar chart (horizontal + vertical, grouped + stacked)
  - Line chart (single + multi-line)
  - Pie chart (pie + donut)
  - Scatter chart
  - Area chart
  - KPI card (big number + trend indicator)
- [ ] Build dashboard grid (`dashboard-canvas.tsx`) — responsive, drag-and-drop in edit mode, static in view mode (dynamic import with `ssr: false`)
- [ ] Build chart widget component — renders chart based on config, fetches its own data
- [ ] Build chart builder dialog — multi-step: Pick type -> Configure axes/aggregation/groupBy -> Colors/title -> Preview
- [ ] Build global filter bar — column filters propagating to all widgets
- [ ] Build widget toolbar — edit, delete, duplicate actions
- [ ] Build dashboard CRUD:
  - API: GET/POST `/api/dashboards`, GET/PUT/DELETE `/api/dashboards/[id]`
  - Dashboard list page (`/dashboards`)
  - Create dashboard page (`/dashboards/new` — pick name + dataset)
  - View mode (`/dashboards/[id]`)
  - Edit mode (`/dashboards/[id]/edit`)
- [ ] Create Zustand dashboard store (layout, widgets, global filters, dirty state, save action)
- [ ] Build export utilities: `exportChartAsPng()`, `exportDashboardAsPdf()`
- [ ] Add light/dark theme support for dashboards

### Deliverable
User creates dashboards with multiple chart types, drag-and-drop layout, global filters, and export.

---

## Phase 1.6: Polish & Testing

**Goal**: Error handling, edge cases, tests, documentation.

### Tasks
- [ ] Add global error boundary component
- [ ] Add API route error wrapper (consistent error response format)
- [ ] Add skeleton loaders for tables, charts, lists
- [ ] Add progress bar for file import (batch progress)
- [ ] Add Zod schemas for all API inputs
- [ ] Add file type/size validation before upload
- [ ] Install vitest, @testing-library/react, @testing-library/jest-dom
- [ ] Write unit tests: parsers, type detector, cleaning operations, analysis builders, format utilities
- [ ] Write integration tests: API routes (datasets CRUD, cleaning, analysis)
- [ ] Install Playwright and write E2E tests: signup -> upload -> clean -> analyze -> dashboard
- [ ] Verify 80%+ coverage on `src/lib/`
- [ ] Write README.md with setup instructions
- [ ] Create `.env.local.example` with all required variables

### Deliverable
Production-ready MVP with comprehensive error handling and test coverage.

---

## Database Schema Summary

| Table | Purpose |
|-------|---------|
| `organizations` | Multi-tenant foundation (id, name, slug) |
| `profiles` | User profiles (id, org_id, full_name, role) |
| `datasets` | Uploaded datasets (id, org_id, name, file_path, column_schema, status) |
| `dataset_rows` | Data rows as JSONB (id, dataset_id, row_index, data, is_deleted) |
| `cleaning_operations` | Immutable operation log (id, dataset_id, operation_type, config, sort_order) |
| `dashboards` | Saved dashboards (id, org_id, dataset_id, name, layout, global_filters, theme) |
| `dashboard_widgets` | Chart widget configs (id, dashboard_id, widget_type, config) |

All tables have RLS policies keyed to `organization_id` via the `profiles` table.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File parsing | Client-side | Immediate preview, no server upload for parsing |
| Data analysis | Server-side SQL | PostgreSQL handles aggregations on JSONB efficiently |
| Data storage | JSONB rows | Dynamic schemas without DDL per dataset |
| Client state | Zustand | Lightweight, immutable-friendly |
| Dashboard grid | react-grid-layout | Drag/resize, serializable layout |
| Charts | Recharts | React-native, composable, responsive |

---

## Success Criteria

- [ ] User can sign up, create an organization, and log in
- [ ] User can upload CSV and Excel files up to 50MB
- [ ] User can preview data before importing
- [ ] Imported data appears in a paginated, sortable table
- [ ] User can apply at least 5 cleaning operations with undo
- [ ] User can run aggregations with group-by and filters
- [ ] User can view per-column statistics
- [ ] User can create a dashboard with at least 4 chart types
- [ ] Dashboard supports drag-and-drop layout with resize
- [ ] Global filters propagate to all charts on a dashboard
- [ ] Dashboard can be exported as PNG or PDF
- [ ] All data is tenant-isolated via RLS
- [ ] Core library modules have 80%+ test coverage
