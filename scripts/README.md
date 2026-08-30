# Repository Scripts

Run these scripts from any working directory; each resolves the repository root from its own location.

| Script | Purpose | Side effects |
|---|---|---|
| `verify-member2.ps1` | Ruff, compile, ML/backend pytest coverage gates, Android JVM tests and lint | Writes ignored caches, coverage, and Android build output |
| `verify-docker-runtime.ps1` | Validates Compose, builds an isolated stack, checks Alembic/table/API health | Creates temporary containers/volume and removes them unless `-KeepContainers` is supplied |
| `download-member2-data.ps1 <dataset>` | Invokes the governed dataset registry/downloader | Downloads potentially large raw data under ignored `data/`; requires prior terms/licence review |
| `validate-member2-device-evidence.py <file>` | Validates device evidence structure and rejects sensitive field names | Read-only; `--require-complete` fails any non-passed release record |
| `validate-doc-links.py [repository-root]` | Validates every local Markdown file/directory link and rejects repository escapes | Read-only; included in local verification and CI |

Examples:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-member2.ps1
powershell -ExecutionPolicy Bypass -File scripts\verify-docker-runtime.ps1
powershell -ExecutionPolicy Bypass -File scripts\download-member2-data.ps1 bidmc
```

Dataset identifiers, source URLs, fingerprints, licenses, and interpretation limits are documented in `docs/research/MEMBER2_DATASETS.md`. Scripts must never print or commit secrets or identifiable health records.
