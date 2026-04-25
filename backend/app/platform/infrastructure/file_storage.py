"""
NovaSight Platform — File Storage Service
==========================================

Tenant-scoped local filesystem storage for uploaded data source files.
Files are stored under ``FILE_STORAGE_ROOT/tenants/{tenant_id}/datasources/{uuid}/``.

Canonical location: ``app.platform.infrastructure.file_storage``
"""

import hashlib
import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


class FileStorageService:
    """Local filesystem storage service with tenant isolation."""

    def __init__(self, tenant_id: str):
        self.tenant_id = str(tenant_id)
        self._root = None

    @property
    def root(self) -> Path:
        if self._root is None:
            self._root = Path(current_app.config["FILE_STORAGE_ROOT"])
        return self._root

    def _tenant_dir(self) -> Path:
        return self.root / "tenants" / self.tenant_id / "datasources"

    def store_file(self, file_bytes: bytes, original_filename: str) -> dict:
        """
        Store an uploaded file securely.

        Returns dict with:
            file_ref: storage key (relative path)
            file_hash: SHA-256 hex digest
            stored_path: absolute path (for internal use only)
        """
        file_id = str(uuid.uuid4())
        # Sanitize: only use the UUID as directory name, never user input
        dest_dir = self._tenant_dir() / file_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Use UUID-based filename to prevent path traversal
        ext = Path(original_filename).suffix.lower()
        safe_filename = f"{file_id}{ext}"
        dest_path = dest_dir / safe_filename

        # Write file
        dest_path.write_bytes(file_bytes)

        # Compute hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        file_ref = f"tenants/{self.tenant_id}/datasources/{file_id}/{safe_filename}"

        logger.info(
            f"Stored file for tenant {self.tenant_id}: "
            f"{original_filename} -> {file_ref} ({len(file_bytes)} bytes)"
        )

        return {
            "file_ref": file_ref,
            "file_hash": file_hash,
            "file_id": file_id,
            "stored_path": str(dest_path),
            "file_size": len(file_bytes),
        }

    def get_file_path(self, file_ref: str) -> Optional[Path]:
        """
        Resolve a file_ref to an absolute path, with tenant isolation check.

        Returns None if the file doesn't exist or the ref is outside the
        tenant's scope (path traversal protection).
        """
        # Normalize and validate
        resolved = (self.root / file_ref).resolve()
        tenant_base = self._tenant_dir().resolve()

        # Ensure the resolved path is within the tenant directory
        if not str(resolved).startswith(str(tenant_base)):
            logger.warning(
                f"Path traversal attempt blocked: {file_ref} "
                f"resolved to {resolved} outside {tenant_base}"
            )
            return None

        if not resolved.exists():
            return None

        return resolved

    def verify_hash(self, file_ref: str, expected_hash: str) -> bool:
        """Verify SHA-256 hash of a stored file."""
        file_path = self.get_file_path(file_ref)
        if file_path is None:
            return False

        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            logger.warning(
                f"Hash mismatch for {file_ref}: "
                f"expected={expected_hash}, actual={actual_hash}"
            )
            return False
        return True

    def delete_file(self, file_ref: str) -> bool:
        """Delete a stored file and its directory."""
        file_path = self.get_file_path(file_ref)
        if file_path is None:
            return False

        # Delete the parent UUID directory
        try:
            shutil.rmtree(file_path.parent)
            logger.info(f"Deleted file: {file_ref}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete {file_ref}: {e}")
            return False

    def get_tenant_usage_bytes(self) -> int:
        """Calculate total storage usage for the tenant."""
        tenant_dir = self._tenant_dir()
        if not tenant_dir.exists():
            return 0
        total = 0
        for f in tenant_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
