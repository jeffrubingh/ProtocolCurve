"""ArtifactLens: an agent output provenance explorer.

ArtifactLens ingests artifact nodes and the transformations that connect them,
builds a lineage graph, measures provenance coverage, locates root artifacts,
and renders deterministic dossier reports.
"""

from artifactlens.model import (
    Artifact,
    Transformation,
    LineageGraph,
    CoverageReport,
    Dossier,
