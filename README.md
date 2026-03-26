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

**Last updated**: 2026-03-27 01:20 (`233665e` on `planning-phase-1`)

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
| Total commits | 6 |
| Branches | 6 |
| Source files | 0 |
| Test files | 0 |

### Recent Activity

```
233665e fix: remove duplicate roadmap table and fix progress count display
612ddc5 chore: add proper gitignore for Next.js project
0473466 chore: add gitignore
8b11059 feat: add auto-updating README with post-commit hook
7ef554b docs: add project CLAUDE.md and PLAN.md for Phase 1 planning
5473147 Initial commit
```

<!-- AUTO-UPDATE:END -->

## Project Structure

See [CLAUDE.md](./CLAUDE.md) for full folder structure and conventions.
See [PLAN.md](./PLAN.md) for detailed Phase 1 feature breakdown.

## License

Private
