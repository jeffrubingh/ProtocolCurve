"""Dossier assembly and rendering for ArtifactLens.

A *dossier* is the human- and machine-readable report ArtifactLens produces
for a graph. :func:`build_dossier` computes the structured
:class:`~artifactlens.model.Dossier`; :func:`render_dossier` serialises it to
either deterministic JSON or a plain-text report in the paper/blue/red visual
identity (rendered as sectioned ASCII for terminals).
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Dict, Mapping, Tuple

from artifactlens.coverage import compute_coverage, grade
from artifactlens.graph import ancestry, find_leaves, find_roots
from artifactlens.model import Dossier, LineageGraph, digest_graph


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
