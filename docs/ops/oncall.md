# On-Call Rotation

> Who picks up the pager when something breaks.
> Companion docs: [postmortem template](postmortem-template.md), [DR drill](dr-drill.md), [key rotation](key-rotation.md), [main runbook](../RUNBOOK.md).

## Rotation

- **Weekly cadence**, Monday 09:00 Cairo → following Monday 09:00.
- One **primary** on-call and one **secondary**.
- Swap only via explicit handoff message in `#datapulse-oncall` with the next engineer's `ack`. Silence is not consent.
- Holidays, vacations, sickness → primary announces ≥48 h ahead and names a replacement in the same message. If no volunteer, tech lead reassigns.

## Responsibilities

On-call owns the runtime of DataPulse for the week:

- Respond to pages within **15 minutes** during business hours (09:00–21:00 Cairo) and **30 minutes** overnight.
- Triage: classify as P0/P1/P2 (see below), acknowledge, begin mitigation.
- Drive incidents to resolution — either fix yourself or coordinate the right people.
- Keep the incident channel (`#datapulse-incidents`) updated with status every 30 min while active.
- Within 48 h of a P0 or P1 resolution, file a blameless postmortem using [the template](postmortem-template.md).

## Severity and paging

| Sev | Definition | Example | Page who |
|---|---|---|---|
| **P0** | Production down, revenue blocked, data loss risk | POS checkout returns 500, DB unreachable, tenant data leaks across RLS | Primary **and** secondary, immediately |
| **P1** | Core feature broken for many tenants | Dashboard empty, pipeline failing every run, Clerk auth down | Primary |
| **P2** | Degraded but workaround exists | One slow endpoint, non-critical cron stuck | Primary, next business day OK |
| **P3** | Cosmetic / latent | Log noise, missing metric, minor UI bug | Not a page — open an issue |

## Escalation matrix

Follow this chain when primary can't resolve within the indicated wall-clock time. **Do not skip steps** unless life-safety or legal exposure is at stake.

| Minutes since page | Action |
|---|---|
| 0 | Primary acks, starts triage |
| 15 | If no ack, secondary pages primary on secondary channel (SMS) and takes co-ownership |
| 30 | If no ack, secondary owns the incident and pages the **tech lead** |
| 60 | Tech lead decides whether to page **CEO/founder** (customer-visible P0 only) |
| 90 | Tech lead + CEO decide on public status-page post and customer email |

Contact details live in `1Password → DataPulse Vault → On-call Contacts`. **Never paste a phone number into Git.**

## Pager setup checklist (per on-call)

- [ ] Slack `#datapulse-oncall` and `#datapulse-incidents` notifications **unmuted** for the week.
- [ ] PagerDuty (or equivalent) schedule shows your name for the week.
- [ ] Grafana and Sentry alert emails routed to your inbox.
- [ ] VPN access to staging + prod working (test before Monday).
- [ ] `gh auth status` works from your laptop for PR-driven rollbacks.
- [ ] Read [the last 5 postmortems](../brain/incidents/) — context matters more than any runbook.

## What to do first when paged

1. **Acknowledge.** In Slack: `ack @primary — investigating`. Starts the clock visibly.
2. **Check dashboards.** Grafana → DataPulse overview → any red. Sentry → spike in last 30 min.
3. **Check recent deploys.** `gh run list --workflow=deploy-prod.yml --limit 5`. If anything merged in the last hour, consider rollback before deep-diving.
4. **Rollback is cheap.** `make rollback IMAGE_TAG=v<previous>` reverts in <5 min. Use it liberally for P0 — investigate in staging afterward.
5. **Declare severity in channel.** One line: "P1 — checkout 500s, started ~14:02, investigating billing DB."

## Handoff

At end-of-week, post in `#datapulse-oncall`:

```
Handoff <date>:
- Pages this week: <count> (P0: <n>, P1: <n>, P2: <n>)
- Unresolved: <link-to-issue-or-"none">
- Recurring alerts: <noisy-signals-worth-tuning>
- Postmortems pending: <links-or-"none">
Next on-call: @<person>, please ack.
```

The incoming on-call replies with `ack` and the handoff is complete.

---

Reviewed quarterly alongside the [DR drill](dr-drill.md). Last review: see git blame.
