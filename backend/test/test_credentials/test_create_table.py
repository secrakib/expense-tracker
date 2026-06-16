"""
Test: credentials/create_table  (PostgreSQL)
"""
import pytest
import psycopg2
from backend.src.credentials.create_table import create_table
from backend.src.credentials.delete_table import delete_table
from backend.database.globals import DATABASE_URL


def test_create_table_runs_without_error():
    delete_table(DATABASE_URL, "credentials")
    create_table(DATABASE_URL)  # should not raise


def test_create_table_is_idempotent():
    """Calling create_table twice must not raise (IF NOT EXISTS semantics)."""
    create_table(DATABASE_URL)
    create_table(DATABASE_URL)


def test_credentials_table_has_expected_columns():
    create_table(DATABASE_URL)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'credentials'
        ORDER BY ordinal_position
        """
    )
    cols = [row[0] for row in cur.fetchall()]
    conn.close()
    assert "user_name" in cols
    assert "password" in cols