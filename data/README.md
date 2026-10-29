# Data directory

**All subdirectories are empty on purpose. There is no Sindhi or Urdu data in this
repository.** An empty directory is not a dataset; scripts that need real data raise
`DataUnavailableError` and never substitute synthetic data.

| Directory | Intended content | Status |
|---|---|---|
| `raw/` | Original corpora exactly as obtained (UTF-8), plus a `SOURCE.md` per corpus with URL, licence, retrieval date and SHA-256 | empty |
| `processed/` | Derived files (e.g. deduplicated lines); every file must be reproducible from `raw/` by a committed script | empty |
| `gold/` | Manually reviewed boundary annotations (`<lang>_gold.tsv`, format in `audit/sampling_protocol.md`); dev and test kept apart | empty |
| `audit/` | Completed ZWNJ annotation sheets and adjudication records | empty |

The only data that ships is the **synthetic** integration-test fixture in
`tests/fixtures/synthetic/` (artificial Latin-letter tokens; not a language).

To add a corpus: place it in `raw/`, record provenance in `raw/SOURCE.md`, set
`corpus.path` and `corpus.licence` in `configs/data/<lang>.yaml`, and run
`make gate0 DATA=<lang>`. Large or licence-restricted files should not be committed;
`.gitignore` excludes `data/raw/*` and `data/processed/*` except the README files.
