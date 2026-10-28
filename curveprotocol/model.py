"""Core data model for CurveProtocol.

The model layer defines the immutable value objects that flow through the
pipeline: :class:`Artifact` (a node in the provenance graph),
:class:`Transformation` (a directed edge produced by an agent step),
:class:`LineageGraph` (the assembled directed acyclic structure),
:class:`CoverageReport` (provenance completeness metrics), and
:class:`Dossier` (the final report bundle).

All objects are frozen dataclasses so that a graph, once assembled, cannot be
mutated in place. Serialization is deterministic: keys are always emitted in a
fixed order and collections are sorted by identifier.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
# Artifact
# --------------------------------------------------------------------------- #

#: Recognised artifact kinds. The kind drives colour selection in reports and
#: influences the confidence heuristics applied during coverage scoring.
ARTIFACT_KINDS: Tuple[str, ...] = (
    "prompt",
    "document",
    "code",
    "dataset",
    "model_output",
    "tool_result",
    "summary",
    "decision",
    "unknown",
)


@dataclass(frozen=True)
class Artifact:
    """A single node in the provenance graph.

    An artifact represents any discrete unit of content an agent produced or
    consumed: a prompt, a retrieved document, a generated code file, a tool
    result, and so on.

    Attributes
    ----------
    id:
        Stable unique identifier. Used as the primary key everywhere.
    kind:
        One of :data:`ARTIFACT_KINDS`. Unknown values are normalised to
        ``"unknown"`` during ingest.
    label:
        Human readable name shown in reports.
    content_hash:
        Optional digest of the artifact body. When absent, CurveProtocol treats
        the artifact as *unverified* which lowers its provenance score.
    produced_by:
        Optional agent or actor identifier that emitted the artifact.
    created_at:
        Optional ISO-8601 timestamp string. Never parsed, only carried through
        and used for stable ordering as a tie-breaker.
    attributes:
        Free-form metadata bag. Values must be JSON serialisable.
    """

    id: str
    kind: str = "unknown"
    label: str = ""
    content_hash: Optional[str] = None
    produced_by: Optional[str] = None
    created_at: Optional[str] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def normalised(self) -> "Artifact":
        """Return a copy with the kind coerced into the known vocabulary."""
        kind = self.kind if self.kind in ARTIFACT_KINDS else "unknown"
        label = self.label or self.id
        return Artifact(
            id=self.id,
            kind=kind,
            label=label,
            content_hash=self.content_hash,
            produced_by=self.produced_by,
            created_at=self.created_at,
            attributes=dict(self.attributes),
        )

    @property
    def is_verified(self) -> bool:
        """True when a content hash is present."""
        return bool(self.content_hash)

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic dictionary form with a fixed key order."""
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "content_hash": self.content_hash,
            "produced_by": self.produced_by,
            "created_at": self.created_at,
            "attributes": _sorted_mapping(self.attributes),
        }

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "Artifact":
        if "id" not in raw:
            raise ValueError("artifact record is missing required field 'id'")
        return Artifact(
            id=str(raw["id"]),
            kind=str(raw.get("kind", "unknown")),
            label=str(raw.get("label", "")),
            content_hash=_opt_str(raw.get("content_hash")),
            produced_by=_opt_str(raw.get("produced_by")),
            created_at=_opt_str(raw.get("created_at")),
            attributes=dict(raw.get("attributes", {}) or {}),
        ).normalised()


# --------------------------------------------------------------------------- #
# Transformation
# --------------------------------------------------------------------------- #

#: Recognised transformation operations.
TRANSFORM_OPS: Tuple[str, ...] = (
    "generate",
    "retrieve",
    "summarize",
    "translate",
    "refactor",
    "merge",
    "split",
    "validate",
    "annotate",
    "derive",
)


