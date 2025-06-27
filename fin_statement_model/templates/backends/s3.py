from __future__ import annotations

"""S3-backed template storage backend.

This backend stores each template bundle as a JSON object in an S3 bucket.  It
is **experimental** and intended primarily for CI / PoC usage (see PRD).

Design decisions:
* One object per template – key format ``<prefix>/<template_id>.json`` where
  *prefix* defaults to ``"templates"``.
* A small object listing is sufficient – performance is not critical at the
  template count expected (<10k).
* Uses the high-level *boto3* resource API so that the implementation remains
  concise and easily mocked with *moto*.

Dependencies:
* ``boto3`` is required at runtime – the class safely imports it lazily to
  avoid hard dependency for users that do not use this backend.
"""

from typing import List, override
import json
import logging
import threading
import importlib

from .base import StorageBackend
from fin_statement_model.templates.models import TemplateBundle

logger = logging.getLogger(__name__)

__all__: list[str] = ["S3StorageBackend"]


class S3StorageBackend(StorageBackend):
    """Store template bundles in an S3 bucket."""

    def __init__(self, bucket: str, *, prefix: str = "templates") -> None:
        try:
            boto3 = importlib.import_module("boto3")  # noqa: WPS433 – optional dependency
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("boto3 is required to use S3StorageBackend.") from exc

        self._bucket_name = bucket
        self._prefix = prefix.rstrip("/")

        # Lazily create resource – moto patches this seamlessly in tests
        self._s3 = boto3.resource("s3")
        self._bucket = self._s3.Bucket(bucket)

        # Thread-safety
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _obj_key(self, template_id: str) -> str:
        return f"{self._prefix}/{template_id}.json"

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------
    @override
    def list(self) -> List[str]:  # noqa: D401 – concise name preferred
        with self._lock:
            return sorted(
                obj.key[len(self._prefix) + 1 : -5]  # strip prefix/ and .json
                for obj in self._bucket.objects.filter(Prefix=f"{self._prefix}/")
                if obj.key.endswith(".json")
            )

    @override
    def save(self, bundle: TemplateBundle) -> str:  # noqa: D401
        template_id = f"{bundle.meta.name}_{bundle.meta.version}"
        key = self._obj_key(template_id)
        with self._lock:
            # Check existence
            objs = list(self._bucket.objects.filter(Prefix=key))
            if any(o.key == key for o in objs):
                raise ValueError(f"Template '{template_id}' already exists in bucket {self._bucket_name}.")
            self._bucket.put_object(Key=key, Body=json.dumps(bundle.model_dump(mode="json")))
        logger.info("Saved template '%s' to s3://%s/%s", template_id, self._bucket_name, key)
        return template_id

    @override
    def load(self, template_id: str) -> TemplateBundle:
        key = self._obj_key(template_id)
        try:
            obj = self._bucket.Object(key).get()
        except Exception as exc:  # pragma: no cover – boto3 raises many types
            raise KeyError(f"Template '{template_id}' not found in bucket {self._bucket_name}.") from exc
        data = json.loads(obj["Body"].read())
        return TemplateBundle.model_validate(data)

    @override
    def delete(self, template_id: str) -> None:  # noqa: D401
        key = self._obj_key(template_id)
        with self._lock:
            self._bucket.objects.filter(Prefix=key).delete()