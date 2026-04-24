# Postmortem — `<short incident title>`

> **Blameless**. This document describes *what happened* and *what the system let happen*, never *who messed up*. If you are naming a person, rewrite as a system property.

File this within **48 hours** of P0/P1 resolution. Save to `docs/brain/incidents/YYYY-MM-DD-<slug>.md`. Link from the incident Slack thread.

---

## Summary

- **Date / time (UTC):** `<start> – <end>` (duration: `<minutes>`)
- **Severity:** P0 / P1 / P2
- **Authors:** `<name(s)>`
- **Reviewers:** `<name(s) who read this before publication>`
- **Status:** Draft / In review / Published

One paragraph, plain English: *what customers experienced, for how long, and what we did about it.* A teammate reading this six months from now should understand the stakes in 30 seconds.

## Impact

Quantify, don't adjective. Numbers beat "many" or "severe":

- Tenants affected: `<count>` of `<total>` (`<%>`)
- Requests failed: `<count>` between `<start>`–`<end>`
- Revenue at risk: `<EGP>` (checkout blocked? dashboards only?)
- Data integrity: none / at-risk / confirmed-loss (describe)
- External notifications: none / status page / email / regulator

## Timeline

All times UTC. Paste from `#datapulse-incidents` — verbatim beats reconstruction.

| Time | Event |
|---|---|
| 14:02 | First alert fires (PagerDuty: `api_error_rate_5m > 5%`) |
| 14:03 | `@oncall` acks, begins triage |
| 14:07 | `@oncall` identifies deploy of commit `abcd123` at 13:58 as likely cause |
| 14:09 | Rollback initiated via `make rollback` |
| 14:14 | Error rate returns to baseline |
| 14:20 | Declared resolved in channel |
| 14:45 | Root cause identified in staging: missing migration `111_webhooks.sql` |

## Root cause

What *system property* allowed the outage. Drill until "human error" is replaced by a specific gap. Examples of good root causes:

- The deploy workflow does not run `alembic check` against staging before promoting the image.
- RLS audit runs hourly but the window between audits is long enough for a misconfigured table to serve cross-tenant rows.
- The Paymob webhook handler retries on 5xx but not on 499 client-disconnect, leading to silent drops.

Examples of **bad** root causes (rewrite):
- "Engineer forgot to run the migration" → *The deploy workflow does not verify migrations are applied before routing traffic.*
- "Alert was missed" → *The alert delivery path (PagerDuty → Slack bridge) silently dropped events when the bridge restarted.*

## Contributing factors

Secondary gaps that made the incident worse or longer. Each one is a candidate action item:

- Rollback took 6 min because the previous image wasn't warm on the registry.
- Sentry alert title didn't include the endpoint, delaying triage.
- The runbook for this failure mode didn't exist; on-call had to read the code.

## What went well

Non-optional section. Calling out the good protects the team culture:

- Automated rollback worked on the first try.
- On-call acked within 60 s of the page.
- Read replica ([#693](https://github.com/ahmed-shaaban-94/Data-Pulse/pull/693)) kept the dashboard up even while checkout was down.

## Action items

Every action item has an **owner** and a **due date**. An AI without both is a wish, not a plan. Prefer items that remove a class of failure over items that fix one instance.

| # | Action | Owner | Due | Tracking issue |
|---|---|---|---|---|
| 1 | Add `alembic check` step to deploy-prod workflow before image promotion | @ahmed | 2026-05-01 | #NNN |
| 2 | Warm previous image on registry via post-deploy prefetch | @ahmed | 2026-05-08 | #NNN |
| 3 | Include endpoint tag in Sentry alert subject line | @ahmed | 2026-05-01 | #NNN |

Cap AI count at 5. More than 5 means the retro scope is too big; split by concern.

## Lessons learned

1–3 bullets. What will the next on-call do differently after reading this? If you can't answer that, the postmortem is incomplete.

- Always check `git log origin/main --since=2h` before deep-diving — recent deploys are the usual suspect.
- A passing `dbt test` run is not the same as migrations applied — they're separate gates that must both be green.

---

## Review

Before publishing, a reviewer who was **not** on the incident must read and sign off:

- [ ] Names of individuals removed; systems named instead.
- [ ] Timeline matches `#datapulse-incidents` scrollback.
- [ ] Every action item has owner + due date + tracking issue.
- [ ] "What went well" is non-empty.
- [ ] No customer PII or credentials in the doc.

Once all boxes check, change Status → Published and link from the next [on-call handoff](oncall.md#handoff).
