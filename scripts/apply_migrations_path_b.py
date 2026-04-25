"""
Apply migrations 112 + 113 to the Droplet via Path B:
  SCP -> docker cp into API container -> run prestart.sh

prestart.sh handles:
  - applying migrations in order
  - registering each in public.schema_migrations
  - skipping any that are already registered

Idempotent: safe to re-run.
"""

import sys
from pathlib import Path

import paramiko

SSH_HOST = "164.92.243.3"
SSH_USER = "root"
SSH_KEY = "C:/Users/user/.ssh/id_ed25519_do_new"

API_CONTAINER = "datapulse-api"

MIGRATIONS_TO_APPLY = [
    "migrations/112_pharma_drug_catalog.sql",
    "migrations/113_data_layer_hardening.sql",
]

REPO_ROOT = Path("C:/Users/user/Documents/GitHub/Data-Pulse")


def ssh_connect() -> paramiko.SSHClient:
    """Connect to the production droplet with strict host-key checking.

    Loads ~/.ssh/known_hosts and rejects unknown hosts — pre-trust must
    be established by SSHing manually first.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY, timeout=15)
    return client


def run(ssh, cmd, allow_fail=False):
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    if rc != 0 and not allow_fail:
        print(f"\n[FAIL] Command exited {rc}: {cmd}")
        if out:
            print(f"  stdout: {out}")
        if err:
            print(f"  stderr: {err}")
        sys.exit(1)
    return out, err, rc


def main() -> None:
    print("[1/4] Connecting to Droplet ...")
    ssh = ssh_connect()

    print("[2/4] Pre-check: schema_migrations state BEFORE apply")
    out, _, _ = run(
        ssh,
        "docker exec datapulse-db psql -U datapulse -d datapulse -tAc "
        '"SELECT filename FROM public.schema_migrations '
        "WHERE filename LIKE '11%' ORDER BY filename;\"",
    )
    print("      Currently registered (1xx series):")
    for line in out.strip().splitlines():
        print(f"        {line}")

    print("[3/4] SCP + docker cp migration files ...")
    sftp = ssh.open_sftp()
    for m in MIGRATIONS_TO_APPLY:
        local = REPO_ROOT / m
        remote = f"/tmp/{Path(m).name}"
        sftp.put(str(local), remote)
        print(f"      SCP {Path(m).name} ({local.stat().st_size:,} bytes)")
        run(ssh, f"docker cp {remote} {API_CONTAINER}:/app/migrations/")
        run(ssh, f"rm -f {remote}")
    sftp.close()

    print("[4/4] Running prestart.sh in API container ...")
    print("      ----- prestart.sh output -----")
    out, err, rc = run(
        ssh,
        f"docker exec -e DB_READER_PASSWORD="
        f"\"$(docker exec {API_CONTAINER} sh -c 'echo $DB_READER_PASSWORD')"
        f'" {API_CONTAINER} bash /app/scripts/prestart.sh',
        allow_fail=True,
    )
    # Simpler approach — DB_READER_PASSWORD is already in the container env
    if rc != 0:
        # retry without the var-injection mess (env is already set in container)
        out, err, rc = run(
            ssh,
            f"docker exec {API_CONTAINER} bash /app/scripts/prestart.sh",
        )
    for line in out.strip().splitlines():
        print(f"      {line}")
    if err.strip():
        print(f"      [stderr] {err.strip()}")
    print("      ------------------------------")

    print("\n[verify] schema_migrations state AFTER apply")
    out, _, _ = run(
        ssh,
        "docker exec datapulse-db psql -U datapulse -d datapulse -tAc "
        '"SELECT filename, applied_at FROM public.schema_migrations '
        "WHERE filename LIKE '11%' ORDER BY filename;\"",
    )
    for line in out.strip().splitlines():
        print(f"      {line}")

    print("\n[verify] tables we expected to land")
    out, _, _ = run(
        ssh,
        'docker exec datapulse-db psql -U datapulse -d datapulse -tAc "'
        "SELECT 'pharma.drug_catalog rows:' || COUNT(*)::text FROM pharma.drug_catalog "
        "UNION ALL "
        "SELECT 'pharma.drug_master rows:'  || COUNT(*)::text FROM pharma.drug_master "
        "UNION ALL "
        "SELECT 'drug_master.default_price_egp precision: ' || numeric_precision::text "  # noqa: E501
        "FROM information_schema.columns "
        "WHERE table_schema='pharma' AND table_name='drug_master' "  # noqa: E501
        "  AND column_name='default_price_egp' "
        "UNION ALL "
        "SELECT 'idx_drug_master_name_en_trgm: ' || COUNT(*)::text FROM pg_indexes "  # noqa: E501
        "WHERE schemaname='pharma' AND indexname='idx_drug_master_name_en_trgm' "
        "UNION ALL "
        "SELECT 'webhooks RLS uses fallback: ' || (qual ~ 'app.tenant_id..\\\\s*true')::text "  # noqa: E501
        "FROM pg_policies WHERE tablename='subscriptions' "
        "  AND policyname='tenant_isolation' "
        '"',
    )
    for line in out.strip().splitlines():
        print(f"      {line}")

    ssh.close()
    print("\n[OK] Path B apply complete.")


if __name__ == "__main__":
    main()
