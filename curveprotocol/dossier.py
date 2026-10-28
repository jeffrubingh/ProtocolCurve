"""Dossier assembly and rendering for CurveProtocol.

A *dossier* is the human- and machine-readable report CurveProtocol produces
for a graph. :func:`build_dossier` computes the structured
:class:`~curveprotocol.model.Dossier`; :func:`render_dossier` serialises it to
either deterministic JSON or a plain-text report in the paper/blue/red visual
identity (rendered as sectioned ASCII for terminals).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Dict, Mapping, Tuple

from curveprotocol.coverage import compute_coverage, grade
from curveprotocol.graph import ancestry, find_leaves, find_roots
from curveprotocol.model import Dossier, LineageGraph, digest_graph


def build_dossier(graph: LineageGraph) -> Dossier:
    """Compute the full :class:`Dossier` for *graph*.

    The dossier bundles the graph digest, root/leaf sets, the coverage report,
    the resolved lineage for every leaf, and histograms of transformation ops
    and artifact kinds.
    """
    roots = find_roots(graph)
    leaves = find_leaves(graph)
    coverage = compute_coverage(graph)

    lineages: Dict[str, Tuple[str, ...]] = {}
    for leaf in leaves:
        chain = ancestry(graph, leaf)
        lineages[leaf] = chain + (leaf,)

    op_hist = Counter(
        graph.transformations[t].op for t in graph.transformation_ids
    )
    kind_hist = Counter(
        graph.artifacts[a].kind for a in graph.artifact_ids
    )

    return Dossier(
        graph_digest=digest_graph(graph),
        roots=roots,
        leaves=leaves,
        coverage=coverage,
        lineages=lineages,
        op_histogram=dict(op_hist),
        kind_histogram=dict(kind_hist),
    )


def render_dossier(
    dossier: Dossier,
    graph: LineageGraph,
    *,
    fmt: str = "text",
) -> str:
    """Render a dossier as ``"json"`` or ``"text"``.

    JSON output is deterministic (sorted keys, fixed separators) and suitable
    for diffing across runs. Text output is a sectioned report for terminals.
    """
    if fmt == "json":
        return json.dumps(dossier.to_dict(), indent=2, sort_keys=True)
    if fmt == "text":
        return _render_text(dossier, graph)
    raise ValueError(f"unsupported format: {fmt!r}")


# --------------------------------------------------------------------------- #
# Text rendering
# --------------------------------------------------------------------------- #

_RULE = "=" * 72
_SUBRULE = "-" * 72


def _render_text(dossier: Dossier, graph: LineageGraph) -> str:
    cov = dossier.coverage
    lines = []
    lines.append(_RULE)
    lines.append("ARTIFACTLENS PROVENANCE DOSSIER")
    lines.append(_RULE)
    lines.append(f"graph digest : {dossier.graph_digest}")
    lines.append(f"artifacts    : {cov.total_artifacts}")
    lines.append(f"roots        : {len(dossier.roots)}")
    lines.append(f"leaves       : {len(dossier.leaves)}")
    lines.append("")

    lines.append("COVERAGE")
    lines.append(_SUBRULE)
    lines.append(
        f"score        : {cov.coverage_score:.4f}  (grade {grade(cov.coverage_score)})"
    )
    lines.append(f"connected    : {cov.connected_artifacts}/{cov.total_artifacts}")
    lines.append(f"verified     : {cov.verified_artifacts}/{cov.total_artifacts}")
    lines.append(f"rooted       : {cov.rooted_artifacts}/{cov.total_artifacts}")
    if cov.orphan_ids:
        lines.append(f"orphans      : {', '.join(cov.orphan_ids)}")
    if cov.dangling_ids:
        lines.append(f"dangling     : {', '.join(cov.dangling_ids)}")
    lines.append("")

    lines.append("ROOTS")
    lines.append(_SUBRULE)
    for rid in dossier.roots:
        art = graph.artifacts[rid]
        lines.append(f"  * {rid}  [{art.kind}]  {art.label}")
    lines.append("")

    lines.append("LEAVES & LINEAGE")
    lines.append(_SUBRULE)
    for leaf in dossier.leaves:
        art = graph.artifacts[leaf]
        lines.append(f"  * {leaf}  [{art.kind}]  {art.label}")
        chain = dossier.lineages.get(leaf, ())
        if len(chain) > 1:
            lines.append("      " + "  ->  ".join(chain))
    lines.append("")

    lines.append("OPERATION HISTOGRAM")
    lines.append(_SUBRULE)
    for op, count in sorted(dossier.op_histogram.items()):
        lines.append(f"  {op:<12} {_bar(count)} {count}")
    lines.append("")

    lines.append("KIND HISTOGRAM")
    lines.append(_SUBRULE)
    for kind, count in sorted(dossier.kind_histogram.items()):
        lines.append(f"  {kind:<14} {_bar(count)} {count}")
    lines.append(_RULE)

    return "\n".join(lines)


def _bar(count: int, unit: str = "#") -> str:
    return unit * min(count, 40)
