import json
import uuid
import importlib

import pytest

from fin_statement_model.core.graph import Graph
from fin_statement_model.templates.backends import S3StorageBackend
from fin_statement_model.templates.registry import TemplateRegistry


def test_s3_backend_roundtrip(monkeypatch):
    """Register and load a template via S3 backend using moto mock."""
    bucket_name = f"fsm-test-{uuid.uuid4()}"
    region = "us-east-1"

    try:
        boto3 = importlib.import_module("boto3")  # type: ignore
        mock_s3 = importlib.import_module("moto").mock_s3  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        pytest.skip("boto3 or moto not installed")

    with mock_s3():
        # Set up mock bucket
        s3 = boto3.resource("s3", region_name=region)
        s3.create_bucket(Bucket=bucket_name)

        backend = S3StorageBackend(bucket=bucket_name)
        TemplateRegistry.configure_backend(backend)

        # Build simple graph
        g = Graph(periods=["2024"])
        g.add_financial_statement_item("Revenue", {"2024": 100.0})

        template_id = TemplateRegistry.register_graph(g, name="s3.integration")

        # Ensure object exists in mock S3
        object_key = f"templates/{template_id}.json"
        obj = s3.Object(bucket_name, object_key)
        assert json.loads(obj.get()["Body"].read())  # object contains json

        # Load via registry
        bundle = TemplateRegistry.get(template_id)
        assert bundle.meta.name == "s3.integration"