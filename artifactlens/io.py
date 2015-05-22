"""Input/output helpers for ArtifactLens.

ArtifactLens ingests two record types from disk: **artifacts** and
**transformations**. Both can be supplied as a single JSON object/array or as
JSON Lines (one record per line). The loader auto-detects the format so the
same file works with either convention.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Tuple

from artifactlens.model import Artifact, Transformation


def load_records(path: Path) -> List[dict]:
    """Load a list of record dictionaries from a JSON or JSONL file.

    Detection rules:

    * If the file parses as a JSON array, its elements are the records.
    * If it parses as a JSON object with an ``artifacts`` or ``transformations``
      key, that container is handled by :func:`load_graph_document` instead;
      here a bare object is treated as a single record.
    * Otherwise the file is parsed as JSON Lines.
    """
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        data = json.loads(text)
        return list(data)
    if stripped.startswith("{"):
        # Could be a single record or a whole document; try full parse first.
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return _parse_jsonl(text)
        if isinstance(obj, dict):
            return [obj]
        return list(obj)
    return _parse_jsonl(text)


def _parse_jsonl(text: str) -> List[dict]:
