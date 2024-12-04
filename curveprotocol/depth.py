"""Liquidity depth scoring.

Depth is not raw balance: a tranche on the edge counts for less than a tranche
in the core, because the edge is the first thing a draw eats. The score is the
weighted depth over the raw balance, so a book that is entirely edge sits near
zero and a book that is entirely core sits at one.

The floor is deliberately absolute (micro-USDT) rather than relative: a tranche
below it is thin no matter how large the rest of the book is.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from curveprotocol import curve
from curveprotocol.model import BANDS, MICRO, CurveBook, DepthReport

#: Tranches below this balance are reported as thin.
DEPTH_FLOOR: int = 250 * MICRO

#: Band weights applied when a reserve carries no explicit weight.
DEFAULT_BAND_WEIGHTS: Dict[str, float] = {
    "seed": 1.0,
    "core": 1.0,
    "buffer": 0.8,
    "edge": 0.45,
    "sink": 0.2,
}


def compute_depth(book: CurveBook) -> DepthReport:
    """Score the book. Deterministic and side-effect free."""
    thin: List[str] = []
    dry: List[str] = []
    band_balances: Dict[str, int] = {band: 0 for band in BANDS}

    raw_total = 0
    weighted = 0
    funded = 0

    for rid in book.reserve_ids:
        reserve = book.reserves[rid]
        weight = reserve.weight if reserve.weight != 1.0 else DEFAULT_BAND_WEIGHTS.get(
            reserve.band, 1.0
        )
        raw_total += reserve.balance
        weighted += curve.depth_of([reserve.balance], [weight])
        band_balances[reserve.band] = band_balances.get(reserve.band, 0) + reserve.balance
        if reserve.is_funded:
            funded += 1
            if reserve.balance < DEPTH_FLOOR:
                thin.append(rid)
        elif not book.producers.get(rid):
            dry.append(rid)

    score = (weighted / (raw_total * MICRO)) if raw_total else 0.0
    return DepthReport(
        total_reserves=len(book.reserve_ids),
        funded_reserves=funded,
        weighted_depth=weighted,
        band_balances=band_balances,
        thin_ids=tuple(sorted(thin)),
        dry_ids=tuple(sorted(dry)),
        depth_score=max(0.0, min(1.0, score)),
    )


def grade(score: float) -> str:
    """Letter grade for a depth score, used by the text renderer."""
    if score >= 0.85:
        return "A"
    if score >= 0.7:
        return "B"
    if score >= 0.55:
        return "C"
    if score >= 0.35:
        return "D"
    return "E"


def shortfalls(report: DepthReport, target: int) -> Tuple[Tuple[str, int], ...]:
    """Bands below *target* micro-USDT, largest shortfall first."""
    rows = [(band, target - bal) for band, bal in report.band_balances.items() if bal < target]
    return tuple(sorted(rows, key=lambda row: (-row[1], row[0])))
