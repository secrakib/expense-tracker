"""
API tests for Expense Tracker using FastAPI TestClient.
Tests run sequentially against the test database.
Run with: pytest backend/test/test_api/test_api.py -v -s
"""

import json as json_lib
import pytest
from fastapi.testclient import TestClient

# ── Point all DB operations at the test database ────────────────────────────
import backend.database.globals as db_globals
#db_globals.location = "backend/test/test_database/database.db"

# Import app AFTER patching the location
from backend.src.api.main import app
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.feature.create_table import create_table as create_expenses_table
from backend.src.credentials.delete_table import delete_table

TEST_DB = "backend/test/test_database/database.db"

# Single client instance so cookies persist across requests
client = TestClient(app, raise_server_exceptions=True)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create fresh tables before all tests, drop them after."""
    delete_table(TEST_DB, "expenses")
    delete_table(TEST_DB, "credentials")
    create_credentials_table(TEST_DB)
    create_expenses_table(TEST_DB)
    yield
    delete_table(TEST_DB, "expenses")
    delete_table(TEST_DB, "credentials")


# ── Helpers ───────────────────────────────────────────────────────────────────

def do_login(username="testuser", password="testpass123"):
    """Log in and store the cookie on the shared client instance."""
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"Login failed: {response.text}"
    # Persist the cookie on the client so subsequent requests are authenticated
    client.cookies.set("access_token", response.cookies["access_token"])
    return response


def do_delete(url, body: dict):
    """Helper for DELETE requests with a JSON body (TestClient workaround)."""
    return client.request(
        "DELETE",
        url,
        content=json_lib.dumps(body),
        headers={"Content-Type": "application/json"},
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_01_register_user():
    response = client.post("/register", json={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 201
    assert "registered successfully" in response.json()["message"]


def test_02_register_duplicate_user():
    response = client.post("/register", json={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_03_login_success():
    response = do_login()
    assert response.json() == {"message": "Login successful"}
    assert "access_token" in response.cookies


def test_04_login_wrong_password():
    response = client.post("/token", data={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == 401


def test_05_login_unknown_user():
    response = client.post("/token", data={"username": "nobody", "password": "pass"})
    assert response.status_code == 401


def test_06_add_expense_authenticated():
    do_login()
    response = client.post(
        "/expenses",
        json={"category": "food", "expense": 25.50, "date": "2024-06-01"},
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Expense added successfully."


def test_07_add_expense_unauthenticated():
    client.cookies.clear()
    response = client.post(
        "/expenses",
        json={"category": "food", "expense": 25.50, "date": "2024-06-01"},
    )
    assert response.status_code == 401
    do_login()  # restore auth for subsequent tests


def test_08_get_expenses():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert "expenses" in response.json()
    assert len(response.json()["expenses"]) >= 1


def test_09_get_expenses_filter_by_category():
    client.post(
        "/expenses",
        json={"category": "transport", "expense": 10.00, "date": "2024-06-02"},
    )
    response = client.get("/expenses?category=transport")
    assert response.status_code == 200
    expenses = response.json()["expenses"]
    assert len(expenses) >= 1
    assert all(e["category"] == "transport" for e in expenses)


def test_10_get_expenses_filter_by_min_max():
    response = client.get("/expenses?min_expense=10&max_expense=30")
    assert response.status_code == 200
    for e in response.json()["expenses"]:
        assert 10 <= e["expense"] <= 30


def test_11_update_expense():
    expenses = client.get("/expenses").json()["expenses"]
    expense_id = expenses[0]["id"]
    response = client.put(
        "/expenses",
        json={"id": expense_id, "category": "groceries", "expense": 99.99},
    )
    assert response.status_code == 200
    assert str(expense_id) in response.json()["message"]


def test_12_update_expense_not_found():
    response = client.put("/expenses", json={"id": 999999, "category": "ghost"})
    assert response.status_code == 404


def test_13_delete_expense_by_category():
    client.post(
        "/expenses",
        json={"category": "todelete", "expense": 5.00, "date": "2024-06-03"},
    )
    response = do_delete("/expenses", {"category": "todelete"})
    assert response.status_code == 200
    assert response.json()["message"].startswith("1 record(s) deleted")


def test_14_delete_expense_no_filter():
    response = do_delete("/expenses", {})
    assert response.status_code == 422  # Validation: at least one filter required


def test_15_delete_user():
    client.post("/register", json={"username": "throwaway", "password": "pass123"})
    do_login(username="throwaway", password="pass123")
    response = client.delete("/expenses/throwaway")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()
    do_login()  # restore main user session


def test_16_access_after_logout():
    """After clearing cookies, requests should be rejected."""
    client.cookies.clear()
    response = client.get("/expenses")
    assert response.status_code == 401