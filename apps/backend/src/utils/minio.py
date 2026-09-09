

from __future__ import annotations

import io
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


def is_minio_configured() -> bool:


    return all(
        os.getenv(env_name)
        for env_name in (
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "MINIO_BUCKET",
            "MINIO_SECURE",
            "MINIO_ROOT_PREFIX",
        )
    )


def upload_csv_to_minio(
    contents: bytes,
    filename: str,
    file_ref: str | None = None,
) -> str:






    if file_ref:
        return file_ref

    _require_minio_env()

    client = _build_client()
    bucket_name = _require_env("MINIO_BUCKET")
    object_name = _build_object_name(filename)

    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    data = io.BytesIO(contents)
    client.put_object(
        bucket_name,
        object_name,
        data,
        length=len(contents),
        content_type=_content_type_for_filename(filename),
    )

    public_base_url = os.getenv("MINIO_PUBLIC_BASE_URL")
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/{bucket_name}/{object_name}"

    return f"minio://{bucket_name}/{object_name}"


def _build_client():


    try:
        from minio import Minio
    except Exception as exc:
        raise RuntimeError(
            "The MinIO SDK is not installed. Add the 'minio' dependency."
        ) from exc

    endpoint = _require_env("MINIO_ENDPOINT")
    access_key = _require_env("MINIO_ACCESS_KEY")
    secret_key = _require_env("MINIO_SECRET_KEY")
    secure = _require_env("MINIO_SECURE").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
    )

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def _build_object_name(filename: str) -> str:


    base_name = Path(filename).name
    root_prefix = _require_env("MINIO_ROOT_PREFIX").strip("/")
    timestamp = datetime.now().strftime("%Y/%m/%d")
    return f"{root_prefix}/{timestamp}/{uuid4().hex}-{base_name}"


def _content_type_for_filename(filename: str) -> str:

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in {"parquet", "pq"}:
        return "application/vnd.apache.parquet"
    if ext == "csv":
        return "text/csv"
    return "application/octet-stream"


def _require_env(name: str) -> str:
    """Read a required environment variable or raise RuntimeError."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _require_minio_env() -> None:

    required = [
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "MINIO_SECURE",
        "MINIO_ROOT_PREFIX",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Missing required MinIO environment variables: {joined}")


def check_storage_health() -> str:


    from src.utils.constants import HEALTH_STATUS_ERROR, HEALTH_STATUS_OK, HEALTH_STATUS_UNKNOWN

    if not is_minio_configured():
        return HEALTH_STATUS_UNKNOWN

    try:
        client = _build_client()
        client.list_buckets()
        bucket_name = _require_env("MINIO_BUCKET")
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        return HEALTH_STATUS_OK
    except Exception:
        return HEALTH_STATUS_ERROR


def parse_storage_ref(path_or_url: str) -> tuple[str, str]:


    if path_or_url.startswith("minio://"):
        rest = path_or_url[len("minio://") :]
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            raise ValueError(f"Invalid MinIO reference: {path_or_url}")
        return bucket, key

    public_base_url = os.getenv("MINIO_PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url and path_or_url.startswith(f"{public_base_url}/"):
        rest = path_or_url[len(public_base_url) + 1 :]
        bucket, _, key = rest.partition("/")
        if not bucket or not key:
            raise ValueError(f"Invalid public reference: {path_or_url}")
        return bucket, key

    parsed = urlparse(path_or_url)
    if parsed.scheme in {"http", "https"} and parsed.path:
        parts = parsed.path.lstrip("/").split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]

    raise ValueError(f"Could not resolve file reference: {path_or_url}")


def get_presigned_download_url(path_or_url: str, *, expires_seconds: int = 3600) -> str:


    if path_or_url.startswith(("http://", "https://")):
        public_base = os.getenv("MINIO_PUBLIC_BASE_URL", "").rstrip("/")
        if public_base and path_or_url.startswith(public_base):
            bucket, object_name = parse_storage_ref(path_or_url)
        else:
            return path_or_url
    else:
        bucket, object_name = parse_storage_ref(path_or_url)

    _require_minio_env()
    client = _build_client()
    presigned = client.presigned_get_object(
        bucket,
        object_name,
        expires=timedelta(seconds=expires_seconds),
    )
    # Rewrite internal Docker hostname to the externally accessible public URL.
    # MINIO_ENDPOINT is the in-cluster address (e.g. "minio:9000"); the presigned
    # URL uses that host, which browsers cannot resolve outside Docker.
    public_base_url = os.getenv("MINIO_PUBLIC_BASE_URL", "").rstrip("/")
    if public_base_url:
        endpoint = os.getenv("MINIO_ENDPOINT", "")
        secure = os.getenv("MINIO_SECURE", "false").strip().lower() in ("1", "true", "yes", "y")
        scheme = "https" if secure else "http"
        internal_base = f"{scheme}://{endpoint}"
        if presigned.startswith(internal_base):
            presigned = public_base_url + presigned[len(internal_base):]
    return presigned


def get_object_bytes(path_or_url: str) -> tuple[bytes, str]:


    bucket, object_name = parse_storage_ref(path_or_url)
    _require_minio_env()
    client = _build_client()
    response = client.get_object(bucket, object_name)
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()
    filename = Path(object_name).name
    return data, _content_type_for_filename(filename)


__all__ = [
    "check_storage_health",
    "get_object_bytes",
    "get_presigned_download_url",
    "is_minio_configured",
    "parse_storage_ref",
    "upload_csv_to_minio",
]
