# ArtifactLens

Provenance coverage for build artifacts. Point it at a lineage graph and it reports how much of the
graph is connected, verified, rooted and how confident its transformations are.

## Usage

```bash
python -m artifactlens coverage examples/fixtures/sample-graph.json
python -m artifactlens dossier examples/fixtures/sample-graph.json -o reports/dossier.md
```

The score combines four fixed-weight signals; the weights are exported from
`artifactlens.coverage` so a report can quote them.

## Layout

- `artifactlens/` - graph model, coverage scoring, dossier rendering and the CLI.
- `runtime/` - the optional C# reader that renders the same dossier.
- `examples/fixtures/` - sample graphs and transformations.