@dataclass(frozen=True)
class Transformation:
    """A directed edge describing how outputs derive from inputs.

    A transformation captures a single agent step. It fans in from one or more
    input artifacts and fans out to one or more output artifacts. Modelling
    both sides as lists lets CurveProtocol represent merges (many inputs) and
    splits (many outputs) without special cases.

    Attributes
    ----------
    id:
        Stable unique identifier for the step.
    op:
        A verb from :data:`TRANSFORM_OPS`; unknown verbs are kept verbatim.
    inputs:
        Artifact ids consumed by the step.
    outputs:
        Artifact ids produced by the step.
    agent:
        Optional agent / tool identifier that ran the step.
    confidence:
        Optional float in ``[0, 1]`` describing how certain the recording
        pipeline is that this edge is real. Missing confidence is treated as
        ``1.0`` for coverage but flagged in the dossier.
    attributes:
        Free-form JSON serialisable metadata.
    """

    id: str
    op: str
    inputs: Sequence[str] = field(default_factory=tuple)
    outputs: Sequence[str] = field(default_factory=tuple)
    agent: Optional[str] = None
    confidence: Optional[float] = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def normalised(self) -> "Transformation":
        return Transformation(
            id=self.id,
            op=self.op or "derive",
            inputs=tuple(dict.fromkeys(str(x) for x in self.inputs)),
            outputs=tuple(dict.fromkeys(str(x) for x in self.outputs)),
            agent=self.agent,
            confidence=self.confidence,
            attributes=dict(self.attributes),
        )

    @property
    def effective_confidence(self) -> float:
        if self.confidence is None:
            return 1.0
        return max(0.0, min(1.0, float(self.confidence)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "op": self.op,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "agent": self.agent,
            "confidence": self.confidence,
            "attributes": _sorted_mapping(self.attributes),
        }

    @staticmethod
    def from_dict(raw: Mapping[str, Any]) -> "Transformation":
        if "id" not in raw:
            raise ValueError("transformation record is missing required field 'id'")
        conf = raw.get("confidence")
        return Transformation(
            id=str(raw["id"]),
            op=str(raw.get("op", "derive")),
            inputs=tuple(str(x) for x in (raw.get("inputs") or [])),
            outputs=tuple(str(x) for x in (raw.get("outputs") or [])),
            agent=_opt_str(raw.get("agent")),
            confidence=(float(conf) if conf is not None else None),
            attributes=dict(raw.get("attributes", {}) or {}),
        ).normalised()


# --------------------------------------------------------------------------- #
# LineageGraph
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LineageGraph:
    """An assembled provenance graph.

    The graph stores artifacts keyed by id and transformations keyed by id,
    plus precomputed adjacency in both directions. Construction happens in
    :func:`curveprotocol.graph.build_graph`, which validates references and
    guarantees the maps are consistent.
    """

    artifacts: Mapping[str, Artifact]
    transformations: Mapping[str, Transformation]
    # artifact id -> transformation ids that produce it
    producers: Mapping[str, Tuple[str, ...]]
    # artifact id -> transformation ids that consume it
    consumers: Mapping[str, Tuple[str, ...]]

    @property
    def artifact_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.artifacts))

    @property
    def transformation_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.transformations))

    def parents(self, artifact_id: str) -> Tuple[str, ...]:
        """Input artifacts feeding every transformation that produced *artifact_id*."""
        seen: List[str] = []
        for tid in self.producers.get(artifact_id, ()):  # deterministic order
            for src in self.transformations[tid].inputs:
                if src not in seen:
                    seen.append(src)
        return tuple(sorted(seen))

    def children(self, artifact_id: str) -> Tuple[str, ...]:
        """Output artifacts of every transformation that consumed *artifact_id*."""
        seen: List[str] = []
        for tid in self.consumers.get(artifact_id, ()):
            for dst in self.transformations[tid].outputs:
                if dst not in seen:
                    seen.append(dst)
        return tuple(sorted(seen))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifacts": [self.artifacts[a].to_dict() for a in self.artifact_ids],
            "transformations": [
                self.transformations[t].to_dict() for t in self.transformation_ids
            ],
        }


# --------------------------------------------------------------------------- #
# CoverageReport
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CoverageReport:
    """Provenance completeness metrics for a graph.

    Attributes
    ----------
    total_artifacts:
        Number of artifacts in the graph.
    connected_artifacts:
        Artifacts that participate in at least one transformation.
    verified_artifacts:
        Artifacts that carry a content hash.
    rooted_artifacts:
        Artifacts that can trace a path back to a declared root.
    orphan_ids:
        Artifacts with no producer and no consumer edges.
    dangling_ids:
        Non-root artifacts with no producing transformation.
    coverage_score:
        Weighted score in ``[0, 1]``; see :mod:`curveprotocol.coverage`.
    """

    total_artifacts: int
    connected_artifacts: int
    verified_artifacts: int
    rooted_artifacts: int
    orphan_ids: Tuple[str, ...]
    dangling_ids: Tuple[str, ...]
    coverage_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_artifacts": self.total_artifacts,
            "connected_artifacts": self.connected_artifacts,
            "verified_artifacts": self.verified_artifacts,
            "rooted_artifacts": self.rooted_artifacts,
            "orphan_ids": list(self.orphan_ids),
            "dangling_ids": list(self.dangling_ids),
            "coverage_score": round(self.coverage_score, 4),
        }


# --------------------------------------------------------------------------- #
# Dossier
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Dossier:
    """The complete report bundle produced by CurveProtocol."""

    graph_digest: str
    roots: Tuple[str, ...]
    leaves: Tuple[str, ...]
    coverage: CoverageReport
    lineages: Mapping[str, Tuple[str, ...]]  # leaf id -> ordered ancestry
    op_histogram: Mapping[str, int]
    kind_histogram: Mapping[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_digest": self.graph_digest,
            "roots": list(self.roots),
            "leaves": list(self.leaves),
            "coverage": self.coverage.to_dict(),
            "lineages": {k: list(v) for k, v in sorted(self.lineages.items())},
            "op_histogram": dict(sorted(self.op_histogram.items())),
            "kind_histogram": dict(sorted(self.kind_histogram.items())),
        }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _sorted_mapping(mapping: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: mapping[k] for k in sorted(mapping)}


def digest_graph(graph: "LineageGraph") -> str:
    """Return a stable SHA-256 digest of the graph structure.

    The digest depends only on artifact ids/kinds/hashes and transformation
    ids/ops/edges, so re-serialising the same logical graph always yields the
    same value regardless of input ordering.
    """
    hasher = hashlib.sha256()
    for aid in graph.artifact_ids:
        art = graph.artifacts[aid]
        hasher.update(f"A|{art.id}|{art.kind}|{art.content_hash or ''}\n".encode())
    for tid in graph.transformation_ids:
        tr = graph.transformations[tid]
        ins = ",".join(sorted(tr.inputs))
        outs = ",".join(sorted(tr.outputs))
        hasher.update(f"T|{tr.id}|{tr.op}|{ins}|{outs}\n".encode())
    return hasher.hexdigest()
