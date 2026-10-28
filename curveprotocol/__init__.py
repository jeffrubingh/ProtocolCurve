"""CurveProtocol: an agent output provenance explorer.

CurveProtocol ingests artifact nodes and the transformations that connect them,
builds a lineage graph, measures provenance coverage, locates root artifacts,
and renders deterministic dossier reports.
"""

from curveprotocol.model import (
    Artifact,
    Transformation,
    LineageGraph,
    CoverageReport,
    Dossier,
)
from curveprotocol.graph import build_graph, find_roots, find_leaves
from curveprotocol.coverage import compute_coverage
from curveprotocol.dossier import build_dossier, render_dossier

__version__ = "1.0.0"

__all__ = [
    "Artifact",
    "Transformation",
    "LineageGraph",
    "CoverageReport",
    "Dossier",
    "build_graph",
    "find_roots",
    "find_leaves",
    "compute_coverage",
    "build_dossier",
    "render_dossier",
    "__version__",
]
