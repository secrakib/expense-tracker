"""
Test: feature layer — add / filter / update / delete / categories  (PostgreSQL)

Replaces all the loose ad-hoc scripts in test_feature/ with a single
properly-structured pytest module backed by the real PostgreSQL database.
"""
import pytest
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.credentials.add_values import add_values as add_credential
from backend.src.credentials.delete_table import delete_table
from backend.src.feature.create_table import create_table as create_expenses_table
from backend.src.feature.add_values import add_values
from backend.src.feature.filter_and_show import filter_expenses
from backend.src.feature.get_categories import get_categories
from backend.src.feature.update_values import update_values
from backend.src.feature.delete_record import delete_record
from backend.test.test_feature.globals import DATABASE_URL

TEST_USER = "testfeatureuser_pg"


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Fresh schema + seed user before the module; teardown after."""
    delete_table(DATABASE_URL, "expenses")
    delete_table(DATABASE_URL, "credentials")
    create_credentials_table(DATABASE_URL)
    create_expenses_table(DATABASE_URL)
    add_credential(TEST_USER, "hashed_pw", DATABASE_URL)
    yield
    delete_table(DATABASE_URL, "expenses")
    delete_table(DATABASE_URL, "credentials")


# ── add_values ────────────────────────────────────────────────────────────────

def test_add_values_returns_success_dict():
    result = add_values(TEST_USER, "food", 25.50, "2024-06-01", DATABASE_URL)
    assert isinstance(result, dict)
    assert result["message"] == "Expense added successfully."


def test_add_values_stores_lowercase_category():
    add_values(TEST_USER, "Transport", 10.00, "2024-06-02", DATABASE_URL)
    rows = filter_expenses(DATABASE_URL, TEST_USER, category="transport")
    assert len(rows) >= 1
    assert all(r["category"] == "transport" for r in rows)


def test_add_values_unknown_user_raises():
    """ForeignKeyViolation from psycopg2 must surface as ValueError."""
    with pytest.raises(ValueError):
        add_values("no_such_user_xyz", "food", 9.99, "2024-01-01", DATABASE_URL)


# ── filter_expenses ───────────────────────────────────────────────────────────

def test_filter_expenses_returns_list_of_dicts():
    rows = filter_expenses(DATABASE_URL, TEST_USER)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert set(rows[0].keys()) == {"id", "user_name", "category", "expense", "date"}


def test_filter_expenses_by_category():
    rows = filter_expenses(DATABASE_URL, TEST_USER, category="food")
    assert all(r["category"] == "food" for r in rows)


def test_filter_expenses_by_min_max():
    rows = filter_expenses(DATABASE_URL, TEST_USER, min_expense=10.0, max_expense=30.0)
    for r in rows:
        assert 10.0 <= r["expense"] <= 30.0


def test_filter_expenses_nonexistent_category_returns_empty():
    rows = filter_expenses(DATABASE_URL, TEST_USER, category="nonexistentcategory_xyz")
    assert rows == []


def test_filter_expenses_by_date():
    add_values(TEST_USER, "datetest", 1.00, "2000-01-01", DATABASE_URL)
    rows = filter_expenses(DATABASE_URL, TEST_USER, date="2000-01-01")
    assert len(rows) >= 1
    assert all(str(r["date"]) == "2000-01-01" for r in rows)


# ── get_categories ────────────────────────────────────────────────────────────

def test_get_categories_returns_list():
    cats = get_categories(DATABASE_URL, TEST_USER)
    assert isinstance(cats, list)
    assert "food" in cats
    assert "transport" in cats


def test_get_categories_new_user_returns_empty():
    add_credential("emptyuser_pg", "pw", DATABASE_URL)
    cats = get_categories(DATABASE_URL, "emptyuser_pg")
    assert cats == []


# ── update_values ─────────────────────────────────────────────────────────────

def test_update_values_category():
    rows = filter_expenses(DATABASE_URL, TEST_USER, category="food")
    target_id = rows[0]["id"]
    result = update_values(DATABASE_URL, target_id, TEST_USER, category="groceries")
    assert result["updated_id"] == target_id
    assert result["changes"]["category"] == "groceries"


def test_update_values_multiple_fields():
    rows = filter_expenses(DATABASE_URL, TEST_USER, category="groceries")
    target_id = rows[0]["id"]
    result = update_values(
        DATABASE_URL, target_id, TEST_USER, expense=99.99, date="2025-01-01"
    )
    assert result["changes"]["expense"] == 99.99
    assert result["changes"]["date"] == "2025-01-01"
    assert "category" not in result["changes"]


def test_update_values_invalid_id_raises():
    with pytest.raises(ValueError):
        update_values(DATABASE_URL, 999_999_999, TEST_USER, category="ghost")


def test_update_values_no_fields_raises():
    rows = filter_expenses(DATABASE_URL, TEST_USER)
    target_id = rows[0]["id"]
    with pytest.raises(ValueError):
        update_values(DATABASE_URL, target_id, TEST_USER)


# ── delete_record ─────────────────────────────────────────────────────────────

def test_delete_record_by_category():
    add_values(TEST_USER, "todelete", 1.00, "2024-01-01", DATABASE_URL)
    result = delete_record(DATABASE_URL, TEST_USER, category="todelete")
    assert result["message"].startswith("1 record(s) deleted")
    assert isinstance(result["deleted_ids"], list)
    assert len(result["deleted_ids"]) == 1


def test_delete_record_no_filter_raises():
    with pytest.raises(ValueError):
        delete_record(DATABASE_URL, TEST_USER)


def test_delete_record_no_match_returns_zero():
    result = delete_record(DATABASE_URL, TEST_USER, category="doesnotexist_xyz")
    assert result["message"].startswith("0 record(s) deleted")
    assert result["deleted_ids"] == []


def test_delete_record_by_min_expense():
    add_values(TEST_USER, "bigspend", 500.00, "2024-03-01", DATABASE_URL)
    result = delete_record(DATABASE_URL, TEST_USER, min_expense=400.0)
    assert len(result["deleted_ids"]) >= 1


def test_delete_record_by_date():
    add_values(TEST_USER, "datedelete", 7.77, "1999-12-31", DATABASE_URL)
    result = delete_record(DATABASE_URL, TEST_USER, date="1999-12-31")
    assert len(result["deleted_ids"]) >= 1