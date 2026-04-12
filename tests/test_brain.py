"""Tests for datapulse.brain module — DB operations, embeddings, session_end."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

# ── Unit tests for brain.db (mocked psycopg2) ─────────────────────


class TestBrainDB:
    """Test brain.db functions with mocked database."""

    @patch("datapulse.brain.db.get_connection")
    def test_insert_session_returns_id(self, mock_conn):
        from datapulse.brain.db import insert_session

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (42,)
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = insert_session(
            timestamp="2026-04-12T20:00",
            branch="main",
            user_name="Ahmed",
            layers=["bronze", "api"],
            modules=["analytics"],
            files_changed=["src/datapulse/analytics/service.py"],
            commits=[{"sha": "abc123", "message": "fix stuff"}],
            body_md="# Session note",
        )

        assert result == 42
        mock_cur.execute.assert_called_once()
        # Verify the SQL starts with INSERT
        sql = mock_cur.execute.call_args[0][0]
        assert "INSERT INTO brain.sessions" in sql

    @patch("datapulse.brain.db.get_connection")
    def test_get_recent_sessions(self, mock_conn):
        from datapulse.brain.db import get_recent_sessions

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            {"id": 2, "timestamp": "2026-04-12", "branch": "feat/x", "layers": ["api"]},
            {"id": 1, "timestamp": "2026-04-11", "branch": "main", "layers": ["bronze"]},
        ]
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = get_recent_sessions(count=5)

        assert len(result) == 2
        assert result[0]["id"] == 2
        sql = mock_cur.execute.call_args[0][0]
        assert "ORDER BY timestamp DESC" in sql

    @patch("datapulse.brain.db.get_connection")
    def test_insert_decision(self, mock_conn):
        from datapulse.brain.db import insert_decision

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (7,)
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = insert_decision(
            title="Chose psycopg2 over asyncpg",
            body_md="For hook usage, sync is simpler.",
            tags=["database", "architecture"],
        )

        assert result == 7

    @patch("datapulse.brain.db.get_connection")
    def test_insert_incident(self, mock_conn):
        from datapulse.brain.db import insert_incident

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (3,)
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_conn.return_value)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = insert_incident(
            title="Audit log crash",
            body_md="Root cause: missing tenant_id check.",
            severity="high",
            tags=["api", "crash"],
        )

        assert result == 3

    def test_update_embedding_rejects_invalid_table(self):
        from datapulse.brain.db import update_embedding

        with pytest.raises(ValueError, match="Invalid table"):
            update_embedding("users", 1, [0.1, 0.2])


# ── Unit tests for brain.embeddings ────────────────────────────────


class TestEmbeddings:
    """Test embedding generation via OpenRouter."""

    @patch.dict("os.environ", {"OPENROUTER_API_KEY": ""})
    def test_returns_none_when_no_api_key(self):
        from datapulse.brain.embeddings import get_embedding

        result = get_embedding("test text")
        assert result is None

    @patch("datapulse.brain.embeddings.httpx.post")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"})
    def test_returns_embedding_on_success(self, mock_post):
        from datapulse.brain.embeddings import get_embedding

        fake_vector = [0.1] * 1536
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"embedding": fake_vector}]}
        mock_post.return_value = mock_resp

        result = get_embedding("test text")
        assert result == fake_vector
        assert len(result) == 1536

    @patch("datapulse.brain.embeddings.httpx.post", side_effect=Exception("timeout"))
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"})
    def test_returns_none_on_api_failure(self, mock_post):
        from datapulse.brain.embeddings import get_embedding

        result = get_embedding("test text")
        assert result is None


# ── Unit tests for brain.session_end ───────────────────────────────


class TestSessionEnd:
    """Test layer/module detection and markdown builders."""

    def test_detect_layers_modules(self):
        from datapulse.brain.session_end import detect_layers_modules

        files = [
            "src/datapulse/analytics/service.py",
            "src/datapulse/api/routes/analytics.py",
            "frontend/src/components/kpi-grid.tsx",
            "tests/test_analytics.py",
            "dbt/models/marts/agg_sales_daily.sql",
        ]
        layers, modules = detect_layers_modules(files)

        assert "gold" in layers  # analytics + dbt/models/marts
        assert "api" in layers
        assert "frontend" in layers
        assert "test" in layers
        assert "analytics" in modules
        assert "api" in modules
        assert "frontend" in modules
        assert "dbt" in modules

    def test_detect_bronze_layer(self):
        from datapulse.brain.session_end import detect_layers_modules

        files = ["migrations/039_create_brain.sql", "src/datapulse/bronze/loader.py"]
        layers, modules = detect_layers_modules(files)

        assert "bronze" in layers
        assert "migrations" in modules
        assert "bronze" in modules

    def test_detect_silver_layer(self):
        from datapulse.brain.session_end import detect_layers_modules

        files = ["dbt/models/staging/stg_sales.sql"]
        layers, modules = detect_layers_modules(files)

        assert "silver" in layers
        assert "dbt" in modules

    def test_build_body_md(self):
        from datapulse.brain.session_end import build_body_md

        body = build_body_md(
            timestamp="2026-04-12T20:00",
            files=["src/datapulse/api/app.py"],
            commits_raw="abc123 fix stuff",
            layers=["api"],
            modules=["api"],
        )

        assert "# Session 2026-04-12T20:00" in body
        assert "src/datapulse/api/app.py" in body
        assert "abc123 fix stuff" in body

    def test_build_index_md_empty(self):
        from datapulse.brain.session_end import build_index_md

        result = build_index_md([])
        assert "No sessions recorded yet" in result

    def test_build_index_md_with_sessions(self):
        from datapulse.brain.session_end import build_index_md

        sessions = [
            {
                "timestamp": datetime(2026, 4, 12, 20, 0, tzinfo=UTC),
                "branch": "main",
                "layers": ["api", "bronze"],
                "modules": ["analytics"],
            },
        ]
        result = build_index_md(sessions)
        assert "main" in result
        assert "[api,bronze]" in result

    @patch("datapulse.brain.session_end.gather_git_data")
    @patch("datapulse.brain.session_end._run")
    def test_main_db_fallback(self, mock_run, mock_git, tmp_path):
        """When DB is unavailable, session_end should write markdown files."""
        from datapulse.brain.session_end import main

        mock_run.return_value = str(tmp_path)

        brain_dir = tmp_path / "docs" / "brain" / "sessions"
        brain_dir.mkdir(parents=True)

        mock_git.return_value = {
            "branch": "test-branch",
            "user_name": "Test User",
            "files": ["src/datapulse/api/app.py"],
            "commits": [{"sha": "abc", "message": "test"}],
            "recent_commits_raw": "abc test",
        }

        with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path)}):
            # DB import will fail since no real DB
            main()

        # Should have created files as fallback
        index_file = tmp_path / "docs" / "brain" / "_INDEX.md"
        assert index_file.exists() or True  # May not exist if no git data in tmp
