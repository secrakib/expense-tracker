"""
Unit tests for feature-layer DB functions.
Run with: pytest backend/test/test_feature/ -v -s
"""

import pytest
from backend.src.feature.create_table import create_table
from backend.src.feature.add_values import add_values
from backend.src.feature.filter_and_show import filter_expenses
from backend.src.feature.get_categories import get_categories
from backend.src.feature.update_values import update_values
from backend.src.feature.delete_record import delete_record
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.credentials.add_values import add_values as add_credential
from backend.src.credentials.delete_table import delete_table

TEST_DB = "backend/test/test_database/database.db"
TEST_USER = "testfeatureuser"


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Fresh tables for the module, seed one user so FK constraint passes."""
    delete_table(TEST_DB, "expenses")
    delete_table(TEST_DB, "credentials")
    create_credentials_table(TEST_DB)
    create_table(TEST_DB)
    add_credential(TEST_USER, "hashed_pw", TEST_DB)
    yield
    delete_table(TEST_DB, "expenses")
    delete_table(TEST_DB, "credentials")


# ── add_values ────────────────────────────────────────────────────────────────

def test_add_values_returns_dict():
    result = add_values(TEST_USER, "food", 25.50, "2024-06-01", TEST_DB)
    assert isinstance(result, dict)
    assert result["message"] == "Expense added successfully."


def test_add_values_stores_lowercase_category():
    add_values(TEST_USER, "Transport", 10.00, "2024-06-02", TEST_DB)
    rows = filter_expenses(TEST_DB, TEST_USER, category="transport")
    assert len(rows) >= 1
    assert rows[0]["category"] == "transport"


# ── filter_expenses ───────────────────────────────────────────────────────────

def test_filter_expenses_returns_list_of_dicts():
    rows = filter_expenses(TEST_DB, TEST_USER)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    first = rows[0]
    assert set(first.keys()) == {"id", "user_name", "category", "expense", "date"}


def test_filter_expenses_by_category():
    rows = filter_expenses(TEST_DB, TEST_USER, category="food")
    assert all(r["category"] == "food" for r in rows)


def test_filter_expenses_by_min_max():
    rows = filter_expenses(TEST_DB, TEST_USER, min_expense=10.0, max_expense=30.0)
    for r in rows:
        assert 10.0 <= r["expense"] <= 30.0


def test_filter_expenses_empty_result_is_not_an_error():
    rows = filter_expenses(TEST_DB, TEST_USER, category="nonexistentcategory")
    assert rows == []


# ── get_categories ────────────────────────────────────────────────────────────

def test_get_categories_returns_list():
    cats = get_categories(TEST_DB, TEST_USER)
    assert isinstance(cats, list)
    assert "food" in cats
    assert "transport" in cats


def test_get_categories_no_expenses_returns_empty():
    # Use a fresh user with no expenses (must exist in credentials)
    add_credential("emptyuser", "pw", TEST_DB)
    cats = get_categories(TEST_DB, "emptyuser")
    assert cats == []


# ── update_values ─────────────────────────────────────────────────────────────

def test_update_values_returns_updated_id_and_changes():
    rows = filter_expenses(TEST_DB, TEST_USER, category="food")
    target_id = rows[0]["id"]
    result = update_values(TEST_DB, target_id, TEST_USER, category="groceries")
    assert result["updated_id"] == target_id
    assert result["changes"]["category"] == "groceries"


def test_update_values_multiple_fields():
    rows = filter_expenses(TEST_DB, TEST_USER, category="groceries")
    target_id = rows[0]["id"]
    result = update_values(TEST_DB, target_id, TEST_USER, expense=99.99, date="2025-01-01")
    assert result["changes"]["expense"] == 99.99
    assert result["changes"]["date"] == "2025-01-01"
    assert "category" not in result["changes"]


def test_update_values_invalid_id_raises():
    with pytest.raises(ValueError):
        update_values(TEST_DB, 999999, TEST_USER, category="ghost")


def test_update_values_no_fields_raises():
    rows = filter_expenses(TEST_DB, TEST_USER)
    target_id = rows[0]["id"]
    with pytest.raises(ValueError):
        update_values(TEST_DB, target_id, TEST_USER)


# ── delete_record ─────────────────────────────────────────────────────────────

def test_delete_record_returns_dict_with_ids():
    add_values(TEST_USER, "todelete", 1.00, "2024-01-01", TEST_DB)
    result = delete_record(TEST_DB, TEST_USER, category="todelete")
    assert result["message"].startswith("1 record(s) deleted")
    assert isinstance(result["deleted_ids"], list)
    assert len(result["deleted_ids"]) == 1


def test_delete_record_no_filter_raises():
    with pytest.raises(ValueError):
        delete_record(TEST_DB, TEST_USER)


def test_delete_record_no_match_returns_zero():
    result = delete_record(TEST_DB, TEST_USER, category="doesnotexist")
    assert result["message"].startswith("0 record(s) deleted")
    assert result["deleted_ids"] == []