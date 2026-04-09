# conftest.py — Root test configuration


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location and dependencies.

    Tests in test files containing 'integration' or 'rls_db' in name get @pytest.mark.integration.
    Tests in test files containing 'e2e' get @pytest.mark.e2e.
    Everything else defaults to @pytest.mark.unit.
    """
    import pytest

    for item in items:
        filepath = str(item.fspath).replace("\\", "/")

        if "e2e" in filepath:
            item.add_marker(pytest.mark.e2e)
        elif any(kw in filepath for kw in ("integration", "_db_", "rls_db")):
            item.add_marker(pytest.mark.integration)
        elif any(kw in str(item.fixturenames) for kw in ("db_session", "client")):
            # Tests using DB fixtures are integration tests
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
