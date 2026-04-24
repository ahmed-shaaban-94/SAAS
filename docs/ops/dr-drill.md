# Disaster Recovery Drill

> Quarterly rehearsal. Verify the backup you never tested is actually restorable, and that the people restoring it know the steps without reading the main [DR runbook](../disaster-recovery.md).
>
> Schedule: first Saturday of Jan / Apr / Jul / Oct. On-call leads, tech lead observes.

## Targets

| Metric | Target | How we measure |
|---|---|---|
| RTO (Recovery Time Objective) | < 30 min | Timer starts at "production DB lost" in drill script, stops when `GET /health` returns 200 on the restored instance |
| RPO (Recovery Point Objective) | < 24 h | `max(backup age) at moment of loss` — pulled from the `backup.sh` log |

A drill **passes** only when both targets are met end-to-end and a reviewer (not the driver) confirms the restored DB contains the expected row counts for `bronze.sales`, `pos.transactions`, and all active-tenant schemas.

## Pre-drill checklist (the week before)

- [ ] Confirm there's a backup ≤ 24 h old on the DR storage bucket (`aws s3 ls $DR_BUCKET | tail`).
- [ ] Provision a clean staging instance (`terraform apply` or the one-shot compose-up).
- [ ] Post in `#datapulse-ops`: "DR drill Saturday <date> 10:00 Cairo. No prod changes. Observers welcome."
- [ ] Print or bookmark the main [DR runbook](../disaster-recovery.md).

## Drill script

Timer starts at step 1. Do not open the DR runbook until step 4 — the point is to surface gaps in recall.

### 1. Declare the scenario

Driver announces in `#datapulse-ops`:

```
DRILL START <UTC time>. Scenario: production primary Postgres is unrecoverable.
Goal: RTO < 30 min, RPO < 24 h.
No prod traffic will be affected — we are restoring onto a staging instance.
```

### 2. Locate the most recent backup

```bash
aws s3 ls s3://$DR_BUCKET/ --recursive | grep 'datapulse_' | tail -1
```

Record:
- Backup filename + timestamp
- Compressed size
- Expected RPO (= now – backup timestamp)

### 3. Pull and decompress

```bash
aws s3 cp s3://$DR_BUCKET/<file> /tmp/
gunzip /tmp/<file>.gz   # if applicable
ls -lh /tmp/<file>       # sanity-check size matches listing
```

### 4. Restore onto the clean staging DB

```bash
export PGPASSWORD=$STAGING_DB_PASSWORD
pg_restore \
  --host=$STAGING_DB_HOST \
  --username=datapulse \
  --dbname=datapulse \
  --no-owner \
  --clean --if-exists \
  --jobs=4 \
  /tmp/<file>
```

**Time checkpoint:** how long did restore take? Note it.

### 5. Run migrations

```bash
cd SAAS
DATABASE_URL=$STAGING_DB_URL alembic upgrade head   # or the migration runner we use
```

### 6. Rebuild dbt marts

```bash
DATABASE_URL=$STAGING_DB_URL make dbt
```

### 7. Verify

- [ ] `GET /health` returns 200.
- [ ] `SELECT count(*) FROM bronze.sales` matches expected magnitude.
- [ ] `SELECT count(*) FROM pos.transactions WHERE status = 'completed'` matches expected magnitude.
- [ ] A sample dashboard loads (log in as a known test tenant, open `/dashboard`).
- [ ] RLS still enforces — attempt a cross-tenant query and confirm it returns 0 rows.

### 8. Stop timer, record outcome

Post in `#datapulse-ops`:

```
DRILL END <UTC time>. Total duration: <min>. RTO target (30 min): PASS/FAIL.
RPO at restore: <h>. RPO target (24 h): PASS/FAIL.
Issues surfaced: <one line per issue>.
```

### 9. Teardown

```bash
# Don't leave a staging DB with prod data lying around.
terraform destroy   # or compose down -v on the local variant
```

## Debrief

Within **24 h** of the drill, driver files one of:

- **Green drill:** one-page summary in `docs/brain/decisions/YYYY-MM-DD-dr-drill.md` noting measured RTO/RPO + any friction points. Link from the next [on-call handoff](oncall.md#handoff).
- **Amber drill (pass but slow):** summary + tracking issues for each friction point. Due dates before the next drill.
- **Red drill (fail):** treat as a P1 — file a [postmortem](postmortem-template.md) even though prod was unaffected, because the *DR capability* was broken. Tech lead decides whether to escalate to an off-cycle drill.

## What we do NOT drill

- Complete AWS region loss — assumed out of scope until we have multi-region. Document gap only.
- Tenant-specific restore (one tenant back without restoring the rest) — separate runbook, needed once a customer loses their own data by accident.
- Application code loss — Git is the source of truth; `git clone + docker compose build` is assumed working.

---

Reviewed alongside [on-call rotation](oncall.md) and [key rotation](key-rotation.md). Last drill: see `docs/brain/decisions/*-dr-drill.md`.
