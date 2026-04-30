# Global Problem-Solution Log
# يُقرأ في كل المشاريع — يُحدَّث بعد كل حل لمشكلة

> **القاعدة**: بعد حل أي مشكلة في أي محادثة أو مشروع، أضف الدرس هنا.
> **التنسيق**: `## [DATE] [PROJECT] — [Problem Title]`

---

## 2026-03-23 D--claude — cmdop TimeoutError Missing

**المشكلة**: `cmdop.exceptions.TimeoutError` مش موجود → ImportError
**الحل**: استخدم `ConnectionTimeoutError` من `cmdop.exceptions` أو `TimeoutError` builtin من Python
**Prevention**: قبل استخدام أي exception من library خارجية → افحص الـ exceptions المتاحة أولاً بـ `dir(module.exceptions)`

---

## 2026-03-23 D--claude — Silver Pipeline Token Cost (520-line file)

**المشكلة**: ملف Silver pipeline واحد كبير (520 سطر) → كل edit يعيد إرسال الملف كاملاً في system-reminders
**الحل**: قسّم لـ 3 ملفات: `02a_load.py` + `02b_dims.py` + `02c_fact.py` مع parquet intermediary
**Prevention**: أي script > 200 سطر في pipeline → قسّمه لـ steps منفصلة

---
## 2026-03-23 DigitalOcean — OpenClaw Setup on Fresh Droplet

**المشكلة**: تثبيت OpenClaw على Ubuntu حديث يفشل بسبب PEP 668 + missing tenacity + TimeoutError
**الحل الكامل**:
```bash
apt install python3.12-venv -y
python3 -m venv ~/openclaw-env
source ~/openclaw-env/bin/activate
pip install openclaw==2026.2.25 cmdop==2026.3.18
```
**النسخ المتوافقة**: openclaw==2026.2.25 + cmdop==2026.3.18
**Prevention**: دايماً استخدم venv + النسختين دول مع بعض

---
## 2026-03-24 Windows — Python Environment Map (This Machine)

**البيئة الصحيحة:**
```
Python active:  C:\Users\user\miniforge3\python.exe  (3.13.12)
python3 fix:    C:\Users\user\miniforge3\python3 (shell wrapper → miniforge3)
conda active:   miniforge3 (26.1.1) — conda-forge channel
```

**Conda Environments (miniforge3 only — miniconda3 removed 2026-03-24):**
```
miniforge3 base          → Python 3.13.12  (default, general use)
miniforge3\envs\pharmacy → pharmacy ETL project
miniforge3\envs\workspace → Python 3.12 | pandas, numpy, polars, pyarrow, matplotlib, seaborn, jupyter, openpyxl
```

**تحذيرات:**
- `python3` كان بيروح لـ Windows Store stub — تم إصلاحه بـ shell wrapper في miniforge3/
- PowerShell execution policy مغلوق → استخدم `cmd` دايماً مش PowerShell
- `pip install` في base → يحتاج `--break-system-packages` على Ubuntu فقط (مش Windows)
- miniconda3 محذوف نهائياً — لا تحاول تستخدمه

**Prevention:** دايماً استخدم `miniforge3\python.exe` أو `python` مباشرة — مش `python3.exe`

---
## 2026-03-31 calude-economy — Credential Sanitization in Skill Files

**المشكلة**: Source repo `digitalocean-expert` SKILL.md had hardcoded droplet IP (157.245.114.125) and password (zezo2025)
**الحل**: Replaced with `$DROPLET_IP` and `os.environ["DROPLET_PASSWORD"]` references before copying to new repo
**Prevention**: Always scan skill/agent files for hardcoded credentials before copying to public repos. Use `grep -r 'password\|secret\|token\|api.key' --include='*.md'`

---
## 2026-04-02 SAAS — Docker 29 Breaks Traefik Docker Provider

