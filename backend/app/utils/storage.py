"""
storage.py
Unified file storage abstraction for RxDetect.

Priority:
  1. Supabase Storage — used when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set
  2. Local disk       — always available as fallback

Key conventions
---------------
  storage_key format : "{bucket}/{filename}"
                        e.g. "prescriptions/abc123.jpg"  or  "reports/abc123.pdf"
  Buckets (auto-created if missing):
    PRESCRIPTION_BUCKET = "prescriptions"
    REPORTS_BUCKET      = "reports"

Usage
-----
    from app.utils.storage import storage, PRESCRIPTION_BUCKET, REPORTS_BUCKET

    # upload bytes
    key = storage.upload_bytes(data, f"{PRESCRIPTION_BUCKET}/{filename}", content_type)

    # upload from a local file path
    key = storage.upload_file(local_path, f"{PRESCRIPTION_BUCKET}/{filename}", content_type)

    # get a time-limited signed URL (returns None for local backend)
    url = storage.get_url(key, expires_in=3600)

    # delete
    storage.delete(key)

    # check which backend is active
    print(storage.name)   # "supabase" or "local"
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
import structlog

log = structlog.get_logger(__name__)

PRESCRIPTION_BUCKET = "prescriptions"
REPORTS_BUCKET      = "reports"

# ── Base class ───────────────────────────────────────────────────────────────

class StorageBackend:
    """Abstract storage backend interface."""

    def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload raw bytes. Returns the storage key."""
        raise NotImplementedError

    def upload_file(
        self, local_path: str, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload from a local file path. Returns the storage key."""
        with open(local_path, "rb") as fh:
            data = fh.read()
        return self.upload_bytes(data, key, content_type)

    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Return a (possibly signed) download URL, or None if not supported."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete an object. Returns True on success."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError


# ── Local disk ───────────────────────────────────────────────────────────────

class LocalStorage(StorageBackend):
    """
    Stores files under `<base_dir>/<key>`.

    For example, key="prescriptions/abc.jpg" →  uploads/prescriptions/abc.jpg
    """

    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        dest = self.base_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        log.info("storage.local.uploaded", key=key, size=len(data))
        return key

    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        return None  # local disk has no URL

    def delete(self, key: str) -> bool:
        dest = self.base_dir / key
        try:
            if dest.exists():
                dest.unlink()
                log.info("storage.local.deleted", key=key)
            return True
        except Exception as exc:
            log.warning("storage.local.delete_failed", key=key, error=str(exc))
            return False

    @property
    def name(self) -> str:
        return "local"


# ── Supabase Storage via REST ────────────────────────────────────────────────

class SupabaseStorage(StorageBackend):
    """
    Supabase Storage backend — uses the Supabase Storage REST API directly
    via `requests` (no extra Python package needed beyond what's in requirements).

    Supabase REST endpoints:
      Upload  : POST  {base}/storage/v1/object/{bucket}/{path}
      Signed  : POST  {base}/storage/v1/object/sign/{bucket}/{path}   body: {"expiresIn": N}
      Delete  : DELETE {base}/storage/v1/object/{bucket}              body: {"prefixes": [path]}

    Authentication: service role key in Authorization header.

    Bucket names must exist in Supabase Storage.  Create them once in the
    Supabase dashboard (Storage → New Bucket) or via the management API.
    Recommended settings:
      - "prescriptions" bucket: private (only backend can access)
      - "reports" bucket: private
    """

    def __init__(self, url: str, service_role_key: str):
        self._base = url.rstrip("/")
        self._key  = service_role_key
        self._auth = {"Authorization": f"Bearer {service_role_key}"}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _split_key(self, key: str) -> tuple[str, str]:
        """
        Split a storage key into (bucket, object_path).
        "prescriptions/abc.jpg" → ("prescriptions", "abc.jpg")
        "abc.jpg"               → ("prescriptions", "abc.jpg")   ← default bucket
        """
        if "/" in key:
            bucket, path = key.split("/", 1)
            return bucket, path
        return PRESCRIPTION_BUCKET, key

    def _obj_url(self, bucket: str, path: str) -> str:
        return f"{self._base}/storage/v1/object/{bucket}/{path}"

    # ── interface ─────────────────────────────────────────────────────────────

    def upload_bytes(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        bucket, path = self._split_key(key)
        url = self._obj_url(bucket, path)
        headers = {**self._auth, "Content-Type": content_type, "x-upsert": "true"}
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=60)
            resp.raise_for_status()
            log.info("storage.supabase.uploaded", key=key, bucket=bucket, size=len(data))
            return key
        except requests.HTTPError as exc:
            log.error(
                "storage.supabase.upload_http_error",
                key=key, status=exc.response.status_code,
                body=exc.response.text[:300],
            )
            raise
        except Exception as exc:
            log.error("storage.supabase.upload_failed", key=key, error=str(exc))
            raise

    def get_url(self, key: str, expires_in: int = 3600) -> str | None:
        bucket, path = self._split_key(key)
        sign_url = f"{self._base}/storage/v1/object/sign/{bucket}/{path}"
        try:
            resp = requests.post(
                sign_url,
                headers={**self._auth, "Content-Type": "application/json"},
                json={"expiresIn": expires_in},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            signed = payload.get("signedURL") or payload.get("signedUrl") or ""
            if signed and signed.startswith("/"):
                signed = self._base + signed
            return signed or None
        except Exception as exc:
            log.error("storage.supabase.signed_url_failed", key=key, error=str(exc))
            return None

    def delete(self, key: str) -> bool:
        bucket, path = self._split_key(key)
        url = f"{self._base}/storage/v1/object/{bucket}"
        try:
            resp = requests.delete(
                url,
                headers={**self._auth, "Content-Type": "application/json"},
                json={"prefixes": [path]},
                timeout=15,
            )
            resp.raise_for_status()
            log.info("storage.supabase.deleted", key=key)
            return True
        except Exception as exc:
            log.warning("storage.supabase.delete_failed", key=key, error=str(exc))
            return False

    @property
    def name(self) -> str:
        return "supabase"


# ── Factory ──────────────────────────────────────────────────────────────────

def _make_backend() -> StorageBackend:
    """
    Determine which storage backend to use based on environment variables.

    Supabase is used when BOTH of the following are non-empty:
      SUPABASE_URL              — e.g. https://xxxx.supabase.co
      SUPABASE_SERVICE_ROLE_KEY — service-role secret key from Supabase dashboard

    Otherwise local disk storage is used (base dir = settings.upload_dir).
    """
    try:
        from app.config import settings
        supabase_url = getattr(settings, "supabase_url", None)
        supabase_key = getattr(settings, "supabase_service_role_key", None)
        upload_dir   = getattr(settings, "upload_dir", "uploads")
    except Exception:
        # Config not yet initialised (e.g. during alembic env setup) — use local
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        upload_dir   = os.getenv("UPLOAD_DIR", "uploads")

    if supabase_url and supabase_key:
        log.info("storage.backend_selected", backend="supabase", url=supabase_url)
        return SupabaseStorage(url=supabase_url, service_role_key=supabase_key)

    log.info("storage.backend_selected", backend="local", dir=upload_dir)
    return LocalStorage(base_dir=upload_dir)


# Singleton — one instance shared across the process.
storage: StorageBackend = _make_backend()
