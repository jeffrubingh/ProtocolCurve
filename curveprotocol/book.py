"""Book assembly, validation and traversal.

The builder is the only place adjacency is computed, and the only place that
decides whether a dangling reference is fatal. In strict mode (the default)
every reference must resolve and every flow must move something; the lenient
mode synthesises the missing tranche so a partial journal can still be read.

The book is a DAG: a flow may credit a reserve that a later flow debits, but a
cycle would make the epoch ordering ambiguous, so cycles are rejected.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from curveprotocol.model import CurveBook, Flow, Reserve


class BookError(ValueError):
    """Raised when a book cannot be assembled."""


def build_book(
    reserves: Iterable[Reserve],
    flows: Iterable[Flow],
    *,
    strict: bool = True,
) -> CurveBook:
    """Assemble and validate a :class:`CurveBook`."""
    by_id: Dict[str, Reserve] = {}
    for reserve in reserves:
        reserve = reserve.normalised()
        if reserve.id in by_id:
            raise BookError(f"duplicate reserve id: {reserve.id}")
        by_id[reserve.id] = reserve

    flows_by_id: Dict[str, Flow] = {}
    producers: Dict[str, List[str]] = {}
    consumers: Dict[str, List[str]] = {}

    for flow in flows:
        flow = flow.normalised()
        if flow.id in flows_by_id:
            raise BookError(f"duplicate flow id: {flow.id}")
        if strict and not flow.outputs:
            raise BookError(f"flow {flow.id} credits nothing")
        flows_by_id[flow.id] = flow

        for rid in flow.inputs:
            if rid not in by_id:
                if strict:
                    raise BookError(f"flow {flow.id} debits unknown reserve {rid}")
                by_id[rid] = Reserve(id=rid).normalised()
            consumers.setdefault(rid, []).append(flow.id)
        for rid in flow.outputs:
            if rid not in by_id:
                if strict:
                    raise BookError(f"flow {flow.id} credits unknown reserve {rid}")
                by_id[rid] = Reserve(id=rid).normalised()
            producers.setdefault(rid, []).append(flow.id)

    book = CurveBook(
        reserves=by_id,
        flows=flows_by_id,
        producers={k: tuple(sorted(v)) for k, v in producers.items()},
        consumers={k: tuple(sorted(v)) for k, v in consumers.items()},
    )
    _reject_cycles(book)
    return book


def _reject_cycles(book: CurveBook) -> None:
    """Depth-first cycle check over reserve adjacency."""
    state: Dict[str, int] = {}
    for start in book.reserve_ids:
        if state.get(start):
            continue
        stack: List[Tuple[str, Iterable[str]]] = [(start, iter(book.sinks(start)))]
        state[start] = 1
        while stack:
            node, children = stack[-1]
            advanced = False
            for child in children:
                if state.get(child) == 1:
                    raise BookError(f"cycle through reserve {child}")
                if not state.get(child):
                    state[child] = 1
                    stack.append((child, iter(book.sinks(child))))
                    advanced = True
                    break
            if not advanced:
                state[node] = 2
                stack.pop()


def find_origins(book: CurveBook) -> Tuple[str, ...]:
    """Reserves nothing debits.

    A flow with no inputs starts a branch, so its output stays an origin even
    though a flow does credit it.
    """
    return tuple(
        r
        for r in book.reserve_ids
        if not book.producers.get(r)
        or all(not book.flows[f].inputs for f in book.producers.get(r, ()))
    )


def find_terminals(book: CurveBook) -> Tuple[str, ...]:
    """Reserves that nothing debits — where the curve ends up."""
    return tuple(r for r in book.reserve_ids if not book.consumers.get(r))


def ancestry(book: CurveBook, reserve_id: str) -> Tuple[str, ...]:
    """Ordered ancestry of *reserve_id*, ancestors before descendants."""
    if reserve_id not in book.reserves:
        raise BookError(f"unknown reserve: {reserve_id}")
    seen: Set[str] = set()
    order: List[str] = []

    def walk(node: str) -> None:
        for parent in book.sources(node):
            if parent in seen:
                continue
            seen.add(parent)
            walk(parent)
            order.append(parent)

    walk(reserve_id)
    return tuple(order)


def reachable(book: CurveBook, reserve_id: str) -> Tuple[str, ...]:
    """Everything downstream of *reserve_id*."""
    if reserve_id not in book.reserves:
        raise BookError(f"unknown reserve: {reserve_id}")
    seen: Set[str] = set()
    order: List[str] = []
    stack = [reserve_id]
    while stack:
        node = stack.pop()
        for child in book.sinks(node):
            if child in seen:
                continue
            seen.add(child)
            order.append(child)
            stack.append(child)
    return tuple(sorted(order))


def op_histogram(book: CurveBook) -> Mapping[str, int]:
    counts: Dict[str, int] = {}
    for fid in book.flow_ids:
        op = book.flows[fid].op
        counts[op] = counts.get(op, 0) + 1
    return counts


def band_histogram(book: CurveBook) -> Mapping[str, int]:
    counts: Dict[str, int] = {}
    for rid in book.reserve_ids:
        band = book.reserves[rid].band
        counts[band] = counts.get(band, 0) + 1
    return counts
