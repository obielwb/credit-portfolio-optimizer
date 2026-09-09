import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.utils import minio as minio_utils


def _minio_reachable() -> bool:
    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    host = endpoint.rsplit(":", 1)[0]
    if host in {"minio", "localhost", "127.0.0.1"}:
        return os.getenv("RUN_MINIO_INTEGRATION", "").lower() in {"1", "true", "yes"}
    return False


@pytest.mark.skipif(not _minio_reachable(), reason="MinIO local not habilitado (RUN_MINIO_INTEGRATION=1)")
def test_upload_csv_to_local_minio(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    monkeypatch.setenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
    monkeypatch.setenv("MINIO_SECRET_KEY", os.getenv("MINIO_SECRET_KEY", "minioadmin"))
    monkeypatch.setenv("MINIO_BUCKET", os.getenv("MINIO_BUCKET", "optimizer"))
    monkeypatch.setenv("MINIO_SECURE", "false")
    monkeypatch.setenv("MINIO_ROOT_PREFIX", "ingestion")
    monkeypatch.setenv("MINIO_PUBLIC_BASE_URL", "http://localhost:9000")

    contents = b"token,default_probability,payment_capacity,contract_propensity,filter_flag\n"
    contents += b"t1,0.1,1000,0.5,0\n"

    ref = minio_utils.upload_csv_to_minio(contents, "integration.csv")

    assert ref.startswith("http://localhost:9000/optimizer/ingestion/")
    assert ref.endswith("integration.csv")


def test_upload_returns_minio_uri_without_public_base(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio123")
    monkeypatch.setenv("MINIO_BUCKET", "uploads")
    monkeypatch.setenv("MINIO_SECURE", "false")
    monkeypatch.setenv("MINIO_ROOT_PREFIX", "csvs")
    monkeypatch.delenv("MINIO_PUBLIC_BASE_URL", raising=False)

    class FakeMinioClient:
        def __init__(self, *args, **kwargs):
            pass

        def bucket_exists(self, bucket_name):
            return True

        def make_bucket(self, bucket_name):
            return None

        def put_object(self, bucket_name, object_name, data, length, content_type=None):
            return None

    import types

    fake_module = types.SimpleNamespace(Minio=FakeMinioClient)
    monkeypatch.setitem(sys.modules, "minio", fake_module)

    ref = minio_utils.upload_csv_to_minio(b"a,b\n1,2\n", "sample.csv")
    assert ref.startswith("minio://uploads/csvs/")