**المشكلة**: Traefik v3.2-v3.4 يفشل مع Docker 29 — "client version 1.24 is too old. Minimum supported API version is 1.40"
**الحل**: استخدم Nginx reverse proxy بدل Traefik (أبسط بكتير مع Cloudflare). أو انتظر Traefik v3.5+ اللي هيصلح التوافق.
**DOCKER_API_VERSION=1.45 env var مش بيشتغل** — Traefik بيستخدم Docker client library مباشرة مش env var.
**Prevention**: لو Docker 29+ → استخدم Nginx أو Caddy بدل Traefik. أو ثبت Docker 28 بدلاً.

---
## 2026-04-02 SAAS — Cloudflare + Self-Signed Cert (Full Mode)

**المشكلة**: Let's Encrypt TLS-ALPN-01 challenge بيفشل خلف Cloudflare proxy (port 443 intercepted)
**الحل**: Self-signed cert على الـ origin + Cloudflare SSL = "Full" (not strict). مشفر end-to-end بدون Let's Encrypt.
**Prevention**: لو الـ domain على Cloudflare → استخدم self-signed أو Cloudflare Origin Certificate بدل Let's Encrypt.

---
## 2026-04-02 SAAS — Migration 002 Needs db_reader_password GUC

**المشكلة**: `002_add_rls_and_roles.sql` بيفشل بدون `SET app.db_reader_password`
**الحل**: شغل الـ migration manually مع `SET app.db_reader_password = '<pass>';` في نفس الـ session (مش -c + -f لأنهم transactions منفصلة). أو استخدم pipe: `(echo "SET ..."; cat file.sql) | psql`
**Prevention**: أي migration بتحتاج GUC → وثقها في script comment + أضف الـ env var للـ prestart service.

---
## 2026-04-02 SAAS — Nginx 502 Due to Docker DNS Caching

**المشكلة**: Nginx يعمل cache لـ DNS عند الـ startup. لو container اتعمله restart وغيّر IP → Nginx يفضل يبعت للـ IP القديم → 502 "Host is unreachable"
**الحل**: أضف `resolver 127.0.0.11 valid=10s;` + استخدم `set $var` pattern بدل proxy_pass مباشر:
```nginx
resolver 127.0.0.11 valid=10s;
location /api/ {
    set $api http://api:8000;   # variable forces re-resolve
    proxy_pass $api;
}
```
**Prevention**: دايماً في Docker + Nginx → استخدم `set $var` + resolver. مش `proxy_pass http://service` مباشرة.

---
## 2026-04-05 SAAS — Docker Healthcheck Failures (3 issues)

**المشكلة 1**: API container healthcheck uses `curl` but slim Python images don't have curl installed → eternal "unhealthy"
**الحل**: Use Python's built-in urllib: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"`
**Prevention**: Never use `curl` in Python container healthchecks — use `python -c "import urllib.request; ..."` instead

**المشكلة 2**: Frontend healthcheck expects HTTP 200 but Next.js `/` returns 308 redirect → "unhealthy"
**الحل**: Check `r.statusCode < 400` instead of `r.statusCode === 200` — redirects (3xx) mean the server is alive
**Prevention**: Any healthcheck on a web app should accept 2xx AND 3xx as healthy

**المشكلة 3**: Nginx Alpine healthcheck uses `localhost` but Alpine resolves it to `::1` (IPv6) while nginx binds `0.0.0.0` (IPv4) → connection refused
**الحل**: Use `127.0.0.1` explicitly instead of `localhost` in healthchecks
**Prevention**: In ALL Alpine-based containers, use `127.0.0.1` not `localhost` for healthchecks

---
## 2026-04-05 SAAS — Cloudflare Flexible SSL + Nginx HTTPS Redirect Loop

