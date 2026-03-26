# DataPulse

> Business/Sales Analytics SaaS -- A Power BI-like dashboard for importing, cleaning, analyzing, and visualizing business data.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS + shadcn/ui |
| Backend | Supabase (Auth + PostgreSQL + Storage) |
| Charts | Recharts |
| Dashboard Grid | react-grid-layout |
| State | Zustand |
| Validation | Zod |
| Testing | Vitest + Playwright |

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm
- Supabase account

### Setup

```bash
# Clone the repository
git clone https://github.com/ahmed-shaaban-94/SAAS.git
cd SAAS

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your Supabase credentials

# Run database migrations
npx supabase db push

# Start development server
npm run dev
```

### Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Pipeline

```
Upload CSV/Excel --> Clean Data --> Analyze --> Build Dashboard
```

## Roadmap

| Phase | Description |
|-------|-------------|
| 2 | Automation (n8n) |
| 3 | AI Analysis (LangGraph) |
| 4 | Website Expansion |

> Phase 1 status is auto-updated below after every commit.

<!-- AUTO-UPDATE:START -->
<!-- This section is auto-updated by scripts/update-readme.sh on every commit -->

## Project Status

**Last updated**: 2026-03-27 01:28 (`3248c0b` on `main`)

### Overall Progress

```
[--------------------] 0% (0/74 tasks)
```

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1.1 | Foundation | Planned |
| 1.2 | Data Import | Planned |
| 1.3 | Data Cleaning | Planned |
| 1.4 | Data Analysis | Planned |
| 1.5 | Dashboard & Viz | Planned |
| 1.6 | Polish & Testing | Planned |

### Stats

| Metric | Value |
|--------|-------|
| Total commits | 12 |
| Branches | 6 |
| Source files | 0 |
| Test files | 0 |

### Recent Activity

```
3248c0b merge: integrate planning-phase-1 into main (CLAUDE.md, PLAN.md, README.md)
99b4fd9 feat: add bronze layer — Excel sales data import pipeline (medallion architecture)
5477336 fix: remove duplicate roadmap table and fix progress count display
3795f74 feat: add pgAdmin + Jupyter, fix dbt gitignore
042d6bb feat: add dbt-core + dbt-postgres to the pipeline
87e1aed feat: add Python app container to Docker Compose
c987e69 feat: foundation phase 1.1 — Python env + import pipeline
612ddc5 chore: add proper gitignore for Next.js project
0473466 chore: add gitignore
8b11059 feat: add auto-updating README with post-commit hook
```

<!-- AUTO-UPDATE:END -->

## Project Structure

See [CLAUDE.md](./CLAUDE.md) for full folder structure and conventions.
See [PLAN.md](./PLAN.md) for detailed Phase 1 feature breakdown.

## License

Private
