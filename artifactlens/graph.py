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
