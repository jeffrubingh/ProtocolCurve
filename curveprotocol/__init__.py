"""CurveProtocol: the Exponential Curve Protocol book engine.

CurveProtocol reads a reserve journal, assembles the book, scores liquidity
depth, projects the growth curve and renders a deterministic trajectory report.
"""

from curveprotocol.book import BookError, build_book, find_origins, find_terminals
from curveprotocol.curve import compound, fingerprint, project, split_bands
from curveprotocol.depth import compute_depth
from curveprotocol.model import CurveBook, DepthReport, Flow, Reserve, Trajectory
from curveprotocol.trajectory import build_trajectory, render

__version__ = "1.0.0"

__all__ = [
    "BookError",
    "build_book",
    "find_origins",
    "find_terminals",
    "compound",
    "fingerprint",
    "project",
    "split_bands",
    "compute_depth",
    "CurveBook",
    "DepthReport",
    "Flow",
    "Reserve",
    "Trajectory",
    "build_trajectory",
    "render",
    "__version__",
]
