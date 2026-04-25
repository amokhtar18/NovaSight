"""
NovaSight Data Sources — Flat File Connector
==============================================

Connector for CSV, TSV, JSON, and Parquet files stored in tenant-scoped
local filesystem storage.

Canonical location: ``app.domains.datasources.infrastructure.connectors.flatfile``
"""

import csv
import hashlib
import io
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.domains.datasources.infrastructure.connectors.base import (
    BaseConnector,
    ConnectionConfig,
    ConnectorException,
    ConnectionTestException,
)
from app.domains.datasources.domain.value_objects import ColumnInfo, TableInfo

logger = logging.getLogger(__name__)


class FlatFileConnector(BaseConnector):
    """
    Connector for flat-file data sources: CSV, TSV, JSON, Parquet.

    The file is stored in local filesystem storage keyed by ``file_ref``
    in ``extra_params``. The connector downloads it to a temp location on
    connect() and verifies SHA-256 hash integrity.

    Schema model:
        - Schema: "default" (single)
        - Table: the original filename (without path), or ``extra_params["file_name"]``
    """

    connector_type = "flatfile"
    supported_auth_methods: List[str] = []
    supports_ssl: bool = False
    default_port: int = 0

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._temp_path: Optional[Path] = None
        self._file_format: Optional[str] = None
        self._columns: Optional[List[ColumnInfo]] = None

    # ── Lifecycle ─────────────────────────────────────────────────

    def connect(self) -> None:
        """Locate and verify the stored file."""
        file_ref = self.config.extra_params.get("file_ref")
        if not file_ref:
            raise ConnectorException("Missing 'file_ref' in extra_params")

        from flask import current_app
        from app.platform.infrastructure.file_storage import FileStorageService

        # Resolve tenant_id from file_ref prefix
        parts = file_ref.split("/")
        if len(parts) < 4 or parts[0] != "tenants":
            raise ConnectorException(f"Invalid file_ref format: {file_ref}")
        tenant_id = parts[1]

        storage = FileStorageService(tenant_id)

        # Verify hash if available
        expected_hash = self.config.extra_params.get("file_hash")
        if expected_hash and not storage.verify_hash(file_ref, expected_hash):
            raise ConnectorException("File integrity check failed: hash mismatch")

        abs_path = storage.get_file_path(file_ref)
        if abs_path is None:
            raise ConnectorException(f"File not found: {file_ref}")

        self._temp_path = abs_path
        self._file_format = (
            self.config.extra_params.get("file_format")
            or self.config.file_format
            or self._detect_format(abs_path)
        )
        self._is_connected = True
        logger.info(f"FlatFileConnector: connected to {file_ref} (format={self._file_format})")

    def disconnect(self) -> None:
        self._is_connected = False
        self._temp_path = None
        self._columns = None

    def test_connection(self) -> bool:
        """Verify the file exists and is readable."""
        try:
            if self._temp_path is None:
                self.connect()
            if self._temp_path is None or not self._temp_path.exists():
                return False
            # Try reading first row
            next(iter(self._read_raw(self._temp_path, self._file_format, batch_size=1, max_rows=1)), None)
            return True
        except Exception as e:
            raise ConnectionTestException(f"Flat file test failed: {e}")

    # ── Schema Introspection ───────────────────────────────────────

    def get_schemas(self) -> List[str]:
        return ["default"]

    def get_tables(self, schema: str) -> List[TableInfo]:
        file_name = self.config.extra_params.get("file_name") or (
            self._temp_path.name if self._temp_path else "file"
        )
        columns = self._get_or_infer_columns()
        return [
            TableInfo(
                name=file_name,
                schema="default",
                row_count=None,
                columns=columns,
            )
        ]

    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        columns = self._get_or_infer_columns()
        file_name = self.config.extra_params.get("file_name") or (
            self._temp_path.name if self._temp_path else "file"
        )
        return TableInfo(name=file_name, schema="default", columns=columns)

    # ── Data Access ────────────────────────────────────────────────

    def fetch_data(
        self,
        query: str = "",
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Stream data in batches. query is ignored in v1."""
        if not self._is_connected or self._temp_path is None:
            raise ConnectorException("Not connected")

        yield from self._read_raw(
            self._temp_path, self._file_format, batch_size=batch_size
        )

    def validate_query(self, query: str):
        """Flat files do not accept ad-hoc SQL in v1."""
        if query.strip():
            return False, "Ad-hoc SQL is not supported for flat-file sources in this version"
        return True, ""

    # ── Private Helpers ────────────────────────────────────────────

    def _detect_format(self, path: Path) -> str:
        ext = path.suffix.lower()
        return {
            ".csv": "csv",
            ".tsv": "tsv",
            ".txt": "csv",
            ".json": "json",
            ".parquet": "parquet",
        }.get(ext, "csv")

    def _get_or_infer_columns(self) -> List[ColumnInfo]:
        if self._columns is not None:
            return self._columns
        if self._temp_path is None:
            return []
        try:
            sample = list(
                self._read_raw(self._temp_path, self._file_format, batch_size=200, max_rows=200)
            )
            if sample:
                first_batch = sample[0]
                if first_batch:
                    self._columns = [
                        ColumnInfo(name=k, data_type=self._infer_type(first_batch, k), nullable=True)
                        for k in first_batch[0].keys()
                    ]
                    return self._columns
        except Exception as e:
            logger.warning(f"Column inference failed: {e}")
        return []

    def _read_raw(
        self,
        path: Path,
        fmt: str,
        batch_size: int = 10000,
        max_rows: Optional[int] = None,
    ) -> Iterator[List[Dict[str, Any]]]:
        if fmt == "json":
            yield from self._read_json(path, batch_size, max_rows)
        elif fmt == "parquet":
            yield from self._read_parquet(path, batch_size, max_rows)
        else:
            delimiter = "\t" if fmt == "tsv" else self.config.extra_params.get("delimiter", ",")
            has_header = self.config.extra_params.get("has_header", True)
            encoding = self.config.extra_params.get("encoding", "utf-8")
            yield from self._read_csv(path, delimiter, has_header, encoding, batch_size, max_rows)

    def _read_csv(
        self,
        path: Path,
        delimiter: str,
        has_header: bool,
        encoding: str,
        batch_size: int,
        max_rows: Optional[int],
    ) -> Iterator[List[Dict[str, Any]]]:
        with path.open("r", encoding=encoding, errors="replace", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter) if has_header else csv.reader(f, delimiter=delimiter)
            batch: List[Dict] = []
            total = 0

            if has_header:
                for row in reader:
                    batch.append(dict(row))
                    total += 1
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                    if max_rows and total >= max_rows:
                        break
            else:
                for row in reader:
                    d = {f"column_{i}": v for i, v in enumerate(row)}
                    batch.append(d)
                    total += 1
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                    if max_rows and total >= max_rows:
                        break

            if batch:
                yield batch

    def _read_json(
        self, path: Path, batch_size: int, max_rows: Optional[int]
    ) -> Iterator[List[Dict[str, Any]]]:
        content = path.read_bytes()
        data = json.loads(content)

        if isinstance(data, dict):
            for key in ("data", "records", "rows", "items", "results"):
                if key in data and isinstance(data[key], list):
                    data = data[key]
                    break
            else:
                data = [data]

        if not isinstance(data, list):
            raise ConnectorException("JSON file must contain an array of objects")

        batch: List[Dict] = []
        for i, record in enumerate(data):
            if not isinstance(record, dict):
                continue
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []
            if max_rows and i + 1 >= max_rows:
                break
        if batch:
            yield batch

    def _read_parquet(
        self, path: Path, batch_size: int, max_rows: Optional[int]
    ) -> Iterator[List[Dict[str, Any]]]:
        try:
            import pyarrow.parquet as pq
            import pyarrow as pa
        except ImportError:
            raise ConnectorException("pyarrow is required for Parquet support")

        pf = pq.ParquetFile(str(path))
        total = 0
        for batch in pf.iter_batches(batch_size=batch_size):
            rows = batch.to_pydict()
            keys = list(rows.keys())
            n = len(rows[keys[0]]) if keys else 0
            records = [
                {k: rows[k][i] for k in keys}
                for i in range(n)
            ]
            if max_rows:
                remaining = max_rows - total
                records = records[:remaining]
            yield records
            total += len(records)
            if max_rows and total >= max_rows:
                break

    def _infer_type(self, batch: List[Dict], key: str) -> str:
        values = [str(r.get(key, "")) for r in batch[:50] if r.get(key) is not None]
        int_count = float_count = 0
        for v in values:
            try:
                int(v)
                int_count += 1
                continue
            except ValueError:
                pass
            try:
                float(v)
                float_count += 1
            except ValueError:
                pass
        total = len(values)
        if not total:
            return "String"
        if int_count == total:
            return "Int64"
        if (int_count + float_count) == total:
            return "Float64"
        return "String"
