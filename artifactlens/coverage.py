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
        has_producer = bool(graph.producers.get(aid))
        has_consumer = bool(graph.consumers.get(aid))
        if has_producer or has_consumer:
            connected += 1
        else:
            orphans.append(aid)

        if graph.artifacts[aid].is_verified:
            verified += 1

        if reaches_root(graph, aid, roots):
            rooted += 1

        # Dangling: not a root, yet nothing produced it (broken provenance).
        if aid not in roots and not has_producer:
            dangling.append(aid)

    mean_conf = _mean_confidence(graph)

    connectivity = connected / total
    verification = verified / total
    rootedness = rooted / total

    score = (
        W_CONNECTIVITY * connectivity
        + W_VERIFICATION * verification
        + W_ROOTEDNESS * rootedness
        + W_CONFIDENCE * mean_conf
    ) / _WEIGHT_SUM

    return CoverageReport(
        total_artifacts=total,
        connected_artifacts=connected,
        verified_artifacts=verified,
        rooted_artifacts=rooted,
        orphan_ids=tuple(sorted(orphans)),
        dangling_ids=tuple(sorted(dangling)),
        coverage_score=score,
    )


def _mean_confidence(graph: LineageGraph) -> float:
    if not graph.transformations:
        return 1.0
    total = sum(
        graph.transformations[t].effective_confidence
        for t in graph.transformation_ids
    )
    return total / len(graph.transformations)


def grade(score: float) -> str:
    """Map a coverage score to a single-letter grade for quick scanning."""
    if score >= 0.90:
        return "A"
    if score >= 0.75:
        return "B"
    if score >= 0.60:
        return "C"
    if score >= 0.40:
        return "D"
    return "F"
