# Member 2 real-signal validation

This package contains licence-aware acquisition, real-dataset adapters, transparent PPG/motion features, participant-held-out evaluation and production-contract validation. Raw datasets and local reports are ignored by Git.

It also includes a frozen external PPG respiratory-rate benchmark (CapnoBase) and real paired optical-channel validation (PhysioNet PTT-PPG). The PTT-PPG publisher documentation conflicts on red/infrared ordering, so its ratios remain wavelength-neutral. SpO2 feature extraction requires paired channels and numeric estimation requires verified wavelength mapping plus explicit device calibration; no universal or fabricated calibration is provided.

PPG-DaLiA's official outer package contains a 24.1 GB uncompressed inner archive. The downloader validates and fingerprints that archive but intentionally does not expand it; the adapter streams the synchronized S1-S15 pickle members directly and ignores unused duplicate chest/device files.

Use Python 3.12:

```powershell
py -3.12 -m venv ml\.venv
ml\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt
$env:PYTHONPATH = "ml;backend"
ml\.venv\Scripts\python.exe -m pytest ml\tests
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli catalog
```

See `docs/research/MEMBER2_DATASETS.md`, `docs/testing/MEMBER2_REAL_DATA_PROTOCOL.md` and `docs/research/PPG_QUALITY_MODEL_CARD.md` before downloading or interpreting results.
