"""Core value model for the Exponential Curve Protocol.

The protocol moves USDT between reserve tranches along a growth curve. The
model layer holds the immutable value objects that flow through the pipeline:
:class:`Reserve` (a tranche holding balance at one band), :class:`Flow` (a
directed capital movement), :class:`CurveBook` (the assembled book),
:class:`DepthReport` (liquidity depth metrics) and :class:`Trajectory` (the
final report bundle).

Balances are integer micro-USDT. Nothing here uses floats for money, so a
replay of the same journal always lands on the same book.

Every object is a frozen dataclass. Serialisation is deterministic: keys are
emitted in a fixed order and collections are sorted by identifier, which is a
load-bearing property for the digest and for golden files.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

#: Recognised bands, ordered from the quietest to the most exposed.
BANDS: Tuple[str, ...] = ("seed", "core", "buffer", "edge", "sink")

#: Recognised flow operations.
FLOW_OPS: Tuple[str, ...] = (
    "seed",
    "deposit",
    "reinvest",
    "harvest",
    "rebalance",
    "draw",
    "settle",
    "validate",
    "annotate",
    "derive",
)

#: Micro-units per USDT.
MICRO: int = 1_000_000


@dataclass(frozen=True)
class Reserve:
    """A single tranche in the book."""

    id: str
    band: str = "core"
    label: str = ""
    balance: int = 0
    epoch: int = 0
    weight: float = 1.0
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def normalised(self) -> "Reserve":
        """Return a copy with band, label, balance and weight coerced."""
        band = self.band if self.band in BANDS else "core"
        return Reserve(
            id=self.id,
            band=band,
            label=self.label or self.id,
            balance=max(0, int(self.balance)),
            epoch=max(0, int(self.epoch)),
            weight=_clamp(self.weight),
            attributes=dict(self.attributes),
        )

    @property
    def is_funded(self) -> bool:
        """True when the tranche carries balance."""
        return self.balance > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "band": self.band,
            "label": self.label,
            "balance": self.balance,
            "epoch": self.epoch,
            "weight": round(self.weight, 4),
            "attributes": _sorted_mapping(self.attributes),
        }

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "Reserve":
        if "id" not in raw:
            raise ValueError("reserve record is missing required field 'id'")
        weight = raw.get("weight")
        return Reserve(
            id=str(raw["id"]),
            band=str(raw.get("band", "core")),
            label=str(raw.get("label", "")),
            balance=int(raw.get("balance", 0) or 0),
            epoch=int(raw.get("epoch", 0) or 0),
            weight=(float(weight) if weight is not None else 1.0),
            attributes=dict(raw.get("attributes", {}) or {}),
        ).normalised()


@dataclass(frozen=True)
class Flow:
    """A directed capital movement.

    A flow fans in from one or more reserves and out to one or more reserves,
    so a harvest that feeds three tranches and a merge that folds two tranches
    into one need no special cases.
    """

    id: str
    op: str = "derive"
    inputs: Sequence[str] = field(default_factory=tuple)
    outputs: Sequence[str] = field(default_factory=tuple)
    agent: Optional[str] = None
    weight: Optional[float] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def normalised(self) -> "Flow":
        return Flow(
            id=self.id,
            op=self.op or "derive",
            inputs=tuple(dict.fromkeys(str(x) for x in self.inputs)),
            outputs=tuple(dict.fromkeys(str(x) for x in self.outputs)),
            agent=self.agent,
            weight=self.weight,
            attributes=dict(self.attributes),
        )

    @property
    def effective_weight(self) -> float:
        """Weight with the missing value folded to one and clamped."""
        if self.weight is None:
            return 1.0
        return _clamp(self.weight)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "op": self.op,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "agent": self.agent,
            "weight": self.weight,
            "attributes": _sorted_mapping(self.attributes),
        }

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "Flow":
        if "id" not in raw:
            raise ValueError("flow record is missing required field 'id'")
        weight = raw.get("weight")
        return Flow(
            id=str(raw["id"]),
            op=str(raw.get("op", "derive")),
            inputs=tuple(str(x) for x in (raw.get("inputs") or [])),
            outputs=tuple(str(x) for x in (raw.get("outputs") or [])),
            agent=_opt_str(raw.get("agent")),
            weight=(float(weight) if weight is not None else None),
            attributes=dict(raw.get("attributes", {}) or {}),
        ).normalised()


@dataclass(frozen=True)
class CurveBook:
    """An assembled book of reserves and flows."""

    reserves: Mapping[str, Reserve]
    flows: Mapping[str, Flow]
    producers: Mapping[str, Tuple[str, ...]]
    consumers: Mapping[str, Tuple[str, ...]]

    @property
    def reserve_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.reserves))

    @property
    def flow_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.flows))

    def sources(self, reserve_id: str) -> Tuple[str, ...]:
        """Reserves debited by every flow that credits *reserve_id*."""
        seen: List[str] = []
        for fid in self.producers.get(reserve_id, ()):
            for src in self.flows[fid].inputs:
                if src not in seen:
                    seen.append(src)
        return tuple(sorted(seen))

    def sinks(self, reserve_id: str) -> Tuple[str, ...]:
        """Reserves credited by every flow that debits *reserve_id*."""
        seen: List[str] = []
        for fid in self.consumers.get(reserve_id, ()):
            for dst in self.flows[fid].outputs:
                if dst not in seen:
                    seen.append(dst)
        return tuple(sorted(seen))

    @property
    def total_balance(self) -> int:
        return sum(self.reserves[r].balance for r in self.reserve_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reserves": [self.reserves[r].to_dict() for r in self.reserve_ids],
            "flows": [self.flows[f].to_dict() for f in self.flow_ids],
        }


@dataclass(frozen=True)
class DepthReport:
    """Liquidity depth metrics for a book."""

    total_reserves: int
    funded_reserves: int
    weighted_depth: int
    band_balances: Mapping[str, int]
    thin_ids: Tuple[str, ...]
    dry_ids: Tuple[str, ...]
    depth_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_reserves": self.total_reserves,
            "funded_reserves": self.funded_reserves,
            "weighted_depth": self.weighted_depth,
            "band_balances": {k: self.band_balances[k] for k in sorted(self.band_balances)},
            "thin_ids": list(self.thin_ids),
            "dry_ids": list(self.dry_ids),
            "depth_score": round(self.depth_score, 4),
        }


@dataclass(frozen=True)
class Trajectory:
    """The complete report bundle."""

    book_digest: str
    curve_fingerprint: str
    origins: Tuple[str, ...]
    terminals: Tuple[str, ...]
    depth: DepthReport
    paths: Mapping[str, Tuple[str, ...]]
    op_histogram: Mapping[str, int]
    band_histogram: Mapping[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "book_digest": self.book_digest,
            "curve_fingerprint": self.curve_fingerprint,
            "origins": list(self.origins),
            "terminals": list(self.terminals),
            "depth": self.depth.to_dict(),
            "paths": {k: list(v) for k, v in sorted(self.paths.items())},
            "op_histogram": dict(sorted(self.op_histogram.items())),
            "band_histogram": dict(sorted(self.band_histogram.items())),
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _sorted_mapping(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: mapping[k] for k in sorted(mapping)}


def digest_book(book: CurveBook) -> str:
    """Return a stable SHA-256 digest of the book structure."""
    hasher = hashlib.sha256()
    for rid in book.reserve_ids:
        res = book.reserves[rid]
        hasher.update(f"R|{res.id}|{res.band}|{res.balance}\n".encode())
    for fid in book.flow_ids:
        fl = book.flows[fid]
        ins = ",".join(sorted(fl.inputs))
        outs = ",".join(sorted(fl.outputs))
        hasher.update(f"F|{fl.id}|{fl.op}|{ins}|{outs}\n".encode())
    return hasher.hexdigest()
