# Changelog

All notable changes are recorded here. Versions are cut from `main` only after
`scripts/parity.sh` and the full test suite pass.

## 0.1.0

First cut of the protocol.

- Integer micro-USDT money path, no floats, no rounding drift.
- `curve.compound` with post-step ceiling clamp, `project`, `epochs_to_ceiling`.
- `curve.split_bands` and `curve.band_weights` for harvest distribution.
- Book assembly with strict and lenient modes, DAG cycle rejection, origins and
  terminal detection, ancestry walk.
- `depth.depth_score` band weighted, `DEPTH_FLOOR` absolute, grades A to E,
  `shortfalls` largest gap first.
- Trajectory assembly with text and JSON renderers.
- Canonical `R|` / `F|` parity format and FNV-1a 64 fingerprint.
- CLI: `ingest`, `origins`, `depth`, `trajectory`, `trace`, `curve`, `verify`,
  `parity`.
- Ports: Rust, Go, C++, Zig, Haskell, OCaml, TypeScript.
- CI matrix with per-language fingerprint assertion.
