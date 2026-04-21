"""Tests for scripts/check_migration_numbers.py (CI guard for issue #538)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_migration_numbers.py"


def _write_migrations(tmp_path: Path, names: list[str]) -> Path:
    """Create a fake migrations/ dir with empty files of the given names."""
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for name in names:
        (migrations / name).write_text("-- test\nSELECT 1;\n")
    # The script derives MIGRATIONS_DIR relative to its own location. To point
    # it at our fake dir, we copy the script into a scripts/ subdir of tmp_path
    # so that __file__.resolve().parent.parent / "migrations" resolves correctly.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "check_migration_numbers.py").write_text(SCRIPT.read_text())
    return scripts_dir / "check_migration_numbers.py"


def _run(script_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )


class TestPassingCases:
    def test_empty_migrations_directory_passes(self, tmp_path):
        script = _write_migrations(tmp_path, [])
        result = _run(script)
        assert result.returncode == 0

    def test_unique_numeric_prefixes_pass(self, tmp_path):
        script = _write_migrations(tmp_path, ["001_init.sql", "002_roles.sql", "003_indexes.sql"])
        result = _run(script)
        assert result.returncode == 0, result.stderr

    def test_letter_suffixed_subslots_are_not_duplicates(self, tmp_path):
        """030 and 030a are distinct slots, not a duplicate of each other."""
        script = _write_migrations(
            tmp_path,
            [
                "030_base.sql",
                "030a_followup.sql",
                "030b_another.sql",
                "031_next.sql",
            ],
        )
        result = _run(script)
        assert result.returncode == 0, result.stderr

    def test_gaps_in_sequence_are_allowed(self, tmp_path):
        """Gaps like 005 -> 007 are permitted (see 006_placeholder.sql)."""
        script = _write_migrations(tmp_path, ["001_init.sql", "002_next.sql", "100_much_later.sql"])
        result = _run(script)
        assert result.returncode == 0

    def test_placeholder_file_passes(self, tmp_path):
        """006_placeholder.sql in the real repo must not be flagged."""
        script = _write_migrations(
            tmp_path, ["005_prior.sql", "006_placeholder.sql", "007_after.sql"]
        )
        result = _run(script)
        assert result.returncode == 0


class TestFailingCases:
    def test_duplicate_numeric_prefix_is_detected(self, tmp_path):
        """The exact #538 bug: two files sharing prefix 031."""
        script = _write_migrations(
            tmp_path,
            [
                "031_gamification.sql",
                "031_pipeline.sql",
            ],
        )
        result = _run(script)
        assert result.returncode == 1
        assert "Duplicate migration prefix '031'" in result.stderr
        assert "031_gamification.sql" in result.stderr
        assert "031_pipeline.sql" in result.stderr

    def test_duplicate_letter_subslot_is_detected(self, tmp_path):
        """030a_foo and 030a_bar both claim sub-slot 030a — also a duplicate."""
        script = _write_migrations(tmp_path, ["030_base.sql", "030a_foo.sql", "030a_bar.sql"])
        result = _run(script)
        assert result.returncode == 1
        assert "Duplicate migration prefix '030a'" in result.stderr

    def test_malformed_filename_is_detected(self, tmp_path):
        """Uppercase letters break the convention."""
        script = _write_migrations(tmp_path, ["031_GoodName.sql"])
        result = _run(script)
        assert result.returncode == 1
        assert "Malformed" in result.stderr

    def test_non_sql_files_are_ignored(self, tmp_path):
        """README and shell scripts in migrations/ must not trigger the check."""
        script = _write_migrations(
            tmp_path,
            ["001_init.sql", "README.md", "apply.sh"],
        )
        # README.md and apply.sh aren't .sql files, so they're skipped entirely.
        result = _run(script)
        assert result.returncode == 0


class TestKnownDuplicatesAllowlist:
    """The allowlist grandfathers historic dupes but still flags new ones."""

    def _make_tree(self, tmp_path: Path, files: list[str], known: list[str]) -> Path:
        """Build a tmp migrations dir with files + an allowlist file."""
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        for name in files:
            (migrations / name).write_text("-- test\nSELECT 1;\n")
        (migrations / ".known-duplicate-prefixes").write_text(
            "\n".join(["# test allowlist", *known]) + "\n"
        )
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "check_migration_numbers.py").write_text(SCRIPT.read_text())
        return scripts_dir / "check_migration_numbers.py"

    def test_known_duplicate_passes_with_warning(self, tmp_path):
        """A dup prefix listed in .known-duplicate-prefixes is grandfathered."""
        script = self._make_tree(
            tmp_path,
            files=["031_a.sql", "031_b.sql", "032_next.sql"],
            known=["031"],
        )
        result = _run(script)
        assert result.returncode == 0, result.stderr
        assert "WARNING" in result.stdout
        assert "031" in result.stdout

    def test_new_duplicate_still_fails_even_with_allowlist(self, tmp_path):
        """A NEW duplicate (not in the allowlist) must still fail."""
        script = self._make_tree(
            tmp_path,
            files=["031_a.sql", "031_b.sql", "050_a.sql", "050_b.sql"],
            known=["031"],  # 050 is NOT grandfathered
        )
        result = _run(script)
        assert result.returncode == 1
        assert "Duplicate migration prefix '050'" in result.stderr
        # The grandfathered 031 still appears as a warning, not a failure:
        assert "031" in result.stdout

    def test_allowlist_missing_file_is_equivalent_to_empty(self, tmp_path):
        """No allowlist file => no grandfathering => dupes fail as before."""
        migrations = tmp_path / "migrations"
        migrations.mkdir()
        (migrations / "031_a.sql").write_text("")
        (migrations / "031_b.sql").write_text("")
        # Deliberately no .known-duplicate-prefixes file
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "check_migration_numbers.py").write_text(SCRIPT.read_text())
        result = _run(scripts_dir / "check_migration_numbers.py")
        assert result.returncode == 1
        assert "Duplicate migration prefix '031'" in result.stderr


@pytest.mark.unit
def test_real_repo_state_has_exactly_three_grandfathered_dupes():
    """Documents the current state on main: the 3 known duplicates
    (031, 088, 089) are grandfathered via migrations/.known-duplicate-prefixes,
    so the script exits 0 but emits a warning. When the rename follow-up PR
    lands, both the dupes AND the allowlist entries go away, and this test
    still passes (exit 0, zero warnings).
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    # Must succeed either way — grandfathered debt doesn't fail CI.
    assert result.returncode == 0, (
        f"Expected exit 0 on main. If a NEW duplicate landed, reconcile it; "
        f"if the known-duplicates file was deleted, restore it. stderr:\n{result.stderr}"
    )
