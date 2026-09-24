<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/C%23-512BD4?style=flat-square&logo=csharp&logoColor=white" alt="C#">
  <img src="https://img.shields.io/badge/Go-00ADD8?style=flat-square&logo=go&logoColor=white" alt="Go">
  <img src="https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=cplusplus&logoColor=white" alt="C++">
  <img src="https://img.shields.io/badge/Zig-F7A41D?style=flat-square&logo=zig&logoColor=black" alt="Zig">
  <img src="https://img.shields.io/badge/Haskell-5D4F85?style=flat-square&logo=haskell&logoColor=white" alt="Haskell">
  <img src="https://img.shields.io/badge/OCaml-EC6813?style=flat-square&logo=ocaml&logoColor=white" alt="OCaml">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
</p>

<h1 align="center">Exponential Curve Protocol</h1>

<p align="center"><sub>integer reserve engine &nbsp;·&nbsp; micro-USDT &nbsp;·&nbsp; deterministic &nbsp;·&nbsp; no floats</sub></p>

<hr>

> Reserves hold USDT in bands. A curve compounds them toward a ceiling. Depth
> scoring reports how much of the book survives a draw.
>
> Everything the engine prints is a function of the book and nothing else, so two
> runs on two machines produce the same bytes. The engine is the specification;
> the ports exist to prove it.

<p align="center">
  <img src="https://i.imgur.com/bJtD2Ea.png" width="900" alt="Exponential Curve Protocol">
</p>

## Properties

What the engine guarantees, and what enforces it.

- **Integer money path** — balances are micro-USDT, division floors, no float touches a balance.
- **Monotone curve** — a negative rate folds to zero, a series never decreases.
- **Post-step clamp** — the ceiling applies after growth, never before.
- **Deterministic output** — records sort by id, keys emit in fixed order.
- **Cycle safety** — flow graphs are DAGs, back edges are rejected at assembly.
- **Cross-language parity** — every port must reproduce one FNV-1a 64 fingerprint.

## Model

Five bands, drained in a fixed order.

A reserve is a tranche of a single band. A flow moves value between tranches and
carries one operation: `derive`, `merge` or `split`. Bands are drained in order, so
the band of a tranche decides its weight under a draw.

| band | weight | role |
| --- | --- | --- |
| `seed` | 1.00 | bootstrap tranche, first in |
| `core` | 1.00 | standing reserve |
| `buffer` | 0.80 | absorbs the first draw |
| `edge` | 0.45 | opportunistic, drained early |
| `sink` | 0.20 | last resort |

A flow with no inputs starts a branch and is reported as an origin. A reserve
nothing consumes is a terminal. Both are computed, never declared.

Assembly runs in two modes. `strict` rejects a book that references a tranche it
does not carry. `lenient` synthesizes the missing tranche so a partial journal still
scores, and marks it. A back edge aborts the build with `cycle through reserve <id>`
and the path that closed it.

<p align="center">
  <img src="https://i.imgur.com/Fl1ePoo.png" width="880" alt="Book assembly with a rejected cycle">
</p>

## Curve

One discrete step, clamped by a ceiling.

~~~
next = balance + balance * rate_bps // 10_000
next = min(next, ceiling)
~~~

`balance * rate_bps` is integer multiplication and the division floors, so a
projection is identical on every machine and in every port. The clamp lands after
the step, which is what gives the curve a shoulder instead of a runaway.

`epochs_to_ceiling` reports the steps to the shoulder, or `-1` when the rate is zero.
`MAX_ROUNDS` caps one call at 4096 steps. `split_bands` distributes a harvest across
bands and hands the remainder to the last band, so the parts always sum to the total.

<p align="center">
  <img src="https://i.imgur.com/XJ4jnIR.png" width="880" alt="Curve approaching the ceiling">
</p>

## Depth

Weighted depth over raw balance.

Raw balance is the wrong measure of safety. An edge tranche drains first, so it
counts for less than a core tranche. `depth_score` weights depth by band: a book of
pure edge sits near zero, a book of pure core sits at one.

Two lists are reported apart. **Thin** are funded tranches below the absolute floor
of 250 USDT — the floor is absolute, not relative, so a small tranche is thin
however large the book. **Dry** are unfunded tranches that nothing credits.

`shortfalls` returns bands under a per-band target, largest gap first, which is the
order a keeper works in. Grades run `A` to `E`.

<p align="center">
  <img src="https://i.imgur.com/HvhUolv.png" width="880" alt="Band weights and depth grading">
</p>

## CLI

Read-only, deterministic, diffable.

~~~
curveprotocol ingest book.jsonl
curveprotocol origins book.jsonl
curveprotocol depth book.jsonl
curveprotocol trajectory book.jsonl
curveprotocol trace book.jsonl r-03
curveprotocol curve 1000000 250 4000000
curveprotocol verify book.jsonl
curveprotocol parity book.jsonl
~~~

Exit codes are `0` ok, `2` usage, `3` bad journal, `4` fingerprint mismatch.

## Canonical format

Sorted by id, hashed with FNV-1a 64.

~~~
R|id|band|balance
F|id|op|inputs|outputs
~~~

Records sort by id before hashing, so input order does not matter. The fingerprint
is sixteen lowercase hex digits over the sorted stream.

<p align="center">
  <img src="https://i.imgur.com/GBTMpb3.png" width="880" alt="Ports agreeing on one fingerprint">
</p>

Reference value for `fixtures/book.jsonl`:

~~~
59c1ddca0f55afdb
~~~

A port that prints anything else is wrong, however clean its source.

## Ports

Standalone. No shared parser, no FFI, no linking to the engine.

- **Go** — `impl/go`, `go build ./...`
- **C++** — `impl/cpp/parity.cpp`, `g++ -O2 -std=c++20`
- **Zig** — `impl/zig/src/main.zig`, `zig build-exe -O ReleaseFast`
- **Haskell** — `impl/haskell/Parity.hs`, `ghc -O2`
- **OCaml** — `impl/ocaml/parity.ml`, `dune build`
- **TypeScript** — `impl/typescript/src/parity.ts`, `tsx`

A C# runtime lives in `runtime/`. Each port is written against `docs/PORTS.md`
alone.

## Build

~~~
pip install -e .
python -m unittest discover -s tests
bash scripts/parity.sh
~~~

`parity.sh` skips any toolchain that is not installed and fails on any mismatch.

## Layout

~~~
curveprotocol/   engine and CLI
impl/            parity ports
runtime/         C# runtime
fixtures/        sample books
docs/            curve, depth and port notes
~~~

## Non-goals

No database. No HTTP surface. No dashboard in this repository. The book is text and
stays text.

## Licence

MIT.
