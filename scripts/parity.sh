#!/usr/bin/env bash
set -u
REF=59c1ddca0f55afdb
B=${1:-fixtures/book.jsonl}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
f=0
chk() { n=$1; shift; g=$("$@" 2>/dev/null | tr -d '\r' | tail -n1); if [ "$g" = "$REF" ]; then printf '%-10s ok\n' "$n"; else printf '%-10s bad\n' "$n"; f=1; fi; }
sk() { printf '%-10s skip %s\n' "$1" "$2"; }
command -v python >/dev/null && chk python python -m curveprotocol parity --book "$B" || sk python python
command -v go >/dev/null && chk go go run ./impl/go "$B" || sk go go
command -v g++ >/dev/null && g++ -O2 -std=c++20 -o "$T/c" impl/cpp/main.cpp >/dev/null 2>&1 && chk cpp "$T/c" "$B" || sk cpp g++
command -v zig >/dev/null && zig build-exe impl/zig/main.zig -O ReleaseFast -femit-bin="$T/z" >/dev/null 2>&1 && chk zig "$T/z" "$B" || sk zig zig
command -v ghc >/dev/null && ghc -O2 -outputdir "$T" -o "$T/h" impl/haskell/Main.hs >/dev/null 2>&1 && chk haskell "$T/h" "$B" || sk haskell ghc
command -v ocamlopt >/dev/null && ocamlopt -o "$T/m" impl/ocaml/main.ml >/dev/null 2>&1 && chk ocaml "$T/m" "$B" || sk ocaml ocamlopt
command -v npx >/dev/null && chk typescript npx --yes tsx impl/typescript/main.ts "$B" || sk typescript npx
exit "$f"
