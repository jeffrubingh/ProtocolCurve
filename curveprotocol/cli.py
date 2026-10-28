"""Command line interface for CurveProtocol.

The CLI exposes the operator workflow as subcommands on ``argparse``:

* ``ingest``     — load a journal and echo the normalised book.
* ``origins``    — list origin and terminal tranches.
* ``depth``      — print the liquidity depth report.
* ``trajectory`` — build and render the trajectory report.
* ``trace``      — print the resolved ancestry of one tranche.
* ``curve``      — project the growth curve from a seed balance.
* ``verify``     — recompute the fingerprint and compare it to an expectation.
* ``parity``     — fingerprint a canonical book file.

Every command is read-only and emits deterministic output, so results can be
diffed across runs and committed as golden files. Exit codes: ``0`` success,
``2`` usage or unknown id, ``3`` journal error, ``4`` fingerprint mismatch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from curveprotocol import __version__, curve, parity
from curveprotocol.book import BookError, ancestry, build_book, find_origins, find_terminals
from curveprotocol.depth import compute_depth, grade, shortfalls
from curveprotocol.io import (
    InputError,
    load_book_document,
    load_records,
    parse_flows,
    parse_reserves,
    write_json,
    write_text,
)
from curveprotocol.model import MICRO, CurveBook
from curveprotocol.trajectory import build_trajectory, render

EXIT_USAGE = 2
EXIT_INPUT = 3
EXIT_MISMATCH = 4


def _usdt(text: str) -> int:
    """Parse a USDT amount into micro-USDT without going through float."""
    whole, _, frac = text.partition(".")
    frac = (frac + "000000")[:6]
    return int(whole or "0") * MICRO + int(frac)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="curveprotocol", description="Exponential Curve Protocol book engine."
    )
    parser.add_argument("--version", action="version", version=f"curveprotocol {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_input(p: argparse.ArgumentParser) -> None:
        p.add_argument("book", nargs="?", type=Path, help="combined book document")
        p.add_argument("--reserves", type=Path, help="reserve journal (JSON or JSONL)")
        p.add_argument("--flows", type=Path, help="flow journal (JSON or JSONL)")
        p.add_argument("--lenient", action="store_true", help="synthesise unknown tranches")

    p_ing = sub.add_parser("ingest", help="validate and echo a book")
    add_input(p_ing)
    p_ing.add_argument("--out", type=Path, help="write the normalised book here")

    p_org = sub.add_parser("origins", help="list origin and terminal tranches")
    add_input(p_org)

    p_dep = sub.add_parser("depth", help="compute liquidity depth")
    add_input(p_dep)
    p_dep.add_argument("--json", action="store_true", help="emit JSON")
    p_dep.add_argument("--target", default="1000", help="per-band target in USDT")

    p_traj = sub.add_parser("trajectory", help="build the trajectory report")
    add_input(p_traj)
    p_traj.add_argument("--format", choices=("text", "json"), default="text")
    p_traj.add_argument("--rate", type=int, default=0, help="compounding rate in bps")
    p_traj.add_argument("--epochs", type=int, default=0, help="curve epochs to project")
    p_traj.add_argument("--out", type=Path, help="write the report here")

    p_tr = sub.add_parser("trace", help="show ancestry of one tranche")
    add_input(p_tr)
    p_tr.add_argument("reserve_id", help="tranche to trace")

    p_cv = sub.add_parser("curve", help="project the growth curve")
    p_cv.add_argument("seed", help="seed balance in USDT")
    p_cv.add_argument("--rate", type=int, default=250, help="rate in bps per epoch")
    p_cv.add_argument("--ceiling", default="0", help="ceiling in USDT, 0 for none")
    p_cv.add_argument("--epochs", type=int, default=12)

    p_vf = sub.add_parser("verify", help="compare the fingerprint to an expectation")
    add_input(p_vf)
    p_vf.add_argument("--expect", required=True, help="expected fingerprint")

    p_par = sub.add_parser("parity", help="fingerprint a canonical book file")
    p_par.add_argument("book", type=Path, help="canonical book file")

    return parser


def _load(args: argparse.Namespace) -> CurveBook:
    strict = not getattr(args, "lenient", False)
    if args.book is not None:
        reserves, flows = load_book_document(args.book)
        return build_book(reserves, flows, strict=strict)
    if not args.reserves or not args.flows:
        raise InputError("provide a book document, or both --reserves and --flows")
    return build_book(
        parse_reserves(load_records(args.reserves)),
        parse_flows(load_records(args.flows)),
        strict=strict,
    )


def _cmd_ingest(args: argparse.Namespace) -> int:
    book = _load(args)
    payload = book.to_dict()
    if args.out:
        write_json(args.out, payload)
        print(f"wrote book: {len(book.reserves)} reserves, {len(book.flows)} flows -> {args.out}")
    else:
        import json

        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _cmd_origins(args: argparse.Namespace) -> int:
    book = _load(args)
    print("ORIGINS")
    for rid in find_origins(book):
        res = book.reserves[rid]
        print(f"  {rid}  [{res.band}]  {res.label}")
    print("TERMINALS")
    for rid in find_terminals(book):
        res = book.reserves[rid]
        print(f"  {rid}  [{res.band}]  {res.label}")
    return 0


def _cmd_depth(args: argparse.Namespace) -> int:
    book = _load(args)
    report = compute_depth(book)
    if args.json:
        import json

        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0
    print(f"depth score    : {report.depth_score:.4f} (grade {grade(report.depth_score)})")
    print(f"weighted       : {report.weighted_depth / MICRO:.6f} USDT")
    print(f"funded         : {report.funded_reserves}/{report.total_reserves}")
    for band in sorted(report.band_balances):
        print(f"  {band:<8} {report.band_balances[band] / MICRO:.6f}")
    for band, gap in shortfalls(report, _usdt(args.target)):
        print(f"short {band:<8} {gap / MICRO:.6f} USDT below target")
    if report.thin_ids:
        print(f"thin           : {', '.join(report.thin_ids)}")
    if report.dry_ids:
        print(f"dry            : {', '.join(report.dry_ids)}")
    return 0


def _cmd_trajectory(args: argparse.Namespace) -> int:
    book = _load(args)
    report = build_trajectory(book, rate_bps=args.rate, epochs=args.epochs)
    rendered = render(report, book, fmt=args.format)
    if args.out:
        write_text(args.out, rendered + "\n")
        print(f"wrote trajectory -> {args.out}")
    else:
        print(rendered)
    return 0


def _cmd_trace(args: argparse.Namespace) -> int:
    book = _load(args)
    if args.reserve_id not in book.reserves:
        print(f"unknown reserve: {args.reserve_id}", file=sys.stderr)
        return EXIT_USAGE
    print("  ->  ".join(ancestry(book, args.reserve_id) + (args.reserve_id,)))
    return 0


def _cmd_curve(args: argparse.Namespace) -> int:
    seed = _usdt(args.seed)
    ceiling = _usdt(args.ceiling)
    series = curve.project(seed, args.rate, ceiling, args.epochs)
    for epoch, value in enumerate(series):
        print(f"{epoch:>4}  {value / MICRO:.6f}")
    print(f"fingerprint {curve.fingerprint([seed, args.rate, ceiling, args.epochs])}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    book = _load(args)
    report = build_trajectory(book)
    if report.curve_fingerprint == args.expect:
        print(f"ok {report.curve_fingerprint}")
        return 0
    print(f"mismatch: expected {args.expect}, got {report.curve_fingerprint}", file=sys.stderr)
    return EXIT_MISMATCH


def _cmd_parity(args: argparse.Namespace) -> int:
    reserves, flows = parity.load(args.book)
    print(f"reserves {len(reserves)}")
    print(f"flows {len(flows)}")
    print(f"raw {sum(r.balance for r in reserves)}")
    print(f"depth {parity.weighted_depth(reserves)}")
    print(f"origins {','.join(parity.origins(reserves, flows))}")
    print(f"fingerprint {parity.fingerprint(reserves, flows)}")
    return 0


_DISPATCH = {
    "ingest": _cmd_ingest,
    "origins": _cmd_origins,
    "depth": _cmd_depth,
    "trajectory": _cmd_trajectory,
    "trace": _cmd_trace,
    "curve": _cmd_curve,
    "verify": _cmd_verify,
    "parity": _cmd_parity,
}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _DISPATCH.get(args.command)
    if handler is None:  # pragma: no cover - argparse enforces this
        raise SystemExit(EXIT_USAGE)
    try:
        return handler(args)
    except (BookError, InputError, parity.ParityError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    raise SystemExit(main())
