# DataPulse — Documentation

## Structure

```
docs/
├── README.md                  ← You are here
├── ARCHITECTURE.md            # System architecture (Mermaid diagrams, ERD, deployment)
├── RUNBOOK.md                 # Operations procedures
├── CLAUDE_REFERENCE.md        # Tech stack, directory tree, schemas, agents, roadmap
├── PLATFORM_MATRIX.md         # Authoritative surface/platform status
│
├── plans/                     # Project plans
│   ├── README.md              #   Master index
│   ├── active/                #   Active / in-flight plans
│   ├── sprints/               #   Dated sprint plans
│   ├── specs/                 #   Design specifications
│   ├── future/                #   Future phase roadmap (Phase 5–10)
│   └── completed/             #   Historical plans (and audits/ codename plans)
│
├── audit/                     # Codebase audits (project, bronze, silver, calculation)
├── reports/                   # Reviews, analyses, post-mortems
├── ops/                       # Operations runbooks (oncall, key rotation, DR drill)
├── adr/                       # Architecture Decision Records
├── design/                    # UX/UI designs (POS terminal, POS v9)
├── team-configs/              # Per-role CLAUDE.md configs
├── pharma-expansion/          # Pharma vertical expansion notes
├── brain/                     # Obsidian vault (decisions, incidents, sessions)
├── CONVENTIONS/               # Engineering conventions
└── assets/                    # Presentations, diagrams
```

## Quick Links

- **[Plans Index](./plans/README.md)** — All active, sprint, future, and completed plans
- **[Audits](./audit/)** — Project, bronze, silver, calculation audits
- **[Reports](./reports/)** — Project reviews, post-mortems, deep analyses
- **[ADR](./adr/)** — Architecture decision records
- **[Ops](./ops/)** — Disaster recovery, on-call, key rotation
- **[CLAUDE.md](../CLAUDE.md)** — Project rules and entry point
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** — Development guide
