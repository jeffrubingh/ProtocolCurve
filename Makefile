PYTHON ?= python
BOOK   ?= examples/fixtures/book.txt
JOURNAL = --reserves examples/fixtures/reserves.jsonl --flows examples/fixtures/flows.jsonl

.PHONY: help compile test depth trajectory parity rust go cpp zig haskell ocaml ts clean

help:
	@echo "CurveProtocol targets:"
	@echo "  compile     byte-compile the Python package"
	@echo "  test        run the Python suite"
	@echo "  depth       print the depth report for the fixture journal"
	@echo "  trajectory  render the trajectory for the fixture journal"
	@echo "  parity      compare the fingerprint across every port"
	@echo "  rust go cpp zig haskell ocaml ts   run one port"
	@echo "  clean       drop caches and build output"

compile:
	$(PYTHON) -m compileall curveprotocol

test:
	$(PYTHON) -m unittest discover -s tests -v

depth:
	$(PYTHON) -m curveprotocol depth $(JOURNAL)

trajectory:
	$(PYTHON) -m curveprotocol trajectory $(JOURNAL)

parity:
	$(PYTHON) -m curveprotocol parity $(BOOK)
	cd impl/rust && cargo run --quiet -- ../../$(BOOK)
	cd impl/go && go run . ../../$(BOOK)
	cd impl/cpp && $(MAKE) --no-print-directory run
	cd impl/zig && zig build run -- ../../$(BOOK)
	cd impl/haskell && runghc Parity.hs ../../$(BOOK)
	cd impl/ocaml && dune exec parity -- ../../$(BOOK)
	cd impl/typescript && npx --yes tsx src/parity.ts ../../$(BOOK)

rust:
	cd impl/rust && cargo test

go:
	cd impl/go && go test ./...

cpp:
	cd impl/cpp && $(MAKE) --no-print-directory test

zig:
	cd impl/zig && zig build test

haskell:
	cd impl/haskell && runghc Parity.hs ../../$(BOOK)

ocaml:
	cd impl/ocaml && dune runtest

ts:
	cd impl/typescript && npx --yes tsc --noEmit

clean:
	$(PYTHON) -c "import glob,shutil;[shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)]"
	$(PYTHON) -c "import shutil;shutil.rmtree('runtime/bin',ignore_errors=True);shutil.rmtree('runtime/obj',ignore_errors=True)"
	cd impl/rust && cargo clean || true
	cd impl/zig && rm -rf zig-cache zig-out || true
	cd impl/ocaml && dune clean || true
