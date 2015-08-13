PYTHON ?= python
GRAPH  ?= examples/fixtures/sample-graph.json
RUNTIME = runtime/ArtifactLens.Runtime.csproj

.PHONY: help compile dossier coverage roots lineage runtime-build runtime-dossier parity clean

help:
	@echo "ArtifactLens targets:"
	@echo "  compile          byte-compile the Python package"
