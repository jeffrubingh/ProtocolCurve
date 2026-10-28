# CurveProtocol

Provenance coverage for build artifacts. Point it at a lineage graph and it reports how much of the
graph is connected, verified, rooted and how confident its transformations are.

## Usage

```bash
python -m curveprotocol coverage examples/fixtures/sample-graph.json
python -m curveprotocol dossier examples/fixtures/sample-graph.json -o reports/dossier.md
```

The score combines four fixed-weight signals; the weights are exported from
`curveprotocol.coverage` so a report can quote them.

## Layout

- `curveprotocol/` - graph model, coverage scoring, dossier rendering and the CLI.
- `runtime/` - the optional C# reader that renders the same dossier.
- `examples/fixtures/` - sample graphs and transformations.
