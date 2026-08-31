# Member 2 Real-Signal Dataset Register

Research and access details were verified against the authoritative dataset pages through 2026-08-30. Raw files are downloaded to the Git-ignored `data/` directory or the external `HEALTH_GUARDIAN_DATA_ROOT` and must never be committed, attached to a pull request, copied into logs, or uploaded as a CI artifact.

## Approved sources

| Dataset | Signals and reference | Approved use | Access and licence | Important limitation |
|---|---|---|---|---|
| [BIDMC PPG and Respiration v1.0.0](https://physionet.org/content/bidmc/1.0.0/) | 53 eight-minute critical-care recordings; PPG, respiration and ECG at 125 Hz; HR, RR and SpO2 at 1 Hz; manual breaths | External PPG/pulse-rate sanity check, respiration research, numeric contract validation | Automatic; Open Data Commons Attribution 1.0 | ICU pulse-oximeter data is not a proxy for consumer wrist wearables. No raw red/infrared channels exist, so SpO2 must not be estimated from it. |
| [CapnoBase v1.1](https://doi.org/10.5683/SP2/NLB8IT) | 42 eight-minute anaesthesia cases; PPG and capnography-derived RR reference | Frozen external PPG respiratory-rate benchmark only | Explicit terms acknowledgement; Borealis custom research terms | Must not be used for training/tuning or participant identification/linkage. Anaesthesia data is not consumer-wearable validation. |
| [PhysioNet PTT-PPG v1.1.0](https://physionet.org/content/pulse-transit-time-ppg/1.1.0/) | 22 healthy participants, 66 sit/walk/run recordings; two sensors each with paired red/infrared plus green PPG at 500 Hz; boundary spot SpO2 | Paired-channel, ratio-feature, motion/activity and abstention validation | Automatic; ODbL 1.0 | The README conflicts on red/infrared channel order. Spot SpO2 is narrow (94-99%), boundary-only and not a synchronized arterial label; neither mapping nor labels support calibration. |
| [PPG-DaLiA](https://archive.ics.uci.edu/dataset/495/ppg%2Bdalia) | 15 participants; wrist BVP 64 Hz, three-axis accelerometer 32 Hz, temperature 4 Hz; ECG-derived HR labels | Primary daily-life motion-aware PPG quality and pulse-rate benchmark | Automatic; CC BY 4.0 | Small cohort. All windows from a participant must remain in one split. It does not support a disease claim. |
| [Sleep-EDF Expanded v1.0.0](https://physionet.org/content/sleep-edfx/1.0.0/) | Whole-night polysomnography with expert hypnograms | Curated annotation-to-session contract validation | Automatic curated pair; Open Data Commons Attribution 1.0 | One curated pair validates conversion, not a general sleep staging model. Legacy R&K labels are mapped explicitly. |
| [WESAD](https://archive.ics.uci.edu/dataset/465/wesad) | Chest/wrist ECG, BVP, EDA, respiration, temperature and motion from 15 subjects | Optional future multimodal experiment | Manual opt-in only; follow the original acknowledgement/licence terms | Stress/affect labels are not diagnoses and are outside the current product claim. |

The BIDMC CSV release contains isolated out-of-order manual-breath sample indices in four recordings. The adapter sorts and deduplicates annotator indices for time-window evaluation and records the correction count in each research record's provenance; it never alters waveform or monitor values.

## Acquisition and integrity

Run from the repository root with the isolated Python 3.12 environment:

```powershell
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli catalog
scripts\download-member2-data.ps1 bidmc
scripts\download-member2-data.ps1 ppg-dalia
scripts\download-member2-data.ps1 sleep-edf
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli download capnobase --accept-dataset-terms
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli download ptt-ppg
ml\.venv\Scripts\python.exe -m sensor_intelligence.cli prepare ppg-dalia
```

The downloader:

- accepts URLs only from the code-reviewed registry;
- resumes partial downloads and writes atomically;
- uses bounded retry/backoff for transient source or signed-redirect failures;
- records byte count, SHA-256, source URL, retrieval time, version, licence and citation;
- caps compressed/uncompressed sizes and archive member counts;
- rejects traversal paths, duplicate targets, encrypted members and symbolic links;
- inspects the 24.1 GB uncompressed PPG-DaLiA inner archive without expanding its unused chest/device duplicates, and streams only the approved synchronized participant records;
- writes a local provenance manifest under `data/manifests/`.
- pins CapnoBase's selected metadata manifest and verifies each publisher MD5, and selectively downloads PTT-PPG WFDB files while verifying every official SHA-256.

Pinned archive hashes belong in `ml/sensor_intelligence/datasets/registry.py` after the first independently verified acquisition. PhysioNet's included `SHA256SUMS.txt` is also checked during dataset verification.

## Data governance

- Dataset time is treated as dataset-relative unless a source explicitly establishes clinical time. Synthetic UTC anchors are labelled `relative_anchored_not_clinical`.
- Only derived features, adapter code, citations, manifests without participant measurements, and aggregate metrics may leave the ignored data directory.
- No raw PPG, ECG, image, EDF, participant pickle, health event, or participant-level prediction goes to Git or ordinary application logs.
- Public/de-identified research data does not remove the need to comply with its licence, attribution, intended-use limits, and project governance.
- These datasets validate engineering behavior. They do not constitute prospective clinical validation, regulatory clearance, or proof of emergency detection.
