"""
Test: FastAPI endpoints  (PostgreSQL)

Replaces the SQLite-based test_api.py. All DB setup/teardown
uses the real PostgreSQL DATABASE_URL from the environment.
"""
import json as json_lib
import pytest
from fastapi.testclient import TestClient

from backend.database.globals import DATABASE_URL
from backend.src.api.main import app
from backend.src.credentials.create_table import create_table as create_credentials_table
from backend.src.credentials.delete_table import delete_table
from backend.src.feature.create_table import create_table as create_expenses_table

client = TestClient(app, raise_server_exceptions=True)


# ── helpers ───────────────────────────────────────────────────────────────────

# File: backend/test/test_api/test_api.py (Modify do_login function)
def do_login(username: str = "testuser", password: str = "testpass123"):
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"Login failed: {response.text}"
    
    # Extract token from response body dictionary and assign to test client headers
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return response


def do_delete(url: str, body: dict):
    return client.request(
        "DELETE",
        url,
        content=json_lib.dumps(body),
        headers={"Content-Type": "application/json"},
    )


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Drop and recreate tables once per test session."""
    delete_table(DATABASE_URL, "expenses")
    delete_table(DATABASE_URL, "credentials")
    create_credentials_table(DATABASE_URL)
    create_expenses_table(DATABASE_URL)
    yield
    delete_table(DATABASE_URL, "expenses")
    delete_table(DATABASE_URL, "credentials")


# ── auth ──────────────────────────────────────────────────────────────────────

def test_01_register_user():
    response = client.post(
        "/register", json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 201
    assert "registered successfully" in response.json()["message"]


def test_02_register_duplicate_user():
    response = client.post(
        "/register", json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_03_login_success():
    response = do_login()
    data = response.json()
    
    # Assert against the updated JSON payload returned by the backend
    assert data.get("message") == "Login successful"
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


def test_04_login_wrong_password():
    response = client.post(
        "/token", data={"username": "testuser", "password": "wrongpass"}
    )
    assert response.status_code == 401


def test_05_login_unknown_user():
    response = client.post("/token", data={"username": "nobody", "password": "pass"})
    assert response.status_code == 401


# ── expenses CRUD ─────────────────────────────────────────────────────────────

def test_06_add_expense_authenticated():
    do_login()
    response = client.post(
        "/expenses",
        json={"category": "food", "expense": 25.50, "date": "2024-06-01"},
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Expense added successfully."


def test_07_add_expense_unauthenticated():
    # Clear both mechanisms to ensure a clean state
    client.cookies.clear()
    client.headers.pop("Authorization", None)  # <-- Drop the bearer header
    
    response = client.post(
        "/expenses",
        json={"category": "food", "expense": 25.50, "date": "2024-06-01"},
    )
    assert response.status_code == 401
    do_login()  # restore session for subsequent tests


def test_08_get_expenses_returns_dicts():
    response = client.get("/expenses")
    assert response.status_code == 200
    expenses = response.json()["expenses"]
    assert len(expenses) >= 1
    assert set(expenses[0].keys()) == {"id", "user_name", "category", "expense", "date"}


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


def test_11_get_categories():
    response = client.get("/expenses/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert "food" in data["categories"]
    assert "transport" in data["categories"]


def test_12_update_expense_returns_changes():
    expenses = client.get("/expenses").json()["expenses"]
    expense_id = expenses[0]["id"]
    response = client.put(
        "/expenses",
        json={"id": expense_id, "category": "groceries", "expense": 99.99},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["updated_id"] == expense_id
    assert data["changes"]["category"] == "groceries"
    assert data["changes"]["expense"] == 99.99


def test_13_update_expense_not_found():
    response = client.put("/expenses", json={"id": 999_999_999, "category": "ghost"})
    assert response.status_code == 404


def test_14_delete_expense_by_category():
    client.post(
        "/expenses",
        json={"category": "todelete", "expense": 5.00, "date": "2024-06-03"},
    )
    response = do_delete("/expenses", {"category": "todelete"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"].startswith("1 record(s) deleted")
    assert len(data["deleted_ids"]) == 1


def test_15_delete_expense_no_filter_returns_422():
    response = do_delete("/expenses", {})
    assert response.status_code == 422


def test_16_delete_user():
    client.post("/register", json={"username": "throwaway", "password": "pass123"})
    do_login(username="throwaway", password="pass123")
    response = client.delete("/expenses/throwaway")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()
    do_login()  # restore primary session


def test_17_access_after_logout():
    # Simulate an absolute logout
    client.cookies.clear()
    client.headers.pop("Authorization", None)  # <-- Drop the bearer header
    
    response = client.get("/expenses")
    assert response.status_code == 401


def test_18_filter_by_date():
    do_login()
    client.post(
        "/expenses",
        json={"category": "datecheck", "expense": 3.33, "date": "2000-01-01"},
    )
    response = client.get("/expenses?date=2000-01-01")
    assert response.status_code == 200
    expenses = response.json()["expenses"]
    assert len(expenses) >= 1
    assert all(str(e["date"]) == "2000-01-01" for e in expenses)


def test_19_add_expense_invalid_payload():
    do_login()
    # missing required fields
    response = client.post("/expenses", json={"category": "food"})
    assert response.status_code == 422