"""Core data model for ArtifactLens.

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
        Optional digest of the artifact body. When absent, ArtifactLens treats
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
