# Changelog

All notable changes to ArtifactLens are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning.

## [1.0.0] - 2026-01-04

### Added
- Immutable data model for artifacts, transformations, lineage graphs,
  coverage reports and dossiers.
- Graph construction with duplicate detection, endpoint validation, lenient
  synthesis of unknown endpoints, and cycle detection.
- Root and leaf discovery plus deterministic transitive ancestry resolution.
- Weighted provenance coverage scoring across connectivity, verification,
  rootedness and transformation confidence, with letter grading.
- Dossier assembly with graph digest, per-leaf lineage chains, and operation
  and kind histograms; text and JSON renderers.
- JSON and JSON Lines ingest with automatic format detection, and combined
