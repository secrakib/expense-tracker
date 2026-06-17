"""
Expense Tracker — Streamlit Frontend
Communicates with the FastAPI backend via HTTP (requests library).
Set BACKEND_URL in the environment or update the constant below.
"""
from __future__ import annotations

import os
from datetime import date
from typing import Optional

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── config ────────────────────────────────────────────────────────────────────

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")

st.set_page_config(
    page_title="💰 Expense Tracker",
    page_icon="💰",
    layout="centered",
)

# ── session helpers ───────────────────────────────────────────────────────────

def _session() -> requests.Session:
    """Return (or create) a persistent requests.Session stored in st.session_state."""
    if "http_session" not in st.session_state:
        st.session_state["http_session"] = requests.Session()
    return st.session_state["http_session"]


def _is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)


def _username() -> str:
    return st.session_state.get("username", "")


# ── API wrappers ──────────────────────────────────────────────────────────────

def api_register(username: str, password: str) -> tuple[bool, str]:
    try:
        r = _session().post(
            f"{BACKEND_URL}/register",
            json={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 201:
            return True, r.json().get("message", "Registered.")
        return False, r.json().get("detail", "Registration failed.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_login(username: str, password: str) -> tuple[bool, str]:
    try:
        r = _session().post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            # Attach the Bearer token to the persistent session
            _session().headers.update({"Authorization": f"Bearer {token}"})
            return True, "Login successful."
        return False, r.json().get("detail", "Login failed.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_logout() -> None:
    _session().cookies.clear()
    _session().headers.pop("Authorization", None)
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    # Clear any cached preview data
    st.session_state.pop("del_preview", None)


def api_get_expenses(
    category: Optional[str] = None,
    date_filter: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> tuple[bool, list | str]:
    params: dict = {}
    if category:
        params["category"] = category
    if date_filter:
        params["date"] = date_filter
    if min_expense is not None:
        params["min_expense"] = min_expense
    if max_expense is not None:
        params["max_expense"] = max_expense
    try:
        r = _session().get(f"{BACKEND_URL}/expenses", params=params, timeout=10)
        if r.status_code == 200:
            return True, r.json().get("expenses", [])
        if r.status_code == 401:
            return False, "Session expired. Please sign in again."
        return False, r.json().get("detail", "Failed to fetch expenses.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_get_categories() -> list[str]:
    try:
        r = _session().get(f"{BACKEND_URL}/expenses/categories", timeout=10)
        if r.status_code == 200:
            return r.json().get("categories", [])
    except requests.RequestException:
        pass
    return []


def api_add_expense(category: str, expense: float, date_val: str) -> tuple[bool, str]:
    try:
        r = _session().post(
            f"{BACKEND_URL}/expenses",
            json={"category": category, "expense": expense, "date": date_val},
            timeout=10,
        )
        if r.status_code == 201:
            return True, r.json().get("message", "Expense added.")
        if r.status_code == 401:
            return False, "Session expired. Please sign in again."
        return False, r.json().get("detail", "Failed to add expense.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_update_expense(
    expense_id: int,
    category: Optional[str],
    expense: Optional[float],
    date_val: Optional[str],
) -> tuple[bool, str]:
    body: dict = {"id": expense_id}
    if category:
        body["category"] = category
    if expense is not None:
        body["expense"] = expense
    if date_val:
        body["date"] = date_val
    try:
        r = _session().put(f"{BACKEND_URL}/expenses", json=body, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, f"Updated ID {data['updated_id']} — changes: {data['changes']}"
        if r.status_code == 401:
            return False, "Session expired. Please sign in again."
        return False, r.json().get("detail", "Failed to update expense.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_delete_expense(
    category: Optional[str] = None,
    date_filter: Optional[str] = None,
    min_expense: Optional[float] = None,
    max_expense: Optional[float] = None,
) -> tuple[bool, str]:
    body: dict = {}
    if category:
        body["category"] = category
    if date_filter:
        body["date"] = date_filter
    if min_expense is not None:
        body["min_expense"] = min_expense
    if max_expense is not None:
        body["max_expense"] = max_expense
    try:
        r = _session().request(
            "DELETE",
            f"{BACKEND_URL}/expenses",
            json=body,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return True, f"{data['message']} (IDs: {data['deleted_ids']})"
        if r.status_code == 401:
            return False, "Session expired. Please sign in again."
        return False, r.json().get("detail", "Failed to delete expenses.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


def api_delete_account() -> tuple[bool, str]:
    try:
        r = _session().delete(
            f"{BACKEND_URL}/expenses/{_username()}",
            timeout=10,
        )
        if r.status_code == 200:
            return True, r.json().get("message", "Account deleted.")
        if r.status_code == 401:
            return False, "Session expired. Please sign in again."
        return False, r.json().get("detail", "Failed to delete account.")
    except requests.RequestException as e:
        return False, f"Network error: {e}"


# ── UI pages ──────────────────────────────────────────────────────────────────

def page_auth() -> None:
    st.title("💰 Expense Tracker")
    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        st.subheader("Sign In")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Sign In", use_container_width=True):
            if not username or not password:
                st.warning("Please fill in both fields.")
            else:
                ok, msg = api_login(username, password)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username.lower()
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        st.subheader("Create Account")
        new_user = st.text_input("Username", key="reg_user")
        new_pass = st.text_input("Password", type="password", key="reg_pass")
        new_pass2 = st.text_input("Confirm Password", type="password", key="reg_pass2")
        if st.button("Create Account", use_container_width=True):
            if not new_user or not new_pass:
                st.warning("Please fill in all fields.")
            elif new_pass != new_pass2:
                st.error("Passwords do not match.")
            else:
                ok, msg = api_register(new_user, new_pass)
                if ok:
                    st.success(msg + " You can now sign in.")
                else:
                    st.error(msg)


def page_view() -> None:
    st.header("📋 My Expenses")

    categories = [""] + api_get_categories()

    with st.expander("Filters", expanded=False):
        col1, col2 = st.columns(2)
        cat_filter = col1.selectbox("Category", categories, key="view_cat")
        date_filter_val = col2.date_input(
            "Date", value=None, key="view_date", format="YYYY-MM-DD"
        )
        col3, col4 = st.columns(2)
        min_exp = col3.number_input("Min amount", min_value=0.0, value=0.0, key="view_min")
        max_exp = col4.number_input("Max amount", min_value=0.0, value=0.0, key="view_max")
        st.button("Apply Filters", use_container_width=True)  # triggers rerun naturally

    date_str = str(date_filter_val) if date_filter_val else None
    min_val = min_exp if min_exp > 0 else None
    max_val = max_exp if max_exp > 0 else None

    ok, data = api_get_expenses(
        category=cat_filter or None,
        date_filter=date_str,
        min_expense=min_val,
        max_expense=max_val,
    )
    if ok:
        if not data:
            st.info("No expenses found.")
        else:
            display = [
                {
                    "ID": r["id"],
                    "Category": r["category"],
                    "Amount (£)": f"{r['expense']:.2f}",
                    "Date": str(r["date"]),
                }
                for r in data
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)
            total = sum(r["expense"] for r in data)
            st.metric("Total", f"£{total:,.2f}")
    else:
        st.error(data)
        if "Session expired" in str(data):
            api_logout()
            st.rerun()


def page_add() -> None:
    st.header("➕ Add Expense")

    existing_cats = api_get_categories()
    cat_options = ["-- type new --"] + existing_cats

    col1, col2 = st.columns(2)
    cat_choice = col1.selectbox("Category", cat_options, key="add_cat_sel")
    if cat_choice == "-- type new --":
        category = col2.text_input("New category name", key="add_cat_new").strip().lower()
    else:
        category = cat_choice

    amount = st.number_input("Amount (£)", min_value=0.01, step=0.01, key="add_amount")
    expense_date = st.date_input("Date", value=date.today(), key="add_date", format="YYYY-MM-DD")

    if st.button("Add Expense", use_container_width=True):
        if not category:
            st.warning("Please enter a category.")
        elif amount <= 0:
            st.warning("Amount must be greater than zero.")
        else:
            ok, msg = api_add_expense(category, amount, str(expense_date))
            if ok:
                st.success(msg)
            else:
                st.error(msg)
                if "Session expired" in msg:
                    api_logout()
                    st.rerun()


def page_update() -> None:
    st.header("✏️ Update Expense")

    ok, data = api_get_expenses()
    if not ok:
        st.error(data)
        if "Session expired" in str(data):
            api_logout()
            st.rerun()
        return
    if not data:
        st.info("No expenses to update.")
        return

    id_map = {
        f"ID {r['id']} — {r['category']} £{r['expense']:.2f} ({r['date']})": r["id"]
        for r in data
    }
    chosen_label = st.selectbox("Select expense to edit", list(id_map.keys()), key="upd_sel")
    expense_id = id_map[chosen_label]

    st.divider()
    st.caption("Leave a field blank / zero to keep the current value.")

    categories = api_get_categories()
    new_cat = st.selectbox(
        "New category (optional)",
        [""] + categories,
        key="upd_cat",
    )
    custom_cat = ""
    if new_cat == "":
        custom_cat = st.text_input("Or type a new category", key="upd_cat_custom").strip().lower()

    new_amount = st.number_input(
        "New amount (0 = keep current)",
        min_value=0.0,
        value=0.0,
        step=0.01,
        key="upd_amount",
    )
    new_date = st.date_input(
        "New date (optional)",
        value=None,
        key="upd_date",
        format="YYYY-MM-DD",
    )

    if st.button("Update", use_container_width=True):
        final_cat = custom_cat or new_cat or None
        final_amount = new_amount if new_amount > 0 else None
        final_date = str(new_date) if new_date else None

        if not any([final_cat, final_amount, final_date]):
            st.warning("Please change at least one field.")
        else:
            ok, msg = api_update_expense(expense_id, final_cat, final_amount, final_date)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
                if "Session expired" in msg:
                    api_logout()
                    st.rerun()


def page_delete() -> None:
    st.header("🗑️ Delete Expenses")
    st.warning("Deletion is permanent. Preview before confirming.", icon="⚠️")

    categories = [""] + api_get_categories()

    cat_filter = st.selectbox("Category filter", categories, key="del_cat")
    col1, col2 = st.columns(2)
    date_filter_val = col1.date_input("Date filter", value=None, key="del_date", format="YYYY-MM-DD")
    col3, col4 = st.columns(2)
    min_exp = col3.number_input("Min amount", min_value=0.0, value=0.0, key="del_min")
    max_exp = col4.number_input("Max amount", min_value=0.0, value=0.0, key="del_max")

    date_str = str(date_filter_val) if date_filter_val else None
    min_val = min_exp if min_exp > 0 else None
    max_val = max_exp if max_exp > 0 else None

    if st.button("Preview matches", use_container_width=True):
        ok, data = api_get_expenses(
            category=cat_filter or None,
            date_filter=date_str,
            min_expense=min_val,
            max_expense=max_val,
        )
        if ok:
            st.session_state["del_preview"] = data
            # Store the filter params used for preview so delete uses the same
            st.session_state["del_params"] = {
                "category": cat_filter or None,
                "date_filter": date_str,
                "min_val": min_val,
                "max_val": max_val,
            }
        else:
            st.error(data)
            if "Session expired" in str(data):
                api_logout()
                st.rerun()

    preview = st.session_state.get("del_preview")

    if preview is not None:
        if len(preview) == 0:
            st.info("No matching expenses found.")
        else:
            st.subheader(f"{len(preview)} expense(s) will be deleted:")
            display = [
                {
                    "ID": r["id"],
                    "Category": r["category"],
                    "Amount (£)": f"{r['expense']:.2f}",
                    "Date": str(r["date"]),
                }
                for r in preview
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)

            if st.button("✅ Confirm Delete", type="primary", use_container_width=True):
                params = st.session_state.get("del_params", {})
                ok, msg = api_delete_expense(
                    category=params.get("category"),
                    date_filter=params.get("date_filter"),
                    min_expense=params.get("min_val"),
                    max_expense=params.get("max_val"),
                )
                if ok:
                    st.success(msg)
                    st.session_state.pop("del_preview", None)
                    st.session_state.pop("del_params", None)
                else:
                    st.error(msg)
                    if "Session expired" in msg:
                        api_logout()
                        st.rerun()


def page_account() -> None:
    st.header("👤 Account")
    st.write(f"Signed in as **{_username()}**")

    st.divider()
    st.subheader("Delete Account")
    st.error(
        "This will permanently delete your account and all your expense data.",
        icon="🚨",
    )
    confirm = st.checkbox("I understand this action cannot be undone.", key="del_acc_confirm")
    if st.button("Delete My Account", disabled=not confirm, use_container_width=True):
        ok, msg = api_delete_account()
        if ok:
            st.success(msg)
            api_logout()
            st.rerun()
        else:
            st.error(msg)


# ── main layout ───────────────────────────────────────────────────────────────

def main() -> None:
    if not _is_logged_in():
        page_auth()
        return

    with st.sidebar:
        st.markdown("### 💰 Expense Tracker")
        st.caption(f"Signed in as **{_username()}**")
        st.divider()
        page = st.radio(
            "Navigate",
            ["View Expenses", "Add Expense", "Update Expense", "Delete Expenses", "Account"],
            key="nav",
        )
        st.divider()
        if st.button("Sign Out", use_container_width=True):
            api_logout()
            st.rerun()

    pages = {
        "View Expenses": page_view,
        "Add Expense": page_add,
        "Update Expense": page_update,
        "Delete Expenses": page_delete,
        "Account": page_account,
    }
    pages[page]()


if __name__ == "__main__":
    main()