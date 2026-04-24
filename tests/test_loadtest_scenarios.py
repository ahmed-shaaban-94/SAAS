"""Sanity checks for the k6 load-test harness (#607).

CI doesn't run k6 itself (needs staging creds), but we can catch two
common rot patterns without a k6 binary:

1. Each scenario file imports the shared helpers from ../lib/common.js.
2. Each scenario declares thresholds so a regression run actually fails.
3. README + Makefile references stay in sync with files on disk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LOADTEST_DIR = REPO_ROOT / "scripts" / "loadtest"
SCENARIOS = list((LOADTEST_DIR / "scenarios").glob("*.js"))


@pytest.mark.unit
class TestLoadtestLayout:
    def test_loadtest_dir_exists(self):
        assert LOADTEST_DIR.is_dir()

    def test_readme_exists(self):
        assert (LOADTEST_DIR / "README.md").is_file()

    def test_env_example_exists(self):
        assert (LOADTEST_DIR / "env.example").is_file()

    def test_common_lib_exists(self):
        assert (LOADTEST_DIR / "lib" / "common.js").is_file()

    def test_scenarios_directory_non_empty(self):
        assert len(SCENARIOS) >= 3, f"expected ≥3 scenarios, found {len(SCENARIOS)}"


@pytest.mark.unit
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda p: p.name)
class TestScenarioFile:
    def test_imports_common_helpers(self, scenario: Path):
        text = scenario.read_text()
        assert "../lib/common.js" in text, (
            f"{scenario.name} should import from ../lib/common.js so all "
            f"scenarios share auth/base-url handling"
        )

    def test_declares_thresholds(self, scenario: Path):
        text = scenario.read_text()
        assert "thresholds" in text, (
            f"{scenario.name} must declare thresholds — a run without "
            f"thresholds cannot fail CI on regression"
        )

    def test_exports_default_function(self, scenario: Path):
        text = scenario.read_text()
        # k6 requires a default export to know what a VU does.
        assert re.search(r"export\s+default\s+function", text), (
            f"{scenario.name} must `export default function` (k6 VU body)"
        )

    def test_exports_options(self, scenario: Path):
        text = scenario.read_text()
        assert re.search(r"export\s+const\s+options", text), (
            f"{scenario.name} must declare `export const options`"
        )


@pytest.mark.unit
class TestMakefileWiring:
    def _makefile_text(self) -> str:
        return (REPO_ROOT / "Makefile").read_text()

    @pytest.mark.parametrize(
        "target",
        [
            "loadtest-dashboard",
            "loadtest-checkout",
            "loadtest-analytics-mixed",
            "loadtest-all",
        ],
    )
    def test_target_declared_in_phony(self, target: str):
        # Every loadtest-* target MUST appear in .PHONY so `make` doesn't
        # mistake a same-named file for the target.
        text = self._makefile_text()
        phony_line = next((ln for ln in text.splitlines() if ln.startswith(".PHONY:")), "")
        assert target in phony_line, f"{target} must be in the .PHONY list"

    @pytest.mark.parametrize(
        "target,scenario",
        [
            ("loadtest-dashboard", "dashboard.js"),
            ("loadtest-checkout", "pos_checkout.js"),
            ("loadtest-analytics-mixed", "analytics_mixed.js"),
        ],
    )
    def test_target_points_to_existing_scenario(self, target: str, scenario: str):
        # Target recipe must reference the scenario file that lives on disk.
        text = self._makefile_text()
        assert scenario in text, f"Makefile target {target} should reference {scenario}"
        assert (LOADTEST_DIR / "scenarios" / scenario).is_file(), (
            f"scenario {scenario} referenced in Makefile but missing on disk"
        )
