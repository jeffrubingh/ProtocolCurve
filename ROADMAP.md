# Roadmap

## Now

- Keep the seven ports green against the reference fingerprint.
- Harden the lenient book reader against partial batches.

## Next

- Streaming ingest so a book larger than memory can be scored.
- Per-band ceilings instead of one global ceiling.
- Reserve provenance export for external auditors.

## Later

- Multi-asset reserves with a per-asset rate table.
- Historical depth snapshots and drift detection between epochs.
- Read-only HTTP surface over the same engine, no new logic.

## Not planned

- A database. The book is text and stays text.
- A web dashboard in this repo.
