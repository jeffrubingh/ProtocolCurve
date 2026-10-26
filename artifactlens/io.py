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
    records: List[dict] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {lineno}: {exc}") from exc
    return records


def load_graph_document(path: Path) -> Tuple[List[Artifact], List[Transformation]]:
    """Load a combined graph document.

    A graph document is a single JSON object with ``artifacts`` and
    ``transformations`` arrays::

        {
          "artifacts": [ {...}, ... ],
          "transformations": [ {...}, ... ]
        }
    """
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, Mapping):
        raise ValueError("graph document must be a JSON object")
    arts = [Artifact.from_dict(r) for r in obj.get("artifacts", [])]
    trs = [Transformation.from_dict(r) for r in obj.get("transformations", [])]
    return arts, trs


def parse_artifacts(records: Iterable[Mapping[str, Any]]) -> List[Artifact]:
    return [Artifact.from_dict(r) for r in records]


def parse_transformations(
    records: Iterable[Mapping[str, Any]],
) -> List[Transformation]:
    return [Transformation.from_dict(r) for r in records]


def write_json(path: Path, payload: Any) -> None:
    """Write *payload* as deterministic pretty JSON."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path, text: str) -> None:
    """Write text, creating the parent directory first."""
    from pathlib import Path

    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
