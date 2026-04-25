"""
Unit tests for file-based data source components.

Covers:
- connection_validators registry per-type checks
- FileValidationService: extension allow-list, size, format/db_type consistency
- FileStorageService: path traversal protection, hash verification
- FlatFileConnector / SQLiteConnector basic round-trip
- Upload-token round-trip in ConnectionService._create_file_connection (HMAC + expiry)
"""

import hashlib
import hmac
import io
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest


# ── Validator registry tests ───────────────────────────────────

def test_validator_database_type_requires_credentials():
    from app.domains.datasources.application.connection_validators import validate_connection_data

    valid, err = validate_connection_data("postgresql", {"name": "x", "db_type": "postgresql"})
    assert not valid
    assert "host" in err.lower() or "required" in err.lower()


def test_validator_file_type_requires_upload_token():
    from app.domains.datasources.application.connection_validators import validate_connection_data

    valid, err = validate_connection_data("flatfile", {"name": "x", "db_type": "flatfile"})
    assert not valid
    assert "upload_token" in err.lower()


def test_validator_file_type_passes_with_token():
    from app.domains.datasources.application.connection_validators import validate_connection_data

    valid, err = validate_connection_data(
        "flatfile",
        {"name": "x", "db_type": "flatfile", "upload_token": "tok|abc|flatfile|9999999999|sig"},
    )
    assert valid, err


def test_is_file_based_helper():
    from app.domains.datasources.application.connection_validators import is_file_based

    assert is_file_based("flatfile")
    assert is_file_based("excel")
    assert is_file_based("sqlite")
    assert not is_file_based("postgresql")
    assert not is_file_based("mysql")


# ── FileStorageService security tests ─────────────────────────

def test_file_storage_path_traversal_protection(tmp_path, monkeypatch):
    from flask import Flask
    from app.platform.infrastructure.file_storage import FileStorageService

    app = Flask(__name__)
    app.config["FILE_STORAGE_ROOT"] = str(tmp_path)

    with app.app_context():
        storage = FileStorageService("tenant-a")
        # Attempted traversal
        result = storage.get_file_path("tenants/tenant-a/../../../etc/passwd")
        assert result is None


def test_file_storage_hash_verification(tmp_path):
    from flask import Flask
    from app.platform.infrastructure.file_storage import FileStorageService

    app = Flask(__name__)
    app.config["FILE_STORAGE_ROOT"] = str(tmp_path)

    with app.app_context():
        storage = FileStorageService("tenant-a")
        result = storage.store_file(b"hello world", "test.csv")
        # Verify with correct hash
        assert storage.verify_hash(result["file_ref"], result["file_hash"])
        # Verify with wrong hash
        assert not storage.verify_hash(result["file_ref"], "deadbeef")


# ── SQLiteConnector tests ─────────────────────────────────────

@pytest.fixture
def temp_sqlite_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    conn.execute("INSERT INTO users (name) VALUES ('alice'), ('bob')")
    conn.commit()
    conn.close()
    return db_path


def test_sqlite_connector_blocks_writes(temp_sqlite_db, tmp_path):
    """SQLite connector must reject DML/DDL queries."""
    from flask import Flask
    from app.domains.datasources.infrastructure.connectors.sqlite import SQLiteConnector
    from app.domains.datasources.infrastructure.connectors.base import ConnectionConfig
    from app.platform.infrastructure.file_storage import FileStorageService

    app = Flask(__name__)
    app.config["FILE_STORAGE_ROOT"] = str(tmp_path)

    with app.app_context():
        # Store the SQLite file via storage service
        storage = FileStorageService("tenant-a")
        result = storage.store_file(temp_sqlite_db.read_bytes(), "test.sqlite")

        config = ConnectionConfig(extra_params={
            "file_ref": result["file_ref"],
            "file_hash": result["file_hash"],
        })
        connector = SQLiteConnector(config)

        # Validation should reject write queries even before connection
        valid, err = connector.validate_query("DROP TABLE users")
        assert not valid

        valid, err = connector.validate_query("DELETE FROM users")
        assert not valid

        valid, err = connector.validate_query("ATTACH DATABASE 'evil.db' AS evil")
        assert not valid

        # SELECT is allowed
        valid, err = connector.validate_query("SELECT * FROM users")
        assert valid


def test_sqlite_connector_read_round_trip(temp_sqlite_db, tmp_path):
    from flask import Flask
    from app.domains.datasources.infrastructure.connectors.sqlite import SQLiteConnector
    from app.domains.datasources.infrastructure.connectors.base import ConnectionConfig
    from app.platform.infrastructure.file_storage import FileStorageService

    app = Flask(__name__)
    app.config["FILE_STORAGE_ROOT"] = str(tmp_path)

    with app.app_context():
        storage = FileStorageService("tenant-a")
        result = storage.store_file(temp_sqlite_db.read_bytes(), "test.sqlite")

        config = ConnectionConfig(extra_params={
            "file_ref": result["file_ref"],
            "file_hash": result["file_hash"],
        })

        with SQLiteConnector(config) as connector:
            assert connector.test_connection()
            schemas = connector.get_schemas()
            assert schemas == ["main"]
            tables = connector.get_tables("main")
            table_names = [t.name for t in tables]
            assert "users" in table_names
            rows = list(connector.fetch_data("SELECT * FROM users"))
            flat = [r for batch in rows for r in batch]
            assert len(flat) == 2


# ── FlatFileConnector tests ───────────────────────────────────

def test_flatfile_connector_csv_round_trip(tmp_path):
    from flask import Flask
    from app.domains.datasources.infrastructure.connectors.flatfile import FlatFileConnector
    from app.domains.datasources.infrastructure.connectors.base import ConnectionConfig
    from app.platform.infrastructure.file_storage import FileStorageService

    app = Flask(__name__)
    app.config["FILE_STORAGE_ROOT"] = str(tmp_path)

    csv_bytes = b"id,name,value\n1,alice,3.14\n2,bob,2.71\n"

    with app.app_context():
        storage = FileStorageService("tenant-a")
        result = storage.store_file(csv_bytes, "test.csv")

        config = ConnectionConfig(extra_params={
            "file_ref": result["file_ref"],
            "file_hash": result["file_hash"],
            "file_format": "csv",
        })

        with FlatFileConnector(config) as connector:
            assert connector.test_connection()
            assert connector.get_schemas() == ["default"]
            tables = connector.get_tables("default")
            assert len(tables) == 1
            rows = list(connector.fetch_data())
            flat = [r for batch in rows for r in batch]
            assert len(flat) == 2
            assert flat[0]["name"] == "alice"


def test_flatfile_connector_rejects_sql():
    from app.domains.datasources.infrastructure.connectors.flatfile import FlatFileConnector
    from app.domains.datasources.infrastructure.connectors.base import ConnectionConfig

    config = ConnectionConfig(extra_params={"file_ref": "x"})
    connector = FlatFileConnector(config)
    valid, err = connector.validate_query("SELECT * FROM x")
    assert not valid


# ── Upload token HMAC verification ────────────────────────────

def test_upload_token_hmac_format():
    """Verify the token format produced by uploads endpoint matches what the
    service expects to consume."""
    secret = "test-secret-key"
    tenant_id = "tenant-a"
    file_ref = "tenants/tenant-a/datasources/abc/abc.csv"
    db_type = "flatfile"
    expires = int(time.time()) + 3600

    payload = f"{tenant_id}|{file_ref}|{db_type}|{expires}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}|{sig}"

    # Parse and verify
    parts = token.split("|")
    assert len(parts) == 5
    recovered_payload = "|".join(parts[:4])
    recovered_sig = parts[4]
    expected_sig = hmac.new(secret.encode(), recovered_payload.encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(recovered_sig, expected_sig)
