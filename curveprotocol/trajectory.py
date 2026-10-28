"""Trajectory assembly and rendering.

A trajectory is the report a reviewer reads: the digest of the book, the
fingerprint of the projected curve, the origins and terminals, the depth
report, and the resolved path for every terminal. Both renderers are pure and
deterministic, so the output can be committed as a golden file and diffed
between runs.
"""

from __future__ import annotations

import json
from typing import Dict, List, Tuple

from curveprotocol import curve
from curveprotocol.book import ancestry, band_histogram, find_origins, find_terminals, op_histogram
from curveprotocol.depth import compute_depth
from curveprotocol.model import MICRO, CurveBook, Trajectory, digest_book

#: Width the text renderer wraps at.
WRAP = 78


def build_trajectory(book: CurveBook, *, rate_bps: int = 0, epochs: int = 0) -> Trajectory:
    """Assemble the report for *book*."""
    origins = find_origins(book)
    terminals = find_terminals(book)
    depth = compute_depth(book)
    paths = {tid: ancestry(book, tid) for tid in terminals}
    seed_balance = sum(book.reserves[r].balance for r in origins)
    fingerprint = curve.fingerprint(
        [
            digest_book(book)[:16],
            rate_bps,
            epochs,
            seed_balance,
            len(book.reserve_ids),
            len(book.flow_ids),
        ]
    )
    return Trajectory(
        book_digest=digest_book(book),
        curve_fingerprint=fingerprint,
        origins=origins,
        terminals=terminals,
        depth=depth,
        paths=paths,
        op_histogram=dict(op_histogram(book)),
        band_histogram=dict(band_histogram(book)),
    )


def _wrap(label: str, value: str) -> List[str]:
    head = f"{label:<16}: "
    width = max(16, WRAP - len(head))
    if len(value) <= width:
        return [head + value]
    lines = [head + value[:width]]
    rest = value[width:]
    while rest:
        lines.append(" " * len(head) + rest[:width])
        rest = rest[width:]
    return lines


def render_text(trajectory: Trajectory, book: CurveBook) -> str:
    """Fixed-width rendering, no colour, no timestamps."""
    out: List[str] = []
    out.append("TRAJECTORY")
    out.extend(_wrap("book digest", trajectory.book_digest))
    out.extend(_wrap("curve print", trajectory.curve_fingerprint))
    out.append("")
    out.extend(_wrap("origins", ", ".join(trajectory.origins) or "-"))
    out.extend(_wrap("terminals", ", ".join(trajectory.terminals) or "-"))
    out.append("")
    depth = trajectory.depth
    out.append(f"depth            : {depth.depth_score:.4f}")
    out.append(f"weighted         : {depth.weighted_depth / MICRO:.6f} USDT")
    out.append(f"funded           : {depth.funded_reserves}/{depth.total_reserves}")
    for band in sorted(depth.band_balances):
        out.append(f"  {band:<8} {depth.band_balances[band] / MICRO:.6f}")
    if depth.thin_ids:
        out.extend(_wrap("thin", ", ".join(depth.thin_ids)))
    if depth.dry_ids:
        out.extend(_wrap("dry", ", ".join(depth.dry_ids)))
    out.append("")
    out.append("PATHS")
    for terminal in trajectory.terminals:
        chain = " -> ".join(trajectory.paths[terminal] + (terminal,))
        out.extend(_wrap(f"  {terminal}", chain))
    out.append("")
    out.append("OPS")
    for op in sorted(trajectory.op_histogram):
        out.append(f"  {op:<10} {trajectory.op_histogram[op]}")
    return "\n".join(out)


def render_json(trajectory: Trajectory) -> str:
    return json.dumps(trajectory.to_dict(), indent=2, sort_keys=True)


def render(trajectory: Trajectory, book: CurveBook, *, fmt: str = "text") -> str:
    if fmt == "json":
        return render_json(trajectory)
    if fmt != "text":
        raise ValueError(f"unknown format: {fmt}")
    return render_text(trajectory, book)
