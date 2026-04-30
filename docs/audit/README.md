# DataPulse — Audits

Read-only audit reports. For execution plans derived from these audits, see [`../plans/`](../plans/).

| Audit | Date | Scope |
|-------|------|-------|
| [project-audit-2026-04-21.md](./project-audit-2026-04-21.md) | 2026-04-21 | Full-project audit (security, architecture, code quality, tests, DB, DevOps, docs) |
| [bronze-audit.md](./bronze-audit.md) | 2026 | Bronze layer (raw ingest) |
| [silver-audit.md](./silver-audit.md) | 2026 | Silver layer (staging / dimensional) |
| [calculation-audit.md](./calculation-audit.md) | 2026-04-07 | Comprehensive cross-layer calculation audit (488 files, 62 findings) |
| [calculation-logic-audit.md](./calculation-logic-audit.md) | 2026-04-07 | Calculation logic narrative analysis (4 HIGH, 7 MOD, 6 LOW) |

## Related plans

Codename audit-execution plans live under [`../plans/completed/audits/`](../plans/completed/audits/):
- Dragon Roar — full project audit execution
- Iron Curtain — hardening
- Market Strike — competitive features
- Unlock the Vault — activate already-built features
