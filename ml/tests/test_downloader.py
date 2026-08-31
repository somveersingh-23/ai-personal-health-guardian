from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from sensor_intelligence.datasets.downloader import (
    acquire_dataset,
    download_resource,
    safe_extract_zip,
    verify_embedded_sha256sums,
)
from sensor_intelligence.datasets.registry import DatasetSpec, ResourceSpec


def test_existing_resource_is_checksum_verified(tmp_path: Path) -> None:
    content = b"approved research bytes"
    destination = tmp_path / "raw" / "sample.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(content)
    resource = ResourceSpec(
        name="sample",
        url="https://example.invalid/sample.bin",
        relative_path="raw/sample.bin",
        expected_sha256=hashlib.sha256(content).hexdigest(),
    )

    result = download_resource(resource, tmp_path)

    assert result["bytes"] == len(content)


def test_existing_resource_is_publisher_md5_verified(tmp_path: Path) -> None:
    content = b"publisher checked bytes"
    destination = tmp_path / "raw" / "sample.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(content)
    resource = ResourceSpec(
        name="sample",
        url="https://example.invalid/sample.bin",
        relative_path="raw/sample.bin",
        expected_md5=hashlib.md5(content, usedforsecurity=False).hexdigest(),
    )

    result = download_resource(resource, tmp_path)

    assert result["publisher_md5"] == resource.expected_md5

    destination.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="publisher MD5 mismatch"):
        download_resource(resource, tmp_path)


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.txt", "blocked")

    with pytest.raises(ValueError, match="escapes"):
        safe_extract_zip(
            archive,
            tmp_path / "extracted",
            tmp_path,
            max_uncompressed_bytes=1024,
            max_members=10,
        )


def test_zip_bomb_declared_size_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("large.txt", "a" * 2_000)

    with pytest.raises(ValueError, match="uncompressed size"):
        safe_extract_zip(
            archive,
            tmp_path / "extracted",
            tmp_path,
            max_uncompressed_bytes=1_000,
            max_members=10,
        )


def test_publisher_checksum_manifest_is_verified(tmp_path: Path) -> None:
    content = b"publisher controlled data"
    (tmp_path / "record.bin").write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    (tmp_path / "SHA256SUMS.txt").write_text(
        f"{digest}  record.bin\n", encoding="utf-8"
    )

    assert verify_embedded_sha256sums(tmp_path) == 1

    (tmp_path / "record.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="mismatch"):
        verify_embedded_sha256sums(tmp_path)


def test_acquisition_verifies_pinned_nested_archive_and_writes_manifest(tmp_path: Path) -> None:
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("signal.bin", b"approved-signal")
    inner_bytes = inner.read_bytes()
    inner_sha256 = hashlib.sha256(inner_bytes).hexdigest()

    archive = tmp_path / "raw" / "sample.zip"
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        bundle.writestr("data.zip", inner_bytes)
    archive_sha256 = hashlib.sha256(archive.read_bytes()).hexdigest()

    resource = ResourceSpec(
        name="sample-archive",
        url="https://example.invalid/sample.zip",
        relative_path="raw/sample.zip",
        expected_sha256=archive_sha256,
        extract_zip=True,
        max_download_bytes=10_000,
        max_uncompressed_bytes=10_000,
        max_archive_members=10,
        inspect_nested_zip_paths=("data.zip",),
        max_nested_uncompressed_bytes=1_000,
        expected_nested_sha256=(("data.zip", inner_sha256),),
    )
    dataset = DatasetSpec(
        key="sample",
        title="Sample",
        version="1.0",
        homepage="https://example.invalid",
        license_name="Test only",
        license_url="https://example.invalid/license",
        citation="Test fixture",
        access_mode="automatic",
        purpose="test",
        limitations=("not real data",),
        resources=(resource,),
    )

    result = acquire_dataset(dataset, tmp_path)

    nested = result["resources"][0]["nested_archives"][0]
    assert nested["sha256"] == inner_sha256
    assert nested["members"] == 1
    assert (tmp_path / "manifests" / "sample-1.0.json").is_file()


def test_manual_access_dataset_is_never_downloaded(tmp_path: Path) -> None:
    dataset = DatasetSpec(
        key="manual",
        title="Manual",
        version="1.0",
        homepage="https://example.invalid",
        license_name="Manual terms",
        license_url="https://example.invalid/license",
        citation="Test fixture",
        access_mode="manual",
        purpose="test",
        limitations=("manual acknowledgement",),
    )

    with pytest.raises(PermissionError, match="manual licence acknowledgement"):
        acquire_dataset(dataset, tmp_path)
