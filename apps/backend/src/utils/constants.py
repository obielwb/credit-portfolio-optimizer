"""Global service, health-check, and ingestion-format constants."""

from __future__ import annotations

SERVICE_NAME = "backend"
SERVICE_VERSION = "0.1.0"

HEALTH_STATUS_OK = "ok"
HEALTH_STATUS_UNKNOWN = "unknown"
HEALTH_STATUS_ERROR = "error"
HEALTH_PROCESS_STATUS_ALIVE = "alive"
HEALTH_UPTIME_PLACEHOLDER = "placeholder"

ALLOWED_INGESTION_FILE_FORMATS = ("csv", "parquet", "pq")
