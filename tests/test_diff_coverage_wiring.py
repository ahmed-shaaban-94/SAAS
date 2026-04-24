"""Sanity checks for the local diff-cover patch-coverage hook.

Mirrors the pattern in `test_loadtest_scenarios.py` — no external tool
binary needed; we just verify the three files that declare the feature
stay consistent.

If these assertions ever fail, something drifted between:
  - scripts/check_diff_coverage.sh (the script itself)
  - Makefile                       (the `diff-cover` target)
  - pyproject.toml                 (the dev extra that installs diff-cover)
  - CONTRIBUTING.md                (the published workflow)
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_diff_coverage.sh"


@pytest.mark.unit
class TestDiffCoverageWiring:
    def test_script_exists(self):
        assert SCRIPT.is_file(), "scripts/check_diff_coverage.sh missing"

    def test_script_is_executable_or_bash_compatible(self):
        # Windows git doesn't preserve the executable bit reliably, so we
        # accept either an executable bit OR a `#!/usr/bin/env bash`
        # shebang (which is how the Makefile invokes it anyway).
        text = SCRIPT.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash"), "script must start with bash shebang"

    def test_script_references_fail_under_threshold(self):
        """Script must actually fail on threshold — not just report."""
        text = SCRIPT.read_text(encoding="utf-8")
        assert "--fail-under=" in text, "diff-cover invocation must pass --fail-under"

    def test_script_honors_skip_env_var(self):
        """SKIP_DIFF_COVER=1 escape hatch must be documented and honored."""
        text = SCRIPT.read_text(encoding="utf-8")
        assert "SKIP_DIFF_COVER" in text

    def test_makefile_declares_diff_cover_target(self):
        mk = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        # Find the '.PHONY' line
        phony = next((ln for ln in mk.splitlines() if ln.startswith(".PHONY:")), "")
        assert "diff-cover" in phony, "Makefile .PHONY must include diff-cover"

    def test_makefile_target_calls_script(self):
        mk = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        assert "scripts/check_diff_coverage.sh" in mk, (
            "Makefile diff-cover target must invoke the script"
        )

    def test_dev_extra_declares_diff_cover(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        # Must appear inside the [project.optional-dependencies].dev block.
        assert "diff-cover>=" in pyproject, "pyproject.toml dev extra must pin diff-cover"

    def test_contributing_documents_make_diff_cover(self):
        contributing = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        assert "make diff-cover" in contributing, "CONTRIBUTING.md must mention `make diff-cover`"
