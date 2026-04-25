"""
Upload drug catalog from Excel to Droplet PostgreSQL.

Strategy:
  1. Convert Excel -> CSV locally (drop stock columns, clean)
  2. SCP CSV to Droplet /tmp/
  3. docker cp into datapulse-db container
  4. CREATE TABLE + COPY via docker exec psql

Source:  C:/Users/user/Downloads/index.xlsx
Target:  pharma.drug_catalog  (datapulse-db container on Droplet 164.92.243.3)

Dropped columns: Total Stock, Branches Stock, WH Stock  (operational — not catalog data)
"""

import csv
import tempfile
from pathlib import Path

import pandas as pd
import paramiko

# ─── Config ──────────────────────────────────────────────────────────────────
EXCEL_PATH = Path("C:/Users/user/Downloads/index.xlsx")
REMOTE_CSV = "/tmp/drug_catalog.csv"
CONTAINER = "datapulse-db"
DB_USER = "datapulse"
DB_NAME = "datapulse"

SSH_HOST = "164.92.243.3"
SSH_USER = "root"
SSH_KEY = "C:/Users/user/.ssh/id_ed25519_do_new"

DROP_COLS = {"Total Stock", "Branches Stock", "WH Stock"}

CREATE_TABLE_SQL = """
CREATE SCHEMA IF NOT EXISTS pharma;

CREATE TABLE IF NOT EXISTS pharma.drug_catalog (
    material_code     TEXT        PRIMARY KEY,
    name_en           TEXT,
    price_egp         NUMERIC(10,2),
    active_ingredient TEXT,
    vendor_name       TEXT,
    division          TEXT,
    category          TEXT,
    subcategory       TEXT,
    segment           TEXT,
    container_form    TEXT,
    imported_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_drug_catalog_name_en
    ON pharma.drug_catalog (name_en);

CREATE INDEX IF NOT EXISTS idx_drug_catalog_ingredient
    ON pharma.drug_catalog (active_ingredient)
    WHERE active_ingredient IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_drug_catalog_category
    ON pharma.drug_catalog (category, subcategory);

COMMENT ON TABLE pharma.drug_catalog IS
    'SAP material master — pharma drug catalog. Keyed on SAP material_code. '
    'Links to pharma.drug_master via drug_alias once barcodes are mapped. '
    'No RLS: shared catalog readable by all tenants.';
"""


# ─── Step 1: Excel -> CSV ─────────────────────────────────────────────────────


def excel_to_csv() -> Path:
    print(f"[1/4] Reading {EXCEL_PATH} ...")
    df = pd.read_excel(EXCEL_PATH, dtype=str)
    df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)
    df.dropna(subset=["Material", "Material Desc."], inplace=True)

    # Deduplicate on material_code (keep last — last row wins for price/name updates)
    before = len(df)
    df.drop_duplicates(subset=["Material"], keep="last", inplace=True)
    dupes = before - len(df)
    if dupes:
        print(f"      Dropped {dupes:,} duplicate material codes")

    col_map = {
        "Material": "material_code",
        "Material Desc.": "name_en",
        "Price": "price_egp",
        "Active Ingredients.": "active_ingredient",
        "Ext.Vendor Name": "vendor_name",
        "Division": "division",
        "Category": "category",
        "SubCategory": "subcategory",
        "Segment": "segment",
        "ContainerReqmts": "container_form",
    }
    df = df.rename(columns=col_map)
    df = df[[v for v in col_map.values() if v in df.columns]]

    # Normalize: strip whitespace, replace empty strings with empty (psql COPY handles \N as NULL)
    for col in df.columns:
        df[col] = df[col].str.strip().replace({"nan": None, "": None})

    # NamedTemporaryFile(delete=False) avoids the mktemp race (CWE-377);
    # we close the handle immediately and let pandas reopen by path.
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
        out = Path(tf.name)
    df.to_csv(out, index=False, quoting=csv.QUOTE_NONNUMERIC, na_rep="")
    print(f"      {len(df):,} rows -> {out}")
    return out


# ─── Step 2-4: SCP + docker cp + COPY ────────────────────────────────────────


def ssh_connect() -> paramiko.SSHClient:
    """Connect to the production droplet with strict host-key checking.

    Loads the operator's ~/.ssh/known_hosts and rejects unknown hosts —
    pre-trust must be established by SSHing manually first (one-shot
    ``ssh-keyscan -H <host> >> ~/.ssh/known_hosts``). This protects
    against MITM where an attacker spoofs the droplet's IP.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(SSH_HOST, username=SSH_USER, key_filename=SSH_KEY, timeout=15)
    return client


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    _, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode().strip()
    if err:
        print(f"      [stderr] {err}")
    return out.strip()


def upload(csv_path: Path) -> None:
    print("[2/4] Connecting to Droplet via SSH ...")
    ssh = ssh_connect()

    print("[3/4] SCP files -> Droplet /tmp/ ...")
    sftp = ssh.open_sftp()

    # Upload CSV
    sftp.put(str(csv_path), REMOTE_CSV)
    print(f"      CSV: {csv_path.stat().st_size / 1024 / 1024:.1f} MB")

    # Upload SQL script (avoids shell escaping hell with multi-line SQL)
    copy_cmd = (
        "\\COPY pharma.drug_catalog("
        "material_code,name_en,price_egp,active_ingredient,vendor_name,"
        "division,category,subcategory,segment,container_form) "
        "FROM '/tmp/drug_catalog.csv' CSV HEADER;\n"
    )
    sql_content = CREATE_TABLE_SQL + "\nTRUNCATE pharma.drug_catalog;\n\n" + copy_cmd
    remote_sql = "/tmp/drug_catalog_setup.sql"
    with sftp.open(remote_sql, "w") as f:
        f.write(sql_content)
    print("      SQL script uploaded")
    sftp.close()

    print(f"[4/4] Importing into {CONTAINER} -> pharma.drug_catalog ...")

    # Copy both files into container
    run(ssh, f"docker cp {REMOTE_CSV} {CONTAINER}:{REMOTE_CSV}")
    run(ssh, f"docker cp {remote_sql} {CONTAINER}:{remote_sql}")

    # Run SQL script (CREATE TABLE + COPY in one shot)
    out = run(ssh, f"docker exec {CONTAINER} psql -U {DB_USER} -d {DB_NAME} -f {remote_sql}")
    if out:
        print(f"      {out}")

    # Count result
    count_sql = "SELECT COUNT(*) FROM pharma.drug_catalog;"
    count = run(
        ssh,
        f"docker exec {CONTAINER} psql -U {DB_USER} -d {DB_NAME} -tAc '{count_sql}'",
    )

    # Cleanup host and container temp files
    run(ssh, f"rm -f {REMOTE_CSV} {remote_sql}")
    run(ssh, f"docker exec {CONTAINER} rm -f {REMOTE_CSV} {remote_sql}")
    ssh.close()

    print("\n[OK] Upload complete.")
    print("     Table: pharma.drug_catalog")
    print(f"     Rows in DB: {count}")
    print(f"     Host: {SSH_HOST}")


def main() -> None:
    csv_path = excel_to_csv()
    upload(csv_path)
    csv_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
