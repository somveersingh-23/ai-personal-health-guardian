"""Resumable, checksum-aware and traversal-safe public-data acquisition."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sensor_intelligence.datasets.registry import DatasetSpec, ResourceSpec
from sensor_intelligence.paths import require_within

CHUNK_BYTES = 1024 * 1024
USER_AGENT = "AI-Personal-Health-Guardian-Research/0.1"
MAX_OPEN_ATTEMPTS = 4


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    """Return MD5 only for publisher integrity metadata, never for security."""

    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_resource_checksums(resource: ResourceSpec, path: Path) -> tuple[str, str | None]:
    sha256 = sha256_file(path)
    md5 = md5_file(path) if resource.expected_md5 else None
    if resource.expected_sha256 and sha256.lower() != resource.expected_sha256.lower():
        raise ValueError(f"checksum mismatch for {resource.name}")
    if resource.expected_md5 and md5 != resource.expected_md5.lower():
        raise ValueError(f"publisher MD5 mismatch for {resource.name}")
    return sha256, md5


def _open_with_retry(request: urllib.request.Request) -> object:
    """Open an approved resource with bounded retry for transient redirect failures."""

    for attempt in range(MAX_OPEN_ATTEMPTS):
        try:
            return urllib.request.urlopen(request, timeout=120)  # noqa: S310
        except urllib.error.HTTPError as exc:
            retryable = exc.code in {400, 408, 425, 429} or exc.code >= 500
            if not retryable or attempt + 1 == MAX_OPEN_ATTEMPTS:
                raise
        except urllib.error.URLError:
            if attempt + 1 == MAX_OPEN_ATTEMPTS:
                raise
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def download_resource(
    resource: ResourceSpec,
    root: Path,
    progress: Callable[[int], None] | None = None,
) -> dict[str, object]:
    destination = require_within(root, root / resource.relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = require_within(root, destination.with_suffix(destination.suffix + ".part"))
    if destination.exists():
        if destination.stat().st_size > resource.max_download_bytes:
            raise ValueError(f"existing {resource.name} exceeds configured size limit")
        actual, publisher_md5 = _verify_resource_checksums(resource, destination)
        result: dict[str, object] = {
            "path": str(destination),
            "sha256": actual,
            "bytes": destination.stat().st_size,
        }
        if publisher_md5:
            result["publisher_md5"] = publisher_md5
        return result

    resume_at = partial.stat().st_size if partial.exists() else 0
    if resume_at > resource.max_download_bytes:
        raise ValueError(f"partial {resource.name} exceeds configured size limit")
    request = urllib.request.Request(resource.url, headers={"User-Agent": USER_AGENT})
    if resume_at:
        request.add_header("Range", f"bytes={resume_at}-")
    with _open_with_retry(request) as response:
        append = resume_at > 0 and getattr(response, "status", None) == 206
        mode = "ab" if append else "wb"
        downloaded = resume_at if append else 0
        response_length = response.headers.get("Content-Length")
        if response_length and downloaded + int(response_length) > resource.max_download_bytes:
            raise ValueError(f"declared size for {resource.name} exceeds configured limit")
        with partial.open(mode) as handle:
            while chunk := response.read(CHUNK_BYTES):
                handle.write(chunk)
                downloaded += len(chunk)
                if downloaded > resource.max_download_bytes:
                    raise ValueError(f"downloaded {resource.name} exceeds configured size limit")
                if progress:
                    progress(downloaded)
            handle.flush()
            os.fsync(handle.fileno())
    partial.replace(destination)
    actual, publisher_md5 = _verify_resource_checksums(resource, destination)
    result = {"path": str(destination), "sha256": actual, "bytes": destination.stat().st_size}
    if publisher_md5:
        result["publisher_md5"] = publisher_md5
    return result


def safe_extract_zip(
    archive: Path,
    destination: Path,
    root: Path,
    *,
    max_uncompressed_bytes: int,
    max_members: int,
) -> list[str]:
    resolved_destination = require_within(root, destination)
    resolved_destination.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > max_members:
            raise ValueError("dataset archive contains too many members")
        if sum(member.file_size for member in members) > max_uncompressed_bytes:
            raise ValueError("dataset archive exceeds configured uncompressed size limit")
        seen_targets: set[Path] = set()
        for member in members:
            target = require_within(resolved_destination, resolved_destination / member.filename)
            if target in seen_targets:
                raise ValueError(f"duplicate dataset archive member: {member.filename}")
            seen_targets.add(target)
            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise ValueError(
                    f"symbolic links are not allowed in dataset archives: {member.filename}"
                )
            if member.flag_bits & 0x1:
                raise ValueError(
                    f"encrypted dataset archive member is not allowed: {member.filename}"
                )
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.is_symlink():
                raise ValueError(f"existing symbolic-link target is not allowed: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary_target = require_within(
                resolved_destination, target.with_name(f"{target.name}.extracting")
            )
            if temporary_target.is_symlink():
                raise ValueError(
                    f"temporary symbolic-link target is not allowed: {member.filename}"
                )
            with bundle.open(member) as source, temporary_target.open("wb") as output:
                shutil.copyfileobj(source, output, CHUNK_BYTES)
                output.flush()
                os.fsync(output.fileno())
            temporary_target.replace(target)
            extracted.append(str(target.relative_to(root)))
    return extracted


def verify_embedded_sha256sums(extract_root: Path) -> int:
    """Verify publisher-provided SHA256SUMS files after safe extraction."""

    verified = 0
    for checksum_file in extract_root.rglob("SHA256SUMS.txt"):
        for line_number, line in enumerate(
            checksum_file.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                expected, relative_name = line.split(maxsplit=1)
            except ValueError as exc:
                raise ValueError(
                    f"malformed checksum line {checksum_file}:{line_number}"
                ) from exc
            relative_name = relative_name.lstrip("* ")
            invalid_hex = any(
                character not in "0123456789abcdefABCDEF" for character in expected
            )
            if len(expected) != 64 or invalid_hex:
                raise ValueError(f"invalid SHA-256 at {checksum_file}:{line_number}")
            target = require_within(checksum_file.parent, checksum_file.parent / relative_name)
            if not target.is_file():
                raise ValueError(f"publisher checksum target is missing: {relative_name}")
            if sha256_file(target).lower() != expected.lower():
                raise ValueError(f"publisher checksum mismatch: {relative_name}")
            verified += 1
    return verified


def inspect_nested_zip(
    archive: Path,
    *,
    max_uncompressed_bytes: int,
    max_members: int,
) -> dict[str, int | str]:
    """Validate a deliberately non-extracted nested archive and record its bounds."""

    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > max_members:
            raise ValueError("nested dataset archive contains too many members")
        uncompressed_bytes = sum(member.file_size for member in members)
        if uncompressed_bytes > max_uncompressed_bytes:
            raise ValueError("nested dataset archive exceeds configured inspection limit")
        names: set[str] = set()
        for member in members:
            normalized = Path(member.filename.replace("/", os.sep))
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError(f"unsafe nested archive member: {member.filename}")
            if member.filename in names:
                raise ValueError(f"duplicate nested archive member: {member.filename}")
            names.add(member.filename)
            unix_mode = member.external_attr >> 16
            if stat.S_ISLNK(unix_mode) or member.flag_bits & 0x1:
                raise ValueError(f"unsupported nested archive member: {member.filename}")
    return {
        "sha256": sha256_file(archive),
        "members": len(members),
        "uncompressed_bytes": uncompressed_bytes,
    }


def acquire_dataset(
    spec: DatasetSpec,
    root: Path,
    progress: Callable[[str, int], None] | None = None,
) -> dict[str, object]:
    if spec.access_mode != "automatic":
        raise PermissionError(f"{spec.key} requires manual licence acknowledgement")
    records: list[dict[str, object]] = []
    for resource in spec.resources:
        record = download_resource(
            resource,
            root,
            (lambda count, name=resource.name: progress(name, count)) if progress else None,
        )
        if resource.extract_zip:
            archive = Path(str(record["path"]))
            extract_dir = archive.parent / "extracted"
            record["extracted_files"] = safe_extract_zip(
                archive,
                extract_dir,
                root,
                max_uncompressed_bytes=resource.max_uncompressed_bytes,
                max_members=resource.max_archive_members,
            )
            record["publisher_checksums_verified"] = verify_embedded_sha256sums(extract_dir)
            nested_archives: list[dict[str, object]] = []
            expected_nested_hashes = dict(resource.expected_nested_sha256)
            if set(expected_nested_hashes) != set(resource.inspect_nested_zip_paths):
                raise ValueError("every inspected nested archive must have a pinned checksum")
            for nested_relative_path in resource.inspect_nested_zip_paths:
                nested_archive = require_within(
                    extract_dir, extract_dir / nested_relative_path
                )
                if not nested_archive.is_file():
                    raise ValueError(
                        f"approved nested archive is missing: {nested_relative_path}"
                    )
                inspection = inspect_nested_zip(
                    nested_archive,
                    max_uncompressed_bytes=resource.max_nested_uncompressed_bytes,
                    max_members=resource.max_archive_members,
                )
                expected_nested_hash = expected_nested_hashes.get(nested_relative_path)
                if (
                    expected_nested_hash is not None
                    and inspection["sha256"] != expected_nested_hash
                ):
                    raise ValueError(
                        f"nested archive checksum mismatch: {nested_relative_path}"
                    )
                nested_archives.append(
                    {
                        "path": str(nested_archive.relative_to(root)),
                        **inspection,
                    }
                )
            if nested_archives:
                record["nested_archives"] = nested_archives
        records.append({"name": resource.name, "url": resource.url, **record})

    provenance = {
        "dataset": spec.key,
        "title": spec.title,
        "version": spec.version,
        "homepage": spec.homepage,
        "license": {"name": spec.license_name, "url": spec.license_url},
        "citation": spec.citation,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "resources": records,
    }
    manifest = require_within(root, root / "manifests" / f"{spec.key}-{spec.version}.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = require_within(root, manifest.with_suffix(".json.tmp"))
    temporary_manifest.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    temporary_manifest.replace(manifest)
    return provenance
