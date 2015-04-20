"""Graph construction and traversal for ArtifactLens.

This module turns raw artifact and transformation records into a validated
:class:`~artifactlens.model.LineageGraph` and provides the traversal helpers
used by the coverage and dossier layers.

The graph is a bipartite-flavoured DAG: artifacts are nodes and each
transformation induces edges from every input artifact to every output
artifact. Cycles are rejected during construction because provenance must flow
forward in time.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Set, Tuple

from artifactlens.model import Artifact, LineageGraph, Transformation


class GraphError(ValueError):
    """Raised when a graph cannot be constructed from the given records."""


def build_graph(
    artifacts: Iterable[Artifact],
    transformations: Iterable[Transformation],
    *,
    strict: bool = True,
) -> LineageGraph:
    """Assemble and validate a :class:`LineageGraph`.

    Parameters
    ----------
    artifacts:
        Iterable of artifact value objects.
    transformations:
        Iterable of transformation value objects.
    strict:
        When ``True`` (default), transformations that reference unknown
        artifact ids raise :class:`GraphError`. When ``False``, missing
        endpoints are synthesised as ``unknown`` artifacts so that a partial
        graph can still be explored.

    Returns
    -------
    LineageGraph
        A fully indexed, cycle-free graph.
    """
    art_map: Dict[str, Artifact] = {}
    for art in artifacts:
        norm = art.normalised()
        if norm.id in art_map:
            raise GraphError(f"duplicate artifact id: {norm.id!r}")
        art_map[norm.id] = norm

    tr_map: Dict[str, Transformation] = {}
    for tr in transformations:
        norm = tr.normalised()
        if norm.id in tr_map:
            raise GraphError(f"duplicate transformation id: {norm.id!r}")
        tr_map[norm.id] = norm

    # Validate / synthesise endpoints.
    for tr in tr_map.values():
        for endpoint in (*tr.inputs, *tr.outputs):
            if endpoint not in art_map:
                if strict:
                    raise GraphError(
                        f"transformation {tr.id!r} references unknown "
                        f"artifact {endpoint!r}"
                    )
                art_map[endpoint] = Artifact(id=endpoint).normalised()

    producers: Dict[str, List[str]] = {aid: [] for aid in art_map}
    consumers: Dict[str, List[str]] = {aid: [] for aid in art_map}
    for tid in sorted(tr_map):
        tr = tr_map[tid]
        for out in tr.outputs:
            producers[out].append(tid)
        for inp in tr.inputs:
            consumers[inp].append(tid)

    graph = LineageGraph(
        artifacts=art_map,
        transformations=tr_map,
        producers={k: tuple(v) for k, v in producers.items()},
        consumers={k: tuple(v) for k, v in consumers.items()},
    )
    _assert_acyclic(graph)
    return graph


def find_roots(graph: LineageGraph) -> Tuple[str, ...]:
    """Return artifact ids that are produced by no transformation.

    Roots are the ultimate sources of provenance: prompts, seed documents, or
    externally supplied datasets that ArtifactLens did not observe being
    generated. Orphan artifacts (no edges at all) are still roots.
    """
    roots = [
        aid
        for aid in graph.artifact_ids
        if not graph.producers.get(aid)
    ]
    return tuple(sorted(roots))


def find_leaves(graph: LineageGraph) -> Tuple[str, ...]:
    """Return artifact ids that are consumed by no transformation.

    Leaves are terminal outputs: the final deliverables of an agent run.
    """
    leaves = [
        aid
        for aid in graph.artifact_ids
        if not graph.consumers.get(aid)
    ]
    return tuple(sorted(leaves))


def ancestry(graph: LineageGraph, artifact_id: str) -> Tuple[str, ...]:
    """Return every ancestor of *artifact_id* in deterministic topo order.

    The result is the transitive closure of :meth:`LineageGraph.parents`
    excluding the artifact itself, ordered so that ancestors always precede
    their descendants.
    """
    if artifact_id not in graph.artifacts:
        raise GraphError(f"unknown artifact id: {artifact_id!r}")

    visited: Set[str] = set()
    order: List[str] = []

