"""Tests for the leads capture service and POST /api/v1/leads route."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datapulse.leads.models import LeadRequest
from datapulse.leads.service import LeadService


def make_repo(email_exists: bool = False) -> MagicMock:
    repo = MagicMock()
    repo.email_exists.return_value = email_exists
    return repo


def test_capture_new_lead_inserts():
    repo = make_repo(email_exists=False)
    svc = LeadService(repo)
    result = svc.capture(LeadRequest(email="new@example.com", name="Ali", company="Pharma Co"))
    assert result.success is True
    repo.insert.assert_called_once()


def test_capture_duplicate_does_not_insert():
    repo = make_repo(email_exists=True)
    svc = LeadService(repo)
    result = svc.capture(LeadRequest(email="dup@example.com"))
    assert result.success is True
    repo.insert.assert_not_called()


def test_lead_request_requires_valid_email():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LeadRequest(email="not-an-email")
