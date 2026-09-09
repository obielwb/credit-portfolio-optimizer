import os
import sys
from types import SimpleNamespace

import pytest

# Ensure project importable
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

import src.utils.minio as minio_utils


def test_upload_csv_to_minio_raises_when_not_configured(monkeypatch):
    for env_name in (
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "MINIO_PUBLIC_BASE_URL",
        "MINIO_SECURE",
        "MINIO_ROOT_PREFIX",
    ):
        monkeypatch.delenv(env_name, raising=False)

    with pytest.raises(
        RuntimeError, match="Missing required MinIO environment variables"
    ):
        minio_utils.upload_csv_to_minio(b"a,b\n1,2\n", "sample.csv")


def test_upload_csv_to_minio_uses_minio_client_when_configured(monkeypatch):
    calls = SimpleNamespace(bucket_exists=None, make_bucket=None, put_object=None)

    class FakeMinioClient:
        def __init__(self, endpoint, access_key=None, secret_key=None, secure=False):
            self.endpoint = endpoint
            self.access_key = access_key
            self.secret_key = secret_key
            self.secure = secure

        def bucket_exists(self, bucket_name):
            calls.bucket_exists = bucket_name
            return False

        def make_bucket(self, bucket_name):
            calls.make_bucket = bucket_name

        def put_object(self, bucket_name, object_name, data, length, content_type=None):
            calls.put_object = {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "length": length,
                "content_type": content_type,
                "payload": data.read(),
            }

    fake_module = SimpleNamespace(Minio=FakeMinioClient)
    monkeypatch.setitem(sys.modules, "minio", fake_module)
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio123")
    monkeypatch.setenv("MINIO_BUCKET", "uploads")
    monkeypatch.setenv("MINIO_PUBLIC_BASE_URL", "http://minio.local")
    monkeypatch.setenv("MINIO_ROOT_PREFIX", "csvs")

    ref = minio_utils.upload_csv_to_minio(b"a,b\n1,2\n", "sample.csv")

    assert ref.startswith("http://minio.local/uploads/csvs/")
    assert calls.bucket_exists == "uploads"
    assert calls.make_bucket == "uploads"
    assert calls.put_object["bucket_name"] == "uploads"
    assert calls.put_object["content_type"] == "text/csv"
    assert calls.put_object["payload"] == b"a,b\n1,2\n"
