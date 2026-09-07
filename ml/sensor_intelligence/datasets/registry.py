"""Auditable registry of approved Member 2 research datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AccessMode = Literal["automatic", "manual"]


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    name: str
    url: str
    relative_path: str
    expected_sha256: str | None = None
    expected_md5: str | None = None
    extract_zip: bool = False
    max_download_bytes: int = 512 * 1024 * 1024
    max_uncompressed_bytes: int = 1024 * 1024 * 1024
    max_archive_members: int = 10_000
    inspect_nested_zip_paths: tuple[str, ...] = ()
    max_nested_uncompressed_bytes: int = 1024 * 1024 * 1024
    expected_nested_sha256: tuple[tuple[str, str], ...] = ()
    extract_directory_name: str = "extracted"
    strip_single_archive_root: bool = False


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    key: str
    title: str
    version: str
    homepage: str
    license_name: str
    license_url: str
    citation: str
    access_mode: AccessMode
    purpose: str
    limitations: tuple[str, ...]
    resources: tuple[ResourceSpec, ...] = ()


DATASETS: dict[str, DatasetSpec] = {
    "capnobase": DatasetSpec(
        key="capnobase",
        title="CapnoBase IEEE TBME Respiratory Rate Benchmark",
        version="1.1",
        homepage="https://doi.org/10.5683/SP2/NLB8IT",
        license_name="Borealis Dataverse custom research terms",
        license_url="https://doi.org/10.5683/SP2/NLB8IT",
        citation="Karlen et al., IEEE TBME 2013; CapnoBase DOI 10.5683/SP2/NLB8IT",
        access_mode="manual",
        purpose="Untuned external validation of respiratory rate derived from PPG",
        limitations=(
            "Benchmark-only dataset: it must not be used to train or tune the algorithm",
            "Research terms prohibit attempts to identify or link participants",
            "Anaesthesia recordings are not representative of a consumer wrist wearable",
        ),
    ),
    "bidmc": DatasetSpec(
        key="bidmc",
        title="BIDMC PPG and Respiration Dataset",
        version="1.0.0",
        homepage="https://physionet.org/content/bidmc/1.0.0/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Pimentel et al., IEEE TBME 2016; PhysioNet DOI 10.13026/C2208R",
        access_mode="automatic",
        purpose="PPG/ECG/respiration waveform SQI and HR/RR/SpO2 numeric validation",
        limitations=(
            "53 short ICU recordings are not representative of consumer wearable users",
            "SpO2 has no raw red/infrared channels, so oxygen saturation cannot be re-estimated",
        ),
        resources=(
            ResourceSpec(
                name="bidmc-archive",
                url="https://physionet.org/content/bidmc/get-zip/1.0.0/",
                relative_path="raw/bidmc/1.0.0/bidmc.zip",
                expected_sha256=(
                    "7c09847e8b9c9ad0005ad6f4041e887119e2ad9a745b6a63b1b394bd439f693b"
                ),
                extract_zip=True,
                max_download_bytes=300 * 1024 * 1024,
                max_uncompressed_bytes=500 * 1024 * 1024,
            ),
        ),
    ),
    "bami1": DatasetSpec(
        key="bami1",
        title="BAMI1 Watch-Type PPG Motion-Artifact Dataset",
        version="repository snapshot",
        homepage="https://github.com/hooseok/BAMI1",
        license_name=(
            "Copyright retained; academic research use with suitable citation stated by publisher"
        ),
        license_url="https://github.com/hooseok/BAMI1",
        citation="Lee, Chung & Lee; cite the publisher's linked paper and dataset acknowledgement",
        access_mode="manual",
        purpose=(
            "Future motion-artifact robustness experiment using multi-channel green PPG, "
            "accelerometer and gyroscope."
        ),
        limitations=(
            "The repository's stated permission is academic-research use with citation, "
            "not a general open-data licence.",
            "Twenty-four healthy subjects performed a short treadmill protocol; it is not "
            "free-living or clinical validation.",
            "Do not assume raw ECG is distributed: verify exact files and reference-HR "
            "format before adapter work.",
        ),
    ),
    "bami2": DatasetSpec(
        key="bami2",
        title="BAMI2 Watch-Type PPG Motion-Artifact Dataset",
        version="repository snapshot",
        homepage="https://github.com/hooseok/BAMI2",
        license_name=(
            "Copyright retained; academic research use with suitable citation stated by publisher"
        ),
        license_url="https://github.com/hooseok/BAMI2",
        citation="Lee, Chung & Lee; cite the publisher's linked paper and dataset acknowledgement",
        access_mode="manual",
        purpose=(
            "Future held-out motion-artifact robustness experiment with PPG, accelerometer, "
            "gyroscope and ECG-derived HR reference."
        ),
        limitations=(
            "The repository's stated permission is academic-research use with citation, "
            "not a general open-data licence.",
            "Twenty-three healthy subjects performed a short treadmill protocol; it is not "
            "free-living or clinical validation.",
            "Do not assume raw ECG is distributed: verify exact files and reference-HR "
            "format before adapter work.",
        ),
    ),
    "bigideaslab-step": DatasetSpec(
        key="bigideaslab-step",
        title="BigIdeasLab STEP Smartwatch Heart-Rate Dataset",
        version="1.0",
        homepage="https://physionet.org/content/bigideaslab-step-hr-smartwatch/1.0/",
        license_name="PhysioNet Restricted Health Data License 1.5.0",
        license_url="https://physionet.org/content/bigideaslab-step-hr-smartwatch/1.0/",
        citation="Bent & Dunn (2021), PhysioNet DOI 10.13026/cqfy-d860",
        access_mode="manual",
        purpose="Future device, activity, and skin-tone subgroup error audit against ECG HR",
        limitations=(
            "Access requires a registered PhysioNet account and the dataset use agreement",
            "It contains device-reported HR, not raw PPG or a generalizable clinical label",
            "Historical devices, firmware, and collection dates cannot validate current models",
        ),
    ),
    "ppg-dalia": DatasetSpec(
        key="ppg-dalia",
        title="PPG-DaLiA",
        version="1.0",
        homepage="https://archive.ics.uci.edu/dataset/495/ppg%2Bdalia",
        license_name="Creative Commons Attribution 4.0 International",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        citation="Reiss, Indlekofer & Schmidt (2019), UCI DOI 10.24432/C53890",
        access_mode="automatic",
        purpose="Daily-life wrist PPG motion compensation with ECG-derived HR ground truth",
        limitations=(
            "Only 15 participants; evaluation must split by participant",
            "ECG-derived heart-rate labels support estimation research, not disease diagnosis",
        ),
        resources=(
            ResourceSpec(
                name="ppg-dalia-archive",
                url="https://archive.ics.uci.edu/static/public/495/ppg+dalia.zip",
                relative_path="raw/ppg-dalia/1.0/ppg-dalia.zip",
                expected_sha256=(
                    "5772387956e34e2e2dc4c2ddbeb98cb70569d5112fa4c13ee98a17680b84a1f3"
                ),
                extract_zip=True,
                max_download_bytes=4 * 1024 * 1024 * 1024,
                max_uncompressed_bytes=10 * 1024 * 1024 * 1024,
                max_archive_members=5_000,
                inspect_nested_zip_paths=("data.zip",),
                max_nested_uncompressed_bytes=30 * 1024 * 1024 * 1024,
                expected_nested_sha256=(
                    (
                        "data.zip",
                        "fcda4d13f6475e88a24f1ef9658627dc98e04dd5c5dd790cd2b0a1a22e31913b",
                    ),
                ),
            ),
        ),
    ),
    "ptt-ppg": DatasetSpec(
        key="ptt-ppg",
        title="Pulse Transit Time PPG Dataset",
        version="1.1.0",
        homepage="https://physionet.org/content/pulse-transit-time-ppg/1.1.0/",
        license_name="Open Data Commons Open Database License 1.0",
        license_url="https://opendatacommons.org/licenses/odbl/1-0/",
        citation="Harte et al. (2021), PhysioNet DOI 10.13026/55GC-A611",
        access_mode="automatic",
        purpose="Real paired optical PPG channel and ratio-feature validation",
        limitations=(
            "Spot SpO2 values occur only at recording boundaries and are not continuous labels",
            "Healthy-subject values are narrow and cannot validate hypoxaemia accuracy",
            "This dataset validates signal plumbing only; it cannot authorize a product SpO2 claim",
            "Publisher documentation conflicts on which paired channel is red versus infrared",
        ),
    ),
    "sleep-edf": DatasetSpec(
        key="sleep-edf",
        title="Sleep-EDF Database Expanded (curated validation pair)",
        version="1.0.0",
        homepage="https://physionet.org/content/sleep-edfx/1.0.0/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Kemp et al. (2000); PhysioNet DOI 10.13026/C2X676",
        access_mode="automatic",
        purpose="Expert-scored sleep-stage/session conversion validation",
        limitations=(
            "The curated pair validates conversion but does not train a general sleep-stage model",
            "Legacy R&K stage labels require an explicit mapping to the product taxonomy",
        ),
        resources=(
            ResourceSpec(
                name="sleep-edf-psg-sc4001e0",
                url=(
                    "https://physionet.org/files/sleep-edfx/1.0.0/"
                    "sleep-cassette/SC4001E0-PSG.edf"
                ),
                relative_path="raw/sleep-edf/1.0.0/SC4001E0-PSG.edf",
                expected_sha256=(
                    "2b40a18adf76af69a42d6db1f30f31d26b369f6d27ca0050ef30147ef892b131"
                ),
                max_download_bytes=60 * 1024 * 1024,
            ),
            ResourceSpec(
                name="sleep-edf-hypnogram-sc4001ec",
                url=(
                    "https://physionet.org/files/sleep-edfx/1.0.0/"
                    "sleep-cassette/SC4001EC-Hypnogram.edf"
                ),
                relative_path="raw/sleep-edf/1.0.0/SC4001EC-Hypnogram.edf",
                expected_sha256=(
                    "a4cf67694ade1b52a0ddd06d5817fd45d2d3e8bac5302f640f3e9cfbbf12a996"
                ),
                max_download_bytes=1024 * 1024,
            ),
        ),
    ),
    "wearanize-plus-oa": DatasetSpec(
        key="wearanize-plus-oa",
        title="Wearanize+ Open-Access Multimodal Sleep Dataset",
        version="v1.1 OA",
        homepage="https://github.com/Niloy333/Wearanize_plus",
        license_name=(
            "Scientific-research-only terms; no re-identification "
            "(source-specific open-access collection)"
        ),
        license_url="https://github.com/Niloy333/Wearanize_plus",
        citation="Wearanize+ dataset and its reference paper; use the source's requested citation",
        access_mode="manual",
        purpose=(
            "Future device-specific offline sleep-session and missing/corrupted-data "
            "robustness research against PSG labels."
        ),
        limitations=(
            "The repository's MIT licence covers repository code, not a blanket licence for "
            "participant data.",
            "The open-access collection excludes questionnaires; scientific-research-only "
            "and no-re-identification conditions apply.",
            "It supports offline research only, never a production or PSG-equivalent "
            "sleep-stage claim.",
        ),
    ),
    "sleep-accel": DatasetSpec(
        key="sleep-accel",
        title="Motion and Heart Rate from a Wrist-Worn Wearable and PSG Sleep Labels",
        version="1.0.0",
        homepage="https://physionet.org/content/sleep-accel/1.0.0/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Walch et al. (2019), PhysioNet DOI 10.13026/hmhs-py35",
        access_mode="automatic",
        purpose="External Apple Watch HR/motion/steps and PSG-labelled sleep session validation",
        limitations=(
            "Only 31 released participants; hold every participant out of any tuning split",
            "PSG labels validate offline session conversion, not a production sleep-stage claim",
            "Apple Watch collection and labels are historical and not Android Health Connect data",
        ),
        resources=(
            ResourceSpec(
                name="sleep-accel-archive",
                url="https://physionet.org/content/sleep-accel/get-zip/1.0.0/",
                relative_path="raw/sleep-accel/1.0.0/sleep-accel.zip",
                extract_zip=True,
                max_download_bytes=700 * 1024 * 1024,
                max_uncompressed_bytes=3 * 1024 * 1024 * 1024,
                max_archive_members=10_000,
            ),
        ),
    ),
    "bidsleep": DatasetSpec(
        key="bidsleep",
        title="BIDSleep: Multi-Night Apple Watch HR, Motion, and Sleep Labels",
        version="1.0.0",
        homepage="https://physionet.org/content/bidsleep-dataset/1.0.0/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Song et al. (2026), PhysioNet DOI 10.13026/a0sy-7t69",
        access_mode="manual",
        purpose=(
            "Future multi-night Apple Watch HR/motion and sleep-label external research "
            "validation."
        ),
        limitations=(
            "The 5.9 GB archive (27.9 GB uncompressed) needs selective, participant-safe "
            "acquisition rather than an automatic full download.",
            "The labels are Dreem-device annotations, not a basis for a clinical or "
            "PSG-equivalence product claim.",
            "Historical Apple Watch/HealthKit data does not validate Android or all OEM devices.",
        ),
    ),
    "dreamt": DatasetSpec(
        key="dreamt",
        title="DREAMT: Multisensor Wearable Sleep Dataset",
        version="2.2.0",
        homepage="https://physionet.org/content/dreamt/2.2.0/",
        license_name="PhysioNet Restricted Health Data License 1.5.0",
        license_url="https://physionet.org/content/dreamt/2.2.0/",
        citation="Wang et al. (2026), PhysioNet DOI 10.13026/3f7y-2d80",
        access_mode="manual",
        purpose="Future approved multisensor sleep research only.",
        limitations=(
            "Requires a registered PhysioNet account and signed data-use agreement.",
            "Never download automatically or store access credentials in this project.",
            "Do not make a clinical sleep-disorder or PSG-equivalence claim from this source.",
        ),
    ),
    "scientisst-move": DatasetSpec(
        key="scientisst-move",
        title="ScientISST MOVE Multimodal Everyday-Activity Biosignals",
        version="1.0.1",
        homepage="https://physionet.org/content/scientisst-move-biosignals/1.0.1/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Areias Saraiva et al. (2024), PhysioNet DOI 10.13026/hyxq-r919",
        access_mode="automatic",
        purpose=(
            "External PPG/ECG/actigraphy/temperature signal-quality research during "
            "annotated everyday movement."
        ),
        limitations=(
            "Seventeen healthy volunteers and roughly 37 synchronized minutes each are "
            "insufficient for a broad wearable claim.",
            "Use its chest ECG only as a pulse-rate reference; do not use it for diagnosis.",
            "A source-specific adapter and participant-disjoint evaluation are required."
        ),
        resources=(
            ResourceSpec(
                name="scientisst-move-archive",
                url="https://physionet.org/content/scientisst-move-biosignals/get-zip/1.0.1/",
                relative_path="raw/scientisst-move/1.0.1/scientisst-move.zip",
                extract_zip=True,
                max_download_bytes=250 * 1024 * 1024,
                max_uncompressed_bytes=600 * 1024 * 1024,
                max_archive_members=10_000,
            ),
        ),
    ),
    "senssmarttech": DatasetSpec(
        key="senssmarttech",
        title="SensSmartTech Synchronous Cardiovascular Waveforms",
        version="1.0.0",
        homepage="https://physionet.org/content/senssmarttech/1.0.0/",
        license_name="Creative Commons Attribution 4.0 International",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        citation="SensSmartTech (2024), PhysioNet DOI 10.13026/fy9p-n277",
        access_mode="automatic",
        purpose=(
            "External PPG/ECG/accelerometer synchronization and signal-integrity "
            "research validation."
        ),
        limitations=(
            "Its recording protocol and participant characteristics must be checked before "
            "any performance claim.",
            "It validates waveform handling and HR research, not consumer-device clinical use.",
            "A source-specific adapter and participant-disjoint evaluation are required."
        ),
        resources=(
            ResourceSpec(
                name="senssmarttech-archive",
                url="https://physionet.org/content/senssmarttech/get-zip/1.0.0/",
                relative_path="raw/senssmarttech/1.0.0/senssmarttech.zip",
                extract_zip=True,
                max_download_bytes=350 * 1024 * 1024,
                max_uncompressed_bytes=1024 * 1024 * 1024,
                max_archive_members=20_000,
                extract_directory_name="x",
                strip_single_archive_root=True,
            ),
        ),
    ),
    "all-of-us-fitbit": DatasetSpec(
        key="all-of-us-fitbit",
        title="All of Us Research Program Fitbit Data",
        version="access-controlled",
        homepage="https://support.researchallofus.org/hc/en-us/articles/20281023493908-Resources-for-Using-Fitbit-Data",
        license_name="All of Us Researcher Workbench access controls and data-use agreement",
        license_url="https://www.researchallofus.org/data-tools/data-access/",
        citation="All of Us Research Program, Fitbit data resources",
        access_mode="manual",
        purpose="Future approved longitudinal baseline research under an institutional protocol",
        limitations=(
            "No credentials, participant data, queries, exports, or access tokens are stored here",
            "Access requires the program's current registration, training, and data-use conditions",
            "This is not an MVP dataset and cannot be silently substituted for public data",
        ),
    ),
    "wrist-exercise": DatasetSpec(
        key="wrist-exercise",
        title="Wrist PPG During Exercise",
        version="1.0.0",
        homepage="https://physionet.org/content/wrist/1.0.0/",
        license_name="Open Data Commons Attribution License 1.0",
        license_url="https://opendatacommons.org/licenses/by/1-0/",
        citation="Jarchi & Casson (2017), PhysioNet DOI 10.13026/C2PQ1X",
        access_mode="automatic",
        purpose="External wrist PPG, IMU motion, and ECG R-peak heart-rate quality validation",
        limitations=(
            "Only eight participants and short controlled exercise recordings",
            "Cycling PPG was publisher-filtered before WFDB conversion",
            "Use for signal-quality research, not disease, diagnostic, or medical-device claims",
        ),
        resources=(
            ResourceSpec(
                name="wrist-exercise-archive",
                url="https://physionet.org/content/wrist/get-zip/1.0.0/",
                relative_path="raw/wrist-exercise/1.0.0/wrist-exercise.zip",
                extract_zip=True,
                max_download_bytes=100 * 1024 * 1024,
                max_uncompressed_bytes=100 * 1024 * 1024,
                max_archive_members=1_000,
            ),
        ),
    ),
    "wesad": DatasetSpec(
        key="wesad",
        title="WESAD (Wearable Stress and Affect Detection)",
        version="1.0",
        homepage="https://archive.ics.uci.edu/dataset/465/wesad",
        license_name="See original dataset acknowledgement policy",
        license_url="https://archive.ics.uci.edu/dataset/465/wesad",
        citation="Schmidt & Reiss (2018), UCI DOI 10.24432/C57K5T",
        access_mode="manual",
        purpose="Optional wrist/chest multimodal research after licence acknowledgement",
        limitations=(
            "Manual acknowledgement is required before acquisition",
            "Stress/affect labels are not disease labels and are outside the MVP claim set",
        ),
    ),
}
