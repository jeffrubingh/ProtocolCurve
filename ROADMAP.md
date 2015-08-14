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
