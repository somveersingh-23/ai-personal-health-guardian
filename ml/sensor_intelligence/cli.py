"""Command-line entry point for reproducible Member 2 data workflows."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from sensor_intelligence.datasets.capnobase import acquire_capnobase
from sensor_intelligence.datasets.downloader import acquire_dataset
from sensor_intelligence.datasets.ppg_dalia import prepare_cache
from sensor_intelligence.datasets.ptt_ppg import acquire_ptt_ppg
from sensor_intelligence.datasets.registry import DATASETS
from sensor_intelligence.evaluation.benchmark import (
    run_bidmc_external_benchmark,
    run_capnobase_external_respiration_benchmark,
    run_ppg_dalia_benchmark,
    run_ptt_ppg_dual_wavelength_validation,
)
from sensor_intelligence.paths import REPOSITORY_ROOT, data_root
from sensor_intelligence.validation import validate_dataset_contracts


class ProgressReporter:
    def __init__(self) -> None:
        self._last_mib: dict[str, int] = {}

    def __call__(self, resource: str, downloaded: int) -> None:
        mib = downloaded // (1024 * 1024)
        if mib == 0 or mib - self._last_mib.get(resource, -25) >= 25:
            print(f"{resource}: {mib} MiB", flush=True)
            self._last_mib[resource] = mib


def _catalog() -> int:
    payload = {
        key: {
            **asdict(spec),
            "resources": [asdict(resource) for resource in spec.resources],
        }
        for key, spec in DATASETS.items()
    }
    print(json.dumps(payload, indent=2))
    return 0


def _download(dataset: str, accept_dataset_terms: bool) -> int:
    spec = DATASETS[dataset]
    if dataset == "capnobase":
        result = acquire_capnobase(
            data_root(),
            terms_accepted=accept_dataset_terms,
            progress=ProgressReporter(),
        )
    elif dataset == "ptt-ppg":
        result = acquire_ptt_ppg(data_root(), ProgressReporter())
    else:
        result = acquire_dataset(spec, data_root(), ProgressReporter())
    summary = {
        "dataset": result["dataset"],
        "version": result["version"],
        "retrieved_at": result["retrieved_at"],
        "resources": [
            {
                "name": resource["name"],
                "bytes": resource["bytes"],
                "sha256": resource["sha256"],
                "extracted_files": len(resource.get("extracted_files", [])),
            }
            for resource in result["resources"]
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


def _dataset_path(dataset: str) -> str:
    version = DATASETS[dataset].version
    return str(data_root() / "raw" / dataset / version)


def _validate(dataset: str) -> int:
    result = validate_dataset_contracts(dataset, Path(_dataset_path(dataset)))
    print(json.dumps(result, indent=2))
    return 0


def _benchmark(dataset: str, max_windows_per_participant: int | None) -> int:
    source = Path(_dataset_path(dataset))
    output = REPOSITORY_ROOT / "ml" / "reports" / "local"
    if dataset == "ppg-dalia":
        result = run_ppg_dalia_benchmark(source, output, max_windows_per_participant)
    elif dataset == "bidmc":
        result = run_bidmc_external_benchmark(source, output, max_windows_per_participant)
    elif dataset == "capnobase":
        result = run_capnobase_external_respiration_benchmark(
            source, output, max_windows_per_participant
        )
    elif dataset == "ptt-ppg":
        result = run_ptt_ppg_dual_wavelength_validation(
            source, output, max_windows_per_participant
        )
    else:
        raise ValueError(f"{dataset} has no pulse-rate benchmark")
    print(json.dumps(result, indent=2))
    return 0


def _prepare(dataset: str) -> int:
    if dataset != "ppg-dalia":
        raise ValueError(f"{dataset} does not require a processed cache")
    result = prepare_cache(Path(_dataset_path(dataset)))
    print(
        json.dumps(
            {
                "dataset": result["dataset"],
                "schema_version": result["schema_version"],
                "records": len(result["records"]),
                "bytes": sum(record["bytes"] for record in result["records"]),
                "source_archive_sha256": result["source_archive_sha256"],
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="member2-data",
        description="Acquire and validate approved real-signal research datasets.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("catalog", help="Show dataset licences, purposes and limitations")
    download = subcommands.add_parser("download", help="Download one approved dataset")
    download.add_argument("dataset", choices=sorted(DATASETS))
    download.add_argument(
        "--accept-dataset-terms",
        action="store_true",
        help="Confirm review and acceptance of manual dataset terms",
    )
    validate = subcommands.add_parser(
        "validate-contracts", help="Validate real-data adapters against the backend contract"
    )
    validate.add_argument("dataset", choices=["bidmc", "ppg-dalia", "sleep-edf"])
    benchmark = subcommands.add_parser(
        "benchmark", help="Run a participant-held-out real-signal benchmark"
    )
    benchmark.add_argument(
        "dataset", choices=["bidmc", "capnobase", "ppg-dalia", "ptt-ppg"]
    )
    benchmark.add_argument("--max-windows-per-participant", type=int, default=None)
    prepare = subcommands.add_parser(
        "prepare", help="Create minimized verified caches for a downloaded dataset"
    )
    prepare.add_argument("dataset", choices=["ppg-dalia"])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        return _catalog()
    if args.command == "download":
        return _download(args.dataset, args.accept_dataset_terms)
    if args.command == "validate-contracts":
        return _validate(args.dataset)
    if args.command == "benchmark":
        if args.max_windows_per_participant is not None and args.max_windows_per_participant < 1:
            raise ValueError("max windows per participant must be positive")
        return _benchmark(args.dataset, args.max_windows_per_participant)
    if args.command == "prepare":
        return _prepare(args.dataset)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    sys.exit(main())
