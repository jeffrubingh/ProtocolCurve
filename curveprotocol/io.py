"""Journal readers and writers.

The protocol records its journal as one JSON object per line (JSONL) or as a
combined document holding both arrays. Both forms are accepted so an operator
can pipe a live journal or hand over a single archived file.

Writers create missing parent directories so a report can be dropped straight
into a fresh dated folder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from curveprotocol.model import Flow, Reserve


class InputError(ValueError):
    """Raised when a journal cannot be parsed."""


def _read_text(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise InputError(f"journal not found: {path}") from None
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from None


def load_records(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON array or a JSONL stream into a list of mappings."""
    text = _read_text(path).strip()
    if not text:
        return []
    if text[0] == "[":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}: {exc}") from None
        if not isinstance(payload, list):
            raise InputError(f"{path}: expected a JSON array")
        return [dict(item) for item in payload if isinstance(item, Mapping)]
    records: List[Dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{lineno}: {exc}") from None
        if not isinstance(record, Mapping):
            raise InputError(f"{path}:{lineno}: expected an object")
        records.append(dict(record))
    return records


def parse_reserves(records: Sequence[Mapping[str, Any]]) -> List[Reserve]:
    reserves: List[Reserve] = []
    for index, raw in enumerate(records):
        try:
            reserves.append(Reserve.from_dict(raw))
        except (ValueError, TypeError) as exc:
            raise InputError(f"reserve #{index}: {exc}") from None
    return reserves


def parse_flows(records: Sequence[Mapping[str, Any]]) -> List[Flow]:
    flows: List[Flow] = []
    for index, raw in enumerate(records):
        try:
            flows.append(Flow.from_dict(raw))
        except (ValueError, TypeError) as exc:
            raise InputError(f"flow #{index}: {exc}") from None
    return flows


def load_book_document(path: Path) -> Tuple[List[Reserve], List[Flow]]:
    """Load a combined document holding ``reserves`` and ``flows``."""
    text = _read_text(path)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: {exc}") from None
    if not isinstance(payload, Mapping):
        raise InputError(f"{path}: expected a JSON object")
    return parse_reserves(payload.get("reserves") or []), parse_flows(
        payload.get("flows") or []
    )


def write_json(path: Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
