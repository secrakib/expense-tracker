"""
Test: credentials/add_values  (PostgreSQL)
"""
import pytest
from backend.src.credentials.add_values import add_values
from backend.src.credentials.delete_table import delete_table
from backend.src.credentials.create_table import create_table
from backend.database.globals import DATABASE_URL


@pytest.fixture(scope="module", autouse=True)
def setup_credentials_table():
    delete_table(DATABASE_URL, "credentials")
    create_table(DATABASE_URL)
    yield
    delete_table(DATABASE_URL, "credentials")


def test_add_values_success():
    result = add_values("rakib", password="adse4cc", database_url=DATABASE_URL)
    assert result is None  # None means success (no duplicate)


def test_add_values_duplicate_returns_message():
    add_values("duplicate_user", password="pass123", database_url=DATABASE_URL)
    result = add_values("duplicate_user", password="pass123", database_url=DATABASE_URL)
    assert result is not None
    assert result["message"] == "duplicate"


def test_add_values_stores_lowercase_username():
    from backend.src.credentials.admin_filter_and_show import admin_filter_expenses
    add_values("UpperUser", password="pw", database_url=DATABASE_URL)
    rows = admin_filter_expenses(DATABASE_URL, "upperuser")
    assert len(rows) >= 1