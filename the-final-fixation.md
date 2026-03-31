# The Final Fixation — Pre-existing CI Issues to Resolve

> These issues exist in the codebase prior to the Fork Strategy PR and must be
> resolved before the official project delivery.

---

## 1. Python Lint (ruff) — 12 errors

### B008 — FastAPI `Depends()` in argument defaults (6 errors)
```
src/datapulse/api/auth.py:31  — Depends(get_settings)
src/datapulse/api/auth.py:45  — Depends(get_settings)
src/datapulse/api/auth.py:58  — Security(_bearer_scheme)
src/datapulse/api/auth.py:60  — Depends(get_settings)
src/datapulse/api/auth.py:122 — Security(_bearer_scheme)
src/datapulse/api/auth.py:124 — Depends(get_settings)
```
**Fix**: Extract to module-level variables or add `# noqa: B008` (standard FastAPI pattern).

### N806 — Uppercase variable in function (3 errors)
```
src/datapulse/api/routes/pipeline.py:120 — TERMINAL
src/datapulse/api/routes/pipeline.py:121 — POLL_INTERVAL
src/datapulse/api/routes/pipeline.py:122 — MAX_DURATION
```
**Fix**: Rename to lowercase (`terminal`, `poll_interval`, `max_duration`) or move to module level.

### E501 — Line too long >100 chars (2 errors)
```
src/datapulse/api/routes/pipeline.py:75  (101 chars)
tests/test_detail_trends.py:1            (108 chars)
```
**Fix**: Break long lines / reword docstring.

### E402 — Import not at top of file (1 error)
```
src/datapulse/ai_light/service.py:33 — import re as _re
```
**Fix**: Move `import re as _re` to the top of the file with other imports.

---

## 2. Frontend ESLint — 2 errors

```
frontend/src/lib/auth.ts:65 — @typescript-eslint/no-explicit-any rule not found
frontend/src/lib/auth.ts:86 — @typescript-eslint/no-explicit-any rule not found
```
**Fix**: Either:
- `npm install -D @typescript-eslint/eslint-plugin` and configure in `.eslintrc`, OR
- Remove the two `eslint-disable-next-line` comments from `auth.ts`

---

## 3. Python Tests — Environment Crash

```
Error: pyo3_runtime.PanicException
Chain: conftest.py → api.auth → api.jwt → PyJWT → cryptography → cffi MISSING
Root: ModuleNotFoundError: No module named '_cffi_backend'
```
**Fix**: Either:
- Add `cffi` to `pyproject.toml` dependencies, OR
- Pin compatible versions: `cryptography>=42,<44` + `PyJWT[crypto]>=2.8,<3`, OR
- Ensure CI installs system `libffi-dev` before pip install

---

## 4. Test Coverage — 25% (target 80%)

New modules with **0% coverage** that need tests:

| Module | File(s) | Priority |
|--------|---------|----------|
| `cache_decorator` | `src/datapulse/cache_decorator.py` | HIGH |
| `explore` | `src/datapulse/explore/models.py, manifest_parser.py, sql_builder.py` | HIGH |
| `embed` | `src/datapulse/embed/token.py` | MEDIUM |
| `sql_lab` | `src/datapulse/sql_lab/validator.py` | HIGH |
| `reports` | `src/datapulse/reports/models.py, template_engine.py` | MEDIUM |
| `tasks` | `src/datapulse/tasks/celery_app.py, query_tasks.py, models.py` | LOW |
| `api routes` | `src/datapulse/api/routes/explore.py, embed.py, sql_lab.py, reports.py, queries.py` | HIGH |

**Minimum tests needed**: ~50-60 tests across these modules to reach 80%.

---

## 5. CodeQL — Potential SQL Injection Flags (3 files)

```
src/datapulse/explore/sql_builder.py      — f-string in FROM clause (line ~244)
src/datapulse/pipeline/quality.py         — f-string SQL with schema/table (line ~245)
src/datapulse/pipeline/repository.py      — f-string SQL with where clause (line ~165)
```
**Fix**: Replace f-string SQL construction with parameterized queries or validate
inputs against a strict whitelist before interpolation.

---

## Execution Order (Recommended)

1. **Environment fix** (cffi/cryptography) — unblocks all tests
2. **Ruff lint fixes** (12 errors across 4 files) — 10 min
3. **Frontend ESLint** (1 file) — 2 min
4. **CodeQL SQL injection** (3 files) — 30 min
5. **Write tests** (6 modules) — biggest effort, ~50-60 tests needed
