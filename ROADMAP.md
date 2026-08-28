# Roadmap

ArtifactLens tracks its delivery against a small set of milestones. The four
milestones below are implemented and shipping in the current release.

## Implemented

- [x] **Lineage core** — artifact and transformation model, validated graph
  construction, cycle detection, and root/leaf/ancestry traversal.
- [x] **Coverage engine** — weighted provenance scoring across connectivity,
  verification, rootedness and confidence with deterministic grading.
- [x] **Dossier reports** — text and JSON dossiers with graph digest, per-leaf
  lineage chains, and operation/kind histograms.
- [x] **Native runtime parity** — the .NET 9 `ArtifactLens.Runtime` reproduces
  the Python graph digest and coverage score byte-for-byte on shared inputs.

## Exploring

- [ ] Interactive HTML lineage viewer generated from a dossier.
- [ ] Diffing two dossiers to surface provenance regressions between runs.
- [ ] Streaming ingest for very large trace logs.