**المشكلة**: Nginx had separate HTTP (port 80) block with `return 301 https://...`. Cloudflare in Flexible mode connects to port 80 → gets 301 → infinite redirect loop
**الحل**: Combine into single server block listening on both 80 and 443 (no redirect). Cloudflare handles HTTPS on the edge.
**Prevention**: When behind Cloudflare → single server block (80+443), NO http-to-https redirect. Cloudflare handles that edge-side.

---
## 2026-04-09 DataPulse — Staging Deploy Pipeline: 7 Cascading Failures

**المشكلة**: Deploy Staging فشل 6 مرات متتالية — كل مرة بسبب مختلف. السبب الأساسي: refactoring كبير (PRs #228, #231, #234) غيّر الـ workflow + Dockerfile + dependencies + security checks بدون اختبار الـ deploy pipeline end-to-end.

### الأعطال السبعة بالترتيب:

| # | Error | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | `POSTGRES_PASSWORD missing` | SSH script exports 3 of 6 required secrets | Added to env/envs/export in workflow |
| 2 | `REDIS_PASSWORD missing` | Secrets set in `staging` env but workflow uses `environment: deploy` | Set secrets in correct `deploy` environment |
| 3 | `DB_READER_PASSWORD must be set` | H2.12 hardening added :? guard but value never set on server | Generated password, set in .env + GitHub secrets |
| 4 | `ModuleNotFoundError: datapulse` | PR #228 replaced `pip install .` with `pip install -r requirements.lock` | Added `pip install --no-deps .` back to Dockerfile |
| 5 | `ModuleNotFoundError: prometheus_fastapi_instrumentator` | requirements.lock not regenerated after adding dep to pyproject.toml | Ran pip-compile to regenerate lock file |
| 6 | `requirements.lock overwritten` | PR #234 merged AFTER #235 with stale lock file | Regenerated lock file again from latest main |
| 7 | Health checks return 301 + `DATABASE_URL missing sslmode` | Nginx H4.6 redirects HTTP→HTTPS; core/db.py requires sslmode in prod | curl -kL https:// + ?sslmode=disable |

**Bonus**: 1.1M duplicate rows in bronze.sales blocked migration 030 (unique index). Fixed with DELETE USING ctid dedup.

### الدروس:

1. **GitHub Environment Scoping**: `${{ secrets.X }}` resolves from the `environment:` specified in the job — NOT from all environments. Always verify which environment name the workflow uses (`deploy` vs `staging` vs `production`).

2. **requirements.lock drift**: When two PRs both touch dependencies, the second merge can overwrite the first's lock file. Always regenerate lock file from the FINAL main state, not from the branch.

3. **Dockerfile pip install pattern**: `pip install --require-hashes -r requirements.lock` installs ONLY external deps. The project package itself needs `pip install --no-deps .` separately. Never remove `pip install .` when switching to lock files.

4. **Deploy health checks behind reverse proxy**: If nginx does HTTP→HTTPS redirect (301), health checks using `http://localhost` will always fail. Use `curl -skL https://localhost` (skip self-signed cert + follow redirects).

5. **DATABASE_URL sslmode in Docker**: New code that validates `sslmode=` in non-dev environments will break container-to-container connections. Add `?sslmode=disable` to DATABASE_URL in docker-compose.yml.

6. **Never deploy without E2E pipeline test**: A single `docker compose up` test on the staging server would have caught ALL 7 issues before merging. Add a "staging dry-run" CI job that builds + starts + health-checks in a runner.

7. **Secret cascade check**: Before any deploy workflow change, run: `grep -n '${.*:?' docker-compose*.yml` to list ALL required variables, then cross-check against the workflow's env/envs/export.

**Prevention Checklist (before merging deploy changes):**
- [ ] `grep '${.*:?' docker-compose*.yml` → all vars in workflow env/envs/export?
- [ ] `pip-compile` → requirements.lock matches pyproject.toml?
- [ ] Dockerfile has `pip install --no-deps .` after lock install?
- [ ] Health check URLs match nginx config (HTTP vs HTTPS)?
- [ ] DATABASE_URL includes `?sslmode=` if code validates it?
- [ ] GitHub secrets set in the CORRECT environment (check `environment:` in workflow)?
- [ ] Server .env has all required vars (DB_READER_PASSWORD, etc.)?

---
## 2026-04-11 DataPulse — CI Whack-a-Mole: 8 PRs to Fix 1 Deploy

**المشكلة**: PR واحد (#296) اتدمج بدون CI green → 8 PRs متتالية (#298-#310) عشان نوصل CI green. كل merge كشف failure جديد لأن CI بيوقف عند أول failure.

### Root Causes (3 categories):

**1. Narrow Exception Handlers (28 occurrence)**
`except (SQLAlchemyError, OSError)` في routes/services — الـ tests بتعمل mock بـ `Exception`/`RuntimeError` اللي بتهرب من الـ handler.
**الحل**: `except Exception` في كل handler على API boundary. عملنا nuclear sweep لكل الـ 28 handler في 17 file.
**Prevention**: أي `except` في route handler لازم يكون `except Exception` — مش narrow types.

**2. Missing Test Mocks**
- `BillingService.check_plan_limits()` مش mocked في scheduler test → `MagicMock >= int` crash
- `httpx` module بالكامل mocked → `except (httpx.HTTPError)` بيعمل TypeError (catching MagicMock)
- Settings validator بيرفض `api_key=""` في production → test مش بيقدر يعمل Settings object
- `inspect.getsource(create_app)` بيرجع source الـ cached wrapper مش الـ original function
- `verify_jwt` بيعمل real HTTP requests في CI → timeout بعد 120s
**Prevention**: كل test لازم يعمل mock لكل external dependency. `MagicMock()` مش بديل لـ real object في type comparisons.

**3. CI Config Issues**
- `--cov-fail-under=95` على integration tests لوحدها (بتغطي 48% بس) → دايماً بتفشل
- PRs merged to wrong base branch (`claude/inspiring-swirles` بدل `main`)
**Prevention**: Integration test coverage threshold لازم يكون أقل من unit test threshold.

### القاعدة الذهبية:
> **NEVER merge a PR until CI is green on the PR branch.**
> CI بيوقف عند أول failure — لو merge وانت failing، كل failure بعده بتحتاج PR جديد.

### Prevention Checklist:
- [ ] `grep -rn "except (" src/ | grep -v "except Exception"` → 0 narrow handlers في routes
- [ ] `grep -rn "side_effect = Exception\|side_effect = RuntimeError" tests/` → كل واحد matched بـ handler
- [ ] CI green on PR branch BEFORE merge
- [ ] Integration `--cov-fail-under` < actual integration coverage (~48%)

---
## 2026-04-11 DataPulse — Always Verify Before Push

**المشكلة**: كل push للـ CI كان بيفشل بسبب مشاكل كان ممكن نكتشفها locally: mock assertions مش متحدثة، ruff format مش متنفذ، migration بتشاور على column مش موجود.

**الحل**: قبل أي `git push`، شغل الـ 3 checks دول:
```bash
ruff format --check src/ tests/    # formatting
ruff check src/ tests/              # lint
pytest -m unit -x -q --timeout=30   # unit tests (fast, stops at first failure)
```

**Why**: كل CI failure = 5 دقايق انتظار + round-trip لـ fix + force-push. الـ 3 commands دول بياخدوا 30 ثانية locally وبيوفروا 80% من الـ CI round-trips.

**Prevention**: 
- بعد تغيير function signature → `grep -rn "assert_called.*function_name" tests/` عشان تلاقي كل الـ mock assertions
- بعد إضافة migration → verify كل table references بـ `grep "column_name" migrations/CREATE_TABLE_file.sql`
- بعد أي edit → `ruff format` مش بس `ruff check`

---
<!-- أضف دروس جديدة فوق هذا السطر -->
