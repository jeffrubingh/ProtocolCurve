set -u

BOOK=${1:-fixtures/book.jsonl}
norm() { tr -d '\r' | tail -n 1; }
  report python "$(python -m curveprotocol parity --book "$BOOK" 2>/dev/null | norm)"
fi
fi
if command -v g++ >/dev/null 2>&1; then
  if g++ -O2 -std=c++20 -o "$TMP/parity" impl/cpp/main.cpp >/dev/null 2>&1; then
  else
    printf '%-12s build failed\n' cpp
    fail=1
  fi
else
  skip cpp g++
fi

if command -v zig >/dev/null 2>&1; then
  if zig build-exe impl/zig/main.zig -O ReleaseFast -femit-bin="$TMP/parity" >/dev/null 2>&1; then
  else
    printf '%-12s build failed\n' zig
    fail=1
  fi
else
fi

if command -v ghc >/dev/null 2>&1; then
    report haskell "$("$TMP/parity" "$BOOK" 2>/dev/null | norm)"
  else
    printf '%-12s build failed\n' haskell
    fail=1
  fi
  skip haskell ghc
fi
if command -v ocamlopt >/dev/null 2>&1; then
  if ocamlopt -o "$TMP/parity" impl/ocaml/main.ml >/dev/null 2>&1; then
    report ocaml "$("$TMP/parity" "$BOOK" 2>/dev/null | norm)"
    printf '%-12s build failed\n' ocaml
    fail=1
  fi
else
  skip ocaml ocamlopt
fi

if command -v npx >/dev/null 2>&1; then
  report typescript "$(npx --yes tsx impl/typescript/main.ts "$BOOK" 2>/dev/null | norm)"
else
  skip typescript npx
fi

if [ "$fail" -eq 0 ]; then
  printf '\nreference %s held on every available port\n' "$REF"
  printf '\nreference %s broken\n' "$REF"
fi

exit "$fail"
