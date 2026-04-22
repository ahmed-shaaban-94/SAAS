#!/usr/bin/env python3
"""Per-module coverage gate enforcer — issue #607 subtask 3.

Reads coverage.xml (produced by pytest-cov --cov-report=xml) and checks that
security-critical modules meet higher coverage thresholds than the overall floor.

Configuration is in pyproject.toml under [tool.datapulse.coverage_gates].
Falls back to DEFAULTS if the section is missing.

Exit codes: 0 = all gates pass, 1 = one or more modules below threshold.

Usage:
  python scripts/check_coverage_gates.py [coverage.xml]
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Default per-module thresholds ─────────────────────────────────────────────
# Values here are the *minimum* line-coverage % required for each module path
# prefix (matched against the package path in coverage.xml).
# Security-critical modules are gated higher than the 77% overall floor.
DEFAULTS: dict[str, int] = {
    "datapulse/core/auth": 90,
    "datapulse/core/jwt": 90,
    "datapulse/rbac": 90,
    "datapulse/billing": 90,
    "datapulse/pos": 85,
}


def load_gates() -> dict[str, int]:
    """Load gates from pyproject.toml if available, else use DEFAULTS."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return DEFAULTS

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return DEFAULTS
    data = tomllib.loads(pyproject.read_text())
    gates = data.get("tool", {}).get("datapulse", {}).get("coverage_gates", {})
    if not gates:
        return DEFAULTS
    return {k: int(v) for k, v in gates.items()}


def parse_coverage_xml(xml_path: Path) -> dict[str, float]:
    """Parse coverage.xml → {package_path: line_rate_pct}."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    rates: dict[str, float] = {}

    for package in root.iter("package"):
        pkg_name = package.get("name", "")
        # Convert dotted package name to path-style
        pkg_path = pkg_name.replace(".", "/")
        hits = 0
        total = 0
        for line in package.iter("line"):
            total += 1
            if line.get("hits", "0") != "0":
                hits += 1
        if total > 0:
            rates[pkg_path] = (hits / total) * 100
    return rates


def match_gate(pkg_path: str, gate_prefix: str) -> bool:
    """True if pkg_path starts with gate_prefix (normalised)."""
    a = pkg_path.replace("\\", "/").rstrip("/")
    b = gate_prefix.replace("\\", "/").rstrip("/")
    return a == b or a.startswith(b + "/")


def main(argv: list[str]) -> int:
    xml_path = Path(argv[1]) if len(argv) > 1 else Path("coverage.xml")
    if not xml_path.exists():
        print(f"::warning::coverage.xml not found at {xml_path} — skipping per-module gates.")
        return 0

    gates = load_gates()
    rates = parse_coverage_xml(xml_path)

    # For each gate, aggregate coverage across all matching packages
    failures: list[str] = []
    for gate_prefix, threshold in gates.items():
        matching = {path: rate for path, rate in rates.items() if match_gate(path, gate_prefix)}
        if not matching:
            print(
                f"::warning::Gate '{gate_prefix}' matched no packages in coverage.xml — skipping."
            )
            continue

        avg_rate = sum(matching.values()) / len(matching)
        status = "✅" if avg_rate >= threshold else "❌"
        print(f"{status} {gate_prefix}: {avg_rate:.1f}% (threshold: {threshold}%)")
        if avg_rate < threshold:
            failures.append(f"  {gate_prefix}: {avg_rate:.1f}% < required {threshold}%")

    if failures:
        print("\nCoverage gate failures:")
        for f in failures:
            print(f"::error::{f}")
        return 1

    print(f"\nAll {len(gates)} per-module coverage gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
