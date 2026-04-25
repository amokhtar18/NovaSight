"""
NovaSight Data Sources — File Validation Service
==================================================

Validates uploaded files for format correctness, security threats,
and content integrity before they are accepted as data sources.

Canonical location: ``app.domains.datasources.application.file_validation_service``
"""

import io
import logging
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

logger = logging.getLogger(__name__)

# ─── Magic bytes for format detection ─────────────────────────────

_MAGIC_SIGNATURES = {
    b"PK\x03\x04": "xlsx_or_zip",  # ZIP-based (xlsx, etc.)
    b"\x89PNG": "png",              # Not allowed
    b"\xff\xd8\xff": "jpeg",        # Not allowed
    b"PAR1": "parquet",
    b"SQLite format 3": "sqlite",
}


# ─── Allowed MIME → format mapping ─────────────────────────────────

EXTENSION_FORMAT_MAP = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".txt": "csv",       # treat plain text as CSV
    ".json": "json",
    ".parquet": "parquet",
    ".xlsx": "excel",
    ".xls": "excel",
    ".sqlite": "sqlite",
    ".db": "sqlite",
    ".sqlite3": "sqlite",
}

# Formats that belong to each db_type
DB_TYPE_FORMATS = {
    "flatfile": {"csv", "tsv", "json", "parquet"},
    "excel": {"excel"},
    "sqlite": {"sqlite"},
}


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class FileValidationService:
    """Validates uploaded data-source files."""

    def validate(
        self,
        file_bytes: bytes,
        original_filename: str,
        declared_db_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run all validation checks on the uploaded file.

        Returns metadata dict on success. Raises FileValidationError on failure.
        """
        results: Dict[str, Any] = {"original_filename": original_filename}

        # 1. Extension check
        ext = Path(original_filename).suffix.lower()
        allowed = current_app.config.get(
            "FILE_UPLOAD_ALLOWED_EXTENSIONS",
            {".csv", ".tsv", ".txt", ".json", ".parquet", ".xlsx", ".xls", ".sqlite", ".db", ".sqlite3"},
        )
        if ext not in allowed:
            raise FileValidationError(
                f"File extension '{ext}' is not allowed. "
                f"Accepted: {', '.join(sorted(allowed))}"
            )

        # 2. Size check
        max_bytes = current_app.config.get("FILE_UPLOAD_MAX_SIZE_BYTES", 200 * 1024 * 1024)
        if len(file_bytes) > max_bytes:
            max_mb = max_bytes / (1024 * 1024)
            raise FileValidationError(
                f"File size ({len(file_bytes) / (1024*1024):.1f} MB) "
                f"exceeds maximum allowed ({max_mb:.0f} MB)"
            )

        if len(file_bytes) == 0:
            raise FileValidationError("File is empty")

        # 3. Magic-byte / content sniffing
        detected_format = self._detect_format(file_bytes, ext)
        results["detected_format"] = detected_format

        # 4. Format-extension consistency
        expected_format = EXTENSION_FORMAT_MAP.get(ext)
        if expected_format and detected_format != expected_format:
            raise FileValidationError(
                f"File content does not match extension '{ext}'. "
                f"Expected format '{expected_format}', detected '{detected_format}'"
            )

        # 5. db_type consistency
        if declared_db_type:
            valid_formats = DB_TYPE_FORMATS.get(declared_db_type, set())
            if detected_format not in valid_formats:
                raise FileValidationError(
                    f"File format '{detected_format}' is not valid for "
                    f"db_type '{declared_db_type}'. "
                    f"Expected one of: {', '.join(sorted(valid_formats))}"
                )

        # 6. Excel-specific: reject macros (VBA)
        if detected_format == "excel" and ext == ".xlsx":
            self._check_xlsx_macros(file_bytes)

        # 7. ClamAV virus scan
        if current_app.config.get("CLAMAV_ENABLED", False):
            self._scan_with_clamav(file_bytes, original_filename)

        # 8. Format-specific content validation
        self._validate_content(file_bytes, detected_format, ext)

        results["format"] = detected_format
        results["size_bytes"] = len(file_bytes)
        results["extension"] = ext

        return results

    def _detect_format(self, file_bytes: bytes, ext: str) -> str:
        """Detect file format from magic bytes and extension."""
        # SQLite check (16 bytes header)
        if file_bytes[:16] == b"SQLite format 3\x00":
            return "sqlite"

        # Parquet check (magic at start)
        if file_bytes[:4] == b"PAR1":
            return "parquet"

        # ZIP-based check (xlsx)
        if file_bytes[:4] == b"PK\x03\x04":
            if ext in (".xlsx", ".xls"):
                return "excel"
            # Unknown ZIP
            raise FileValidationError(
                f"File appears to be a ZIP archive but has extension '{ext}'"
            )

        # XLS (old binary format)
        if file_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            if ext in (".xls", ".xlsx"):
                return "excel"
            raise FileValidationError(
                "File appears to be an OLE2 compound document"
            )

        # JSON check
        stripped = file_bytes.lstrip()
        if stripped and stripped[0:1] in (b"{", b"["):
            if ext in (".json",):
                return "json"

        # Default to CSV for text files
        if ext in (".csv", ".tsv", ".txt"):
            return EXTENSION_FORMAT_MAP.get(ext, "csv")

        # Fallback
        return EXTENSION_FORMAT_MAP.get(ext, "unknown")

    def _check_xlsx_macros(self, file_bytes: bytes) -> None:
        """Reject XLSX files containing VBA macros."""
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                names = zf.namelist()
                # VBA macros live in vbaProject.bin
                vba_indicators = [
                    n for n in names
                    if "vbaproject" in n.lower() or n.lower().endswith(".bin")
                ]
                if vba_indicators:
                    raise FileValidationError(
                        "Excel file contains VBA macros, which are not allowed "
                        "for security reasons. Please save as .xlsx without macros."
                    )
        except zipfile.BadZipFile:
            raise FileValidationError("File claims to be XLSX but is not a valid ZIP archive")

    def _scan_with_clamav(self, file_bytes: bytes, filename: str) -> None:
        """Scan file with ClamAV daemon."""
        try:
            import clamd
        except ImportError:
            logger.warning("pyclamd/clamd not installed; skipping virus scan")
            return

        host = current_app.config.get("CLAMAV_HOST", "localhost")
        port = current_app.config.get("CLAMAV_PORT", 3310)

        try:
            cd = clamd.ClamdNetworkSocket(host=host, port=port, timeout=30)
            cd.ping()
        except Exception as e:
            logger.error(f"ClamAV not reachable at {host}:{port}: {e}")
            # Fail open or closed based on policy — we fail closed
            raise FileValidationError(
                "Virus scanning service is unavailable. Upload rejected."
            )

        try:
            result = cd.instream(io.BytesIO(file_bytes))
            status, reason = result.get("stream", ("OK", ""))
            if status != "OK":
                logger.warning(f"ClamAV detected threat in {filename}: {reason}")
                raise FileValidationError(
                    f"File rejected: virus/malware detected ({reason})"
                )
        except FileValidationError:
            raise
        except Exception as e:
            logger.error(f"ClamAV scan error: {e}")
            raise FileValidationError("Virus scan failed. Upload rejected.")

    def _validate_content(self, file_bytes: bytes, detected_format: str, ext: str) -> None:
        """Format-specific content validation."""
        if detected_format == "csv" or detected_format == "tsv":
            self._validate_csv_content(file_bytes, detected_format)
        elif detected_format == "json":
            self._validate_json_content(file_bytes)
        elif detected_format == "sqlite":
            self._validate_sqlite_content(file_bytes)
        elif detected_format == "excel":
            self._validate_excel_content(file_bytes)
        elif detected_format == "parquet":
            self._validate_parquet_content(file_bytes)

    def _validate_csv_content(self, file_bytes: bytes, fmt: str) -> None:
        """Validate CSV/TSV can be parsed."""
        import csv
        try:
            # Try to detect encoding
            sample = file_bytes[:8192]
            try:
                text = sample.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    text = sample.decode("latin-1")
                except UnicodeDecodeError:
                    raise FileValidationError("Unable to detect file encoding")

            delimiter = "\t" if fmt == "tsv" else None
            reader = csv.reader(io.StringIO(text), delimiter=delimiter) if delimiter else csv.reader(io.StringIO(text))
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= 5:
                    break

            if len(rows) < 1:
                raise FileValidationError("CSV file appears to be empty")

        except csv.Error as e:
            raise FileValidationError(f"Invalid CSV format: {e}")

    def _validate_json_content(self, file_bytes: bytes) -> None:
        """Validate JSON structure."""
        import json
        try:
            data = json.loads(file_bytes)
            if not isinstance(data, (list, dict)):
                raise FileValidationError(
                    "JSON must contain an array or object at the top level"
                )
        except json.JSONDecodeError as e:
            raise FileValidationError(f"Invalid JSON: {e}")

    def _validate_sqlite_content(self, file_bytes: bytes) -> None:
        """Validate SQLite database is readable."""
        import sqlite3
        import tempfile
        import os

        # Write to temp file and open read-only
        fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
        try:
            os.write(fd, file_bytes)
            os.close(fd)

            conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = cursor.fetchall()
                if not tables:
                    raise FileValidationError("SQLite database contains no tables")
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            raise FileValidationError(f"Invalid SQLite database: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _validate_excel_content(self, file_bytes: bytes) -> None:
        """Validate Excel file has readable sheets."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
            if not wb.sheetnames:
                raise FileValidationError("Excel file contains no sheets")
            wb.close()
        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Invalid Excel file: {e}")

    def _validate_parquet_content(self, file_bytes: bytes) -> None:
        """Validate Parquet file is readable."""
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(io.BytesIO(file_bytes))
            if table.num_columns == 0:
                raise FileValidationError("Parquet file contains no columns")
        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Invalid Parquet file: {e}")
