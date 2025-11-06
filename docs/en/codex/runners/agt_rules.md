# AGT rule ingestion runner

The `scripts/agt_ingest_rules.py` command rebuilds `rules_updates/agt/index.json` from the official AGT material stored under `rules_updates/agt/`. Tooling that consumes SAF-T (AO) validation rules should always read constraints through `lib.validators.rules_loader` to guarantee consistency with the single source of truth.

```bash
python scripts/agt_ingest_rules.py --rebuild --verbose
```

The script also refreshes:

- `docs/en/agt/agt_rules_summary.md` with a human-readable snapshot of the current sources and rules.
- `docs/en/agt/agt_rules_changelog.md` with a running audit log.

For CI integration use the GitHub workflow defined in `.github/workflows/agt-rules-sync.yml`.
