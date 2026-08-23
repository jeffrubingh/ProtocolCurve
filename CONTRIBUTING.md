# Contributing

## Ground rules

1. The money path is integer. A pull request that introduces a float into
   `curve.py` or any port is rejected.
2. A behaviour change lands in the Python engine first, with a test, and then in
   every port in the same pull request.
3. No port may add a dependency the others do not have.
4. The fingerprint is a contract. If it changes on purpose, update
   `tests/test_parity.py` and `docs/PORTS.md` together and say why.

## Local checks
Both must pass before you open a pull request. `scripts/parity.sh` skipping a
language because its compiler is missing is fine locally; CI runs all of them.

## Style

- Standard library only in Python, four space indent, type hints on public
  functions.
- Tests are named for the behaviour, not the function.
- Commit messages are imperative and one line.
