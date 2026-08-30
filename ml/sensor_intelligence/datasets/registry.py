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
