import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

SCHEMA_EXPORTS = [
    "OptimizationJobSchema",
    "RunStatusSchema",
    "RunResultSchema",
    "ParametersSchema",
    "SuccessResponseSchema",
    "StatisticsDashboardSchema",
    "ComparisonRunsDataSchema",
    "RunComparisonSnapshotSchema",
]

SERVICE_MODULES = [
    "async_service",
    "comparison_service",
    "ingestion_service",
    "optimization_service",
    "parameters_service",
    "statistics_service",
]


def test_schema_public_exports_importable():
    schema = importlib.import_module("src.schema")

    for name in SCHEMA_EXPORTS:
        assert hasattr(schema, name), f"src.schema missing export: {name}"


def test_services_package_importable():
    services = importlib.import_module("src.services")

    assert services.__all__ == SERVICE_MODULES

    for module_name in SERVICE_MODULES:
        module = importlib.import_module(f"src.services.{module_name}")
        assert module is not None


def test_main_app_importable():
    main = importlib.import_module("src.main")

    assert main.app is not None
    assert main.create_app is not None
