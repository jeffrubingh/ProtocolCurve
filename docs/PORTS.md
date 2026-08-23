# Ports

Every port is a standalone reimplementation of the engine. There is no shared
parser, no shared runtime, no FFI. Each one reads the canonical text format on
stdin or from a path and prints a fingerprint.

## Canonical format

Two record types, one per line, pipe separated, no header:
- `R` is a reserve tranche. `band` is one of `seed`, `core`, `buffer`, `edge`,
  `sink`. `balance` is integer micro-USDT.
- `F` is a flow. `op` is one of `derive`, `merge`, `split`. `inputs` and
  `outputs` are comma separated reserve ids, or `-` when empty.
- Records are sorted by id before hashing, so input order does not matter.

The fingerprint is FNV-1a 64 over the sorted canonical line stream, printed as
sixteen lowercase hex digits. The reference value for `fixtures/book.jsonl` is
`59c1ddca0f55afdb`.

## What a port must not do

- Use floating point anywhere in the money path.
- Reorder records before sorting.
- Emit a trailing newline inside the hashed stream.

## Matrix

| port | entry point | build |
| ---- | ----------- | ----- |
| Go | `impl/go` | `go build ./...` |
| C++ | `impl/cpp/main.cpp` | `g++ -O2 -std=c++20` |
| Zig | `impl/zig/main.zig` | `zig build-exe -O ReleaseFast` |
| Haskell | `impl/haskell/Main.hs` | `ghc -O2` |
| OCaml | `impl/ocaml/main.ml` | `ocamlopt` |
| TypeScript | `impl/typescript/main.ts` | `tsx` |

## Running the check
The script skips any toolchain that is not installed and fails on any
fingerprint mismatch. CI runs the same check per language, with the exotic
toolchains marked `continue-on-error` so a broken distro package does not red
the whole build.
