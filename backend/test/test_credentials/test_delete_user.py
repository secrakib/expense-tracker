"""
Test: credentials/delete_user  (PostgreSQL)
"""
import pytest
from backend.src.credentials.add_values import add_values
from backend.src.credentials.delete_user import delete_user
from backend.src.credentials.create_table import create_table
from backend.src.credentials.delete_table import delete_table
from backend.database.globals import DATABASE_URL


@pytest.fixture(scope="module", autouse=True)
def setup():
    delete_table(DATABASE_URL, "credentials")
    create_table(DATABASE_URL)
    yield
    delete_table(DATABASE_URL, "credentials")


def test_delete_user_success():
    add_values("rakin", password="pw", database_url=DATABASE_URL)
    result = delete_user(DATABASE_URL, user_name="rakin")
    assert "deleted" in result["message"].lower()


def test_delete_user_not_found_raises():
    with pytest.raises(ValueError, match="not found"):
        delete_user(DATABASE_URL, user_name="ghost_user_xyz")


def test_delete_user_case_insensitive():
    add_values("CaseUser", password="pw", database_url=DATABASE_URL)
    result = delete_user(DATABASE_URL, user_name="caseuser")
    assert "deleted" in result["message"].lower()