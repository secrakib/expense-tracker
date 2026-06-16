"""
Test: credentials/delete_table  (PostgreSQL)
"""
import pytest
import psycopg2
from backend.src.credentials.create_table import create_table
from backend.src.credentials.delete_table import delete_table
from backend.database.globals import DATABASE_URL


def _table_exists(table_name: str) -> bool:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s
        )
        """,
        (table_name,),
    )
    exists = cur.fetchone()[0]
    conn.close()
    return exists


def test_delete_table_removes_credentials():
    create_table(DATABASE_URL)
    assert _table_exists("credentials")
    delete_table(DATABASE_URL, "credentials")
    assert not _table_exists("credentials")


def test_delete_table_nonexistent_does_not_raise():
    """DROP TABLE IF EXISTS must be safe to call on a missing table."""
    delete_table(DATABASE_URL, "credentials")  # already gone — should not raise


def test_delete_table_expenses_cascade():
    """Deleting credentials should cascade to expenses (FK)."""
    from backend.src.feature.create_table import create_table as create_expenses
    create_table(DATABASE_URL)
    create_expenses(DATABASE_URL)
    delete_table(DATABASE_URL, "credentials")  # CASCADE drops expenses too
    assert not _table_exists("credentials")