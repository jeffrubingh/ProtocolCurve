"""Provenance coverage scoring for ArtifactLens.

Coverage answers a single question: *how much of this graph can we actually
trust and trace?* It combines four independent signals into one score:

1. **Connectivity** — the fraction of artifacts touched by any transformation.
2. **Verification** — the fraction of artifacts carrying a content hash.
3. **Rootedness** — the fraction of artifacts that trace back to a root.
4. **Confidence** — the mean effective confidence of all transformations.

The four signals are combined with fixed weights so the score is reproducible
and easy to reason about. Weights are exposed as module constants for callers
that want to document or audit them.
"""

from __future__ import annotations

from typing import Set, Tuple

from artifactlens.graph import find_roots, reaches_root
from artifactlens.model import CoverageReport, LineageGraph

#: Weight applied to the connectivity signal.
W_CONNECTIVITY = 0.30
#: Weight applied to the verification signal.
W_VERIFICATION = 0.25
#: Weight applied to the rootedness signal.
W_ROOTEDNESS = 0.30
#: Weight applied to the mean transformation confidence signal.
W_CONFIDENCE = 0.15

_WEIGHT_SUM = W_CONNECTIVITY + W_VERIFICATION + W_ROOTEDNESS + W_CONFIDENCE


def compute_coverage(graph: LineageGraph) -> CoverageReport:
    """Compute a :class:`CoverageReport` for *graph*.

    The function is pure and deterministic: identical graphs always yield
    identical reports, including the ordering of the ``orphan_ids`` and
    ``dangling_ids`` lists.
    """
    total = len(graph.artifacts)
    if total == 0:
        return CoverageReport(
            total_artifacts=0,
            connected_artifacts=0,
            verified_artifacts=0,
            rooted_artifacts=0,
            orphan_ids=(),
            dangling_ids=(),
            coverage_score=0.0,
        )

    roots: Set[str] = set(find_roots(graph))

    connected = 0
    verified = 0
    rooted = 0
    orphans = []
    dangling = []

    for aid in graph.artifact_ids:
