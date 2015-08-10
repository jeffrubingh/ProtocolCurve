"""Command line interface for ArtifactLens.

The CLI exposes the full workflow as subcommands built on the standard library
``argparse``:

* ``ingest``   — load a graph document and echo a normalised, validated copy.
* ``roots``    — list root and leaf artifacts.
* ``coverage`` — compute and print the provenance coverage report.
* ``dossier``  — build and render the full dossier (text or JSON).
* ``lineage``  — print the resolved ancestry chain for one artifact.

Every command reads a graph document (or separate artifact/transformation
files) and emits deterministic output so results can be diffed across runs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from artifactlens import __version__
from artifactlens.coverage import compute_coverage, grade
from artifactlens.dossier import build_dossier, render_dossier
from artifactlens.graph import GraphError, ancestry, build_graph, find_leaves, find_roots
from artifactlens.io import (
    load_graph_document,
    load_records,
    parse_artifacts,
    parse_transformations,
    write_json,
)
from artifactlens.model import Artifact, LineageGraph, Transformation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="artifactlens",
        description="Agent output provenance explorer.",
    )
    parser.add_argument(
        "--version", action="version", version=f"artifactlens {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared input arguments factory.
    def add_input_args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "graph",
            nargs="?",
            type=Path,
            help="path to a combined graph document (JSON with artifacts + "
            "transformations)",
        )
        p.add_argument(
            "--artifacts",
            type=Path,
            help="path to an artifacts JSON/JSONL file",
        )
        p.add_argument(
            "--transformations",
            type=Path,
            help="path to a transformations JSON/JSONL file",
        )
        p.add_argument(
            "--lenient",
            action="store_true",
            help="synthesise unknown artifacts instead of failing",
        )

    p_ingest = sub.add_parser("ingest", help="validate and echo a graph")
    add_input_args(p_ingest)
    p_ingest.add_argument("--out", type=Path, help="write normalised graph here")

    p_roots = sub.add_parser("roots", help="list root and leaf artifacts")
    add_input_args(p_roots)

    p_cov = sub.add_parser("coverage", help="compute provenance coverage")
    add_input_args(p_cov)
    p_cov.add_argument(
        "--json", action="store_true", help="emit JSON instead of text"
    )

    p_dos = sub.add_parser("dossier", help="build the full dossier report")
    add_input_args(p_dos)
    p_dos.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    p_dos.add_argument("--out", type=Path, help="write the dossier here")

    p_lin = sub.add_parser("lineage", help="show ancestry of one artifact")
    add_input_args(p_lin)
    p_lin.add_argument("artifact_id", help="artifact to trace")

    return parser


def _load_graph(args: argparse.Namespace) -> LineageGraph:
    strict = not getattr(args, "lenient", False)
    if args.graph is not None:
        arts, trs = load_graph_document(args.graph)
        return build_graph(arts, trs, strict=strict)
