PYTHON ?= python
GRAPH  ?= examples/fixtures/sample-graph.json
RUNTIME = runtime/ArtifactLens.Runtime.csproj

.PHONY: help compile dossier coverage roots lineage runtime-build runtime-dossier parity clean

help:
	@echo "ArtifactLens targets:"
	@echo "  compile          byte-compile the Python package"
	@echo "  dossier          render the dossier for the fixture graph"
	@echo "  coverage         print coverage for the fixture graph"
	@echo "  roots            list roots and leaves"
	@echo "  lineage ID=<id>  trace ancestry of an artifact"
	@echo "  runtime-build    build the C# runtime (Release)"
	@echo "  runtime-dossier  render the dossier via the native runtime"
	@echo "  parity           compare Python and runtime graph digests"
	@echo "  clean            remove build and cache artifacts"

compile:
	$(PYTHON) -m compileall artifactlens

dossier:
	$(PYTHON) -m artifactlens dossier $(GRAPH)

coverage:
	$(PYTHON) -m artifactlens coverage $(GRAPH)

roots:
	$(PYTHON) -m artifactlens roots $(GRAPH)

lineage:
	$(PYTHON) -m artifactlens lineage $(GRAPH) $(ID)

runtime-build:
	dotnet build $(RUNTIME) -c Release

runtime-dossier:
	dotnet run --project $(RUNTIME) -c Release -- dossier $(GRAPH)

parity:
	$(PYTHON) -m artifactlens dossier --format json $(GRAPH) | $(PYTHON) -c "import sys,json;print('py digest:',json.load(sys.stdin)['graph_digest'])"
	dotnet run --project $(RUNTIME) -c Release -- digest $(GRAPH)

clean:
	$(PYTHON) -c "import shutil,glob,os;[shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)]"
	$(PYTHON) -c "import shutil;shutil.rmtree('runtime/bin',ignore_errors=True);shutil.rmtree('runtime/obj',ignore_errors=True)"
