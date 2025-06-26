"""Compute and display correct checksum for built-in template.

Utility script to recompute the SHA-256 checksum for the
``fin_statement_model.templates.builtin.data.lbo.standard_v1.json``
bundle and compare it with the checksum stored inside the file.

Run this script manually when the JSON bundle changes to update
its embedded checksum before committing changes.
"""

import hashlib
import json
import logging
from pathlib import Path

src = Path("fin_statement_model/templates/builtin/data/lbo.standard_v1.json")
bundle = json.loads(src.read_text())
good = hashlib.sha256(json.dumps(bundle["graph_dict"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()

logger = logging.getLogger(__name__)


def main() -> None:
    """Print stored and computed checksum values."""
    logger.info("stored : %s", bundle["checksum"])
    logger.info("correct: %s", good)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
