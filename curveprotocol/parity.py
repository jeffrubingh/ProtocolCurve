"""Canonical book text and the cross-language fingerprint.

The ports cannot share the JSON loader without dragging a parser into every
language, so they share a flat line format instead::

    R|id|band|balance
    F|id|op|inputs|outputs

``inputs`` and ``outputs`` are comma separated and may be empty. The
fingerprint is FNV-1a 64 over the reserve lines and then the flow lines, each
sorted and newline terminated, so every implementation produces the same value
for the same book.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from curveprotocol.curve import fnv1a64
from curveprotocol.model import BANDS, MICRO, Flow, Reserve

#: Weight in micro-units per band, mirroring :mod:`curveprotocol.depth`.
BAND_WEIGHT_MICRO: Dict[str, int] = {
    "seed": MICRO,
    "core": MICRO,
    "buffer": 800_000,
    "edge": 450_000,
    "sink": 200_000,
}

#: Tranches below this balance are thin.
FLOOR: int = 250 * MICRO


class ParityError(ValueError):
    """Raised when a canonical book is malformed."""


def parse(text: str) -> Tuple[List[Reserve], List[Flow]]:
    reserves: List[Reserve] = []
    flows: List[Flow] = []
    seen_r: set = set()
    seen_f: set = set()
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if parts[0] == "R":
            if len(parts) != 4:
                raise ParityError(f"line {lineno}: reserve needs 4 fields")
            rid, band, balance = parts[1], parts[2], parts[3]
            if rid in seen_r:
                raise ParityError(f"line {lineno}: duplicate reserve {rid}")
            seen_r.add(rid)
            reserves.append(
                Reserve(id=rid, band=band if band in BANDS else "core", balance=int(balance))
            )
        elif parts[0] == "F":
            if len(parts) != 5:
                raise ParityError(f"line {lineno}: flow needs 5 fields")
            fid = parts[1]
            if fid in seen_f:
                raise ParityError(f"line {lineno}: duplicate flow {fid}")
            seen_f.add(fid)
            ins = tuple(x for x in parts[3].split(",") if x)
            outs = tuple(x for x in parts[4].split(",") if x)
            if not outs:
                raise ParityError(f"line {lineno}: flow {fid} credits nothing")
            flows.append(Flow(id=fid, op=parts[2] or "derive", inputs=ins, outputs=outs))
        else:
            raise ParityError(f"line {lineno}: unknown record {parts[0]}")
    known = {r.id for r in reserves}
    for flow in flows:
        for ref in flow.inputs + flow.outputs:
            if ref not in known:
                raise ParityError(f"flow {flow.id}: unknown reserve {ref}")
    return reserves, flows


def weighted_depth(reserves: List[Reserve]) -> int:
    total = 0
    for reserve in reserves:
        weight = BAND_WEIGHT_MICRO.get(reserve.band, MICRO)
        total += reserve.balance * weight // MICRO
    return total


def origins(reserves: List[Reserve], flows: List[Flow]) -> List[str]:
    debited = {ref for flow in flows for ref in flow.outputs if flow.inputs}
    return sorted(r.id for r in reserves if r.id not in debited)


def fingerprint(reserves: List[Reserve], flows: List[Flow]) -> str:
    lines = [f"R|{r.id}|{r.band}|{r.balance}" for r in sorted(reserves, key=lambda r: r.id)]
    lines += [
        f"F|{f.id}|{f.op}|{','.join(sorted(f.inputs))}|{','.join(sorted(f.outputs))}"
        for f in sorted(flows, key=lambda f: f.id)
    ]
    return format(fnv1a64(("\n".join(lines) + "\n").encode()), "016x")


def load(path: Path) -> Tuple[List[Reserve], List[Flow]]:
    return parse(Path(path).read_text(encoding="utf-8"))
