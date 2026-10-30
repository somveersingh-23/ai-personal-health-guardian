"""Medical document ingestion and processing module for the Member 3 RAG pipeline.

Supports safe, authorized medical document ingestion:
- File type validation: text (.txt, .md) and PDF (.pdf via PyMuPDF).
- Strict file size limit: rejects files > 5MB.
- Text extraction from plain text and PDF pages.
- Text sanitization: strips control characters and neutralizes prompt injections.
- Deterministic chunking: configurable chunk size, overlap, and min chunk size.
- Metadata extraction: document_id, chunk_id, title, source_name, topic,
  language, review_status, reviewed_at, version, safety_tags, keywords, and content_hash.
- Document deletion: removes chunks matching a document_id from storage.
- Document re-indexing support.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from .models import KnowledgeChunk, ReviewStatus

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
SUPPORTED_EXTENSIONS = frozenset({".txt", ".md", ".pdf"})

DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_MIN_CHUNK_SIZE = 50

DEFAULT_SAFETY_TAGS = ("authorized_ingestion", "non_diagnostic", "educational")
DEFAULT_TOPIC = "general_health"
DEFAULT_SOURCE_NAME = "Authorized Medical Guidance"
DEFAULT_LANGUAGE = "en"
DEFAULT_VERSION = "1.0"

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "it", "its", "this", "that", "these",
    "those", "my", "your", "his", "her", "our", "their", "i", "me", "you",
    "he", "she", "we", "they", "what", "why", "how", "when", "where",
    "which", "who", "whom", "not", "no", "so", "if", "as",
})

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|constraints?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"change\s+(the\s+)?safety\s+action", re.IGNORECASE),
    re.compile(r"diagnose\s+(the\s+)?user", re.IGNORECASE),
    re.compile(r"reveal\s+(secrets?|api\s*key|password)", re.IGNORECASE),
    re.compile(r"execute\s+(command|code|script)", re.IGNORECASE),
    re.compile(r"override\s+(safety|constraint|rule)", re.IGNORECASE),
    re.compile(r"bypass\s+(safety|filter|rule|constraint)", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class IngestionError(Exception):
    """Base exception for document ingestion errors."""


class FileValidationError(IngestionError):
    """Raised when file extension or format is unsupported or invalid."""


class FileSizeLimitError(IngestionError):
    """Raised when file exceeds the 5MB size limit."""


class EmptyDocumentError(IngestionError):
    """Raised when extracted document text is empty or shorter than minimum chunk size."""


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IngestedChunkRecord:
    """A single processed knowledge chunk with its hash and metadata."""

    chunk: KnowledgeChunk
    content_hash: str
    char_count: int

    def to_dict(self) -> dict:
        """Convert chunk and metadata to a JSONL-compatible dictionary."""
        return {
            "document_id": self.chunk.document_id,
            "chunk_id": self.chunk.chunk_id,
            "title": self.chunk.title,
            "content": self.chunk.content,
            "source_name": self.chunk.source_name,
            "source_url": self.chunk.source_url,
            "topic": self.chunk.topic,
            "language": self.chunk.language,
            "reviewed_at": self.chunk.reviewed_at.isoformat(),
            "review_status": self.chunk.review_status.value,
            "safety_tags": list(self.chunk.safety_tags),
            "keywords": list(self.chunk.keywords),
            "version": self.chunk.version,
            "expires_on": (
                self.chunk.expires_on.isoformat()
                if self.chunk.expires_on
                else None
            ),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class IngestedDocument:
    """Represents a successfully ingested and chunked medical document."""

    document_id: str
    title: str
    chunks: tuple[IngestedChunkRecord, ...]
    injection_detected: bool
    sanitized: bool
    total_chars: int

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


# ---------------------------------------------------------------------------
# Extraction & Validation Helpers
# ---------------------------------------------------------------------------

def validate_file_size(size_bytes: int, max_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
    """Validate that file size does not exceed the limit."""
    if size_bytes > max_bytes:
        raise FileSizeLimitError(
            f"File size {size_bytes} bytes exceeds maximum limit of {max_bytes} bytes (5MB)"
        )


def validate_file_extension(path_or_name: str | Path) -> str:
    """Validate and return normalized lowercase file extension."""
    suffix = Path(path_or_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file extension '{suffix}'. Supported extensions: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return suffix


def extract_text_from_file(path: str | Path) -> str:
    """Extract plain text from a .txt, .md, or .pdf file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileValidationError(f"File not found: {file_path}")

    validate_file_size(file_path.stat().st_size)
    suffix = validate_file_extension(file_path)

    if suffix in {".txt", ".md"}:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise FileValidationError(f"File must be valid UTF-8 text: {exc}") from exc

    if suffix == ".pdf":
        if fitz is None:
            raise IngestionError("PyMuPDF (fitz) is required for PDF ingestion")
        try:
            doc = fitz.open(str(file_path))
            if doc.is_encrypted:
                doc.close()
                raise FileValidationError("Encrypted PDFs are not supported")
            pages_text = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(pages_text)
        except Exception as exc:
            if isinstance(exc, (FileValidationError, FileSizeLimitError)):
                raise
            raise FileValidationError(f"Failed to read PDF file: {exc}") from exc

    raise FileValidationError(f"Unhandled extension: {suffix}")


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract plain text from raw bytes of a .txt, .md, or .pdf file."""
    validate_file_size(len(data))
    suffix = validate_file_extension(filename)

    if suffix in {".txt", ".md"}:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FileValidationError(f"Content must be valid UTF-8 text: {exc}") from exc

    if suffix == ".pdf":
        if fitz is None:
            raise IngestionError("PyMuPDF (fitz) is required for PDF ingestion")
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            if doc.is_encrypted:
                doc.close()
                raise FileValidationError("Encrypted PDFs are not supported")
            pages_text = [page.get_text() for page in doc]
            doc.close()
            return "\n\n".join(pages_text)
        except Exception as exc:
            if isinstance(exc, (FileValidationError, FileSizeLimitError)):
                raise
            raise FileValidationError(f"Failed to read PDF stream: {exc}") from exc

    raise FileValidationError(f"Unhandled extension: {suffix}")


# ---------------------------------------------------------------------------
# Sanitization & Hashing
# ---------------------------------------------------------------------------

def sanitize_medical_text(text: str) -> tuple[str, bool]:
    """Strip control characters and neutralize prompt injection attempts.

    Returns
    -------
    tuple[str, bool]
        (sanitized_text, injection_detected)
    """
    # Strip control characters (preserve \t, \n, \r)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    injection_detected = False
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("[content removed]", cleaned)
            injection_detected = True

    # Normalize excessive carriage returns and trailing whitespace
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned, injection_detected


def compute_content_hash(text: str) -> str:
    """Compute deterministic SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokenize_text(text: str) -> list[str]:
    """Tokenize text into lowercase alpha-numeric words excluding stop words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def extract_keywords(
    text: str,
    topic: str = "",
    max_keywords: int = 8,
) -> tuple[str, ...]:
    """Extract distinct non-stop keywords from text, falling back to topic/health."""
    tokens = _tokenize_text(text)
    seen: set[str] = set()
    result: list[str] = []

    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
            if len(result) >= max_keywords:
                break

    if topic:
        topic_tokens = _tokenize_text(topic.replace("_", " "))
        for tt in topic_tokens:
            if tt not in seen:
                seen.add(tt)
                result.append(tt)

    if not result:
        result = ["general", "health"]

    return tuple(result)


# ---------------------------------------------------------------------------
# Deterministic Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
) -> list[str]:
    """Deterministically partition text into overlapping windows.

    Parameters
    ----------
    text:
        Sanitized input text.
    chunk_size:
        Maximum characters per chunk.
    overlap:
        Overlap characters between adjacent chunks.
    min_chunk_size:
        Minimum characters for a standalone chunk.

    Returns
    -------
    list[str]
        List of non-empty chunk strings.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if overlap < 0:
        raise ValueError("overlap must be a non-negative integer")
    if overlap >= chunk_size:
        raise ValueError("overlap must be strictly less than chunk_size")
    if min_chunk_size <= 0:
        raise ValueError("min_chunk_size must be a positive integer")
    if min_chunk_size > chunk_size:
        raise ValueError("min_chunk_size cannot exceed chunk_size")

    cleaned = text.strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        return [cleaned] if len(cleaned) >= min_chunk_size else []

    step = chunk_size - overlap
    chunks: list[str] = []
    start = 0
    n = len(cleaned)

    while start < n:
        end = min(start + chunk_size, n)
        candidate = cleaned[start:end].strip()
        if len(candidate) >= min_chunk_size:
            chunks.append(candidate)
        elif chunks and candidate:
            # Append trailing snippet to previous chunk to prevent losing context
            chunks[-1] = (chunks[-1] + " " + candidate).strip()
        if end >= n:
            break
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Storage & Deletion Operations
# ---------------------------------------------------------------------------

def save_document_to_jsonl(
    kb_path: Path | str,
    doc: IngestedDocument,
) -> int:
    """Save document chunks to a JSONL knowledge base, replacing any existing chunks."""
    target_path = Path(kb_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # First remove any existing records for this document_id
    delete_document_from_jsonl(target_path, doc.document_id)

    # Append new records
    with open(target_path, "a", encoding="utf-8") as f:
        for chunk_record in doc.chunks:
            line = json.dumps(chunk_record.to_dict()) + "\n"
            f.write(line)

    return len(doc.chunks)


def delete_document_from_jsonl(
    kb_path: Path | str,
    document_id: str,
) -> int:
    """Remove all chunks for document_id from JSONL file atomically.

    Returns the number of chunks deleted.
    """
    target_path = Path(kb_path)
    if not target_path.is_file():
        return 0

    target_id = document_id.strip()
    if not target_id:
        return 0

    kept_lines: list[str] = []
    deleted_count = 0

    with open(target_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
                if isinstance(record, dict) and record.get("document_id") == target_id:
                    deleted_count += 1
                    continue
            except json.JSONDecodeError:
                pass
            kept_lines.append(stripped + "\n")

    if deleted_count > 0:
        # Atomic replace using temporary file in same directory
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            dir=target_path.parent,
            delete=False,
            encoding="utf-8",
        )
        try:
            temp_file.writelines(kept_lines)
            temp_file.close()
            os.replace(temp_file.name, target_path)
        except Exception:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise

    return deleted_count


# ---------------------------------------------------------------------------
# Medical Document Ingestor
# ---------------------------------------------------------------------------

class MedicalDocumentIngestor:
    """Ingest, validate, sanitize, chunk, and index medical documents."""

    def __init__(
        self,
        kb_path: Optional[Path | str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        self._kb_path = Path(kb_path) if kb_path is not None else None
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chunk_size = min_chunk_size
        self._max_file_size = max_file_size

    def ingest_text(
        self,
        text: str,
        document_id: str,
        title: str,
        topic: str = DEFAULT_TOPIC,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_url: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        version: str = DEFAULT_VERSION,
        safety_tags: Optional[Sequence[str]] = None,
        keywords: Optional[Sequence[str]] = None,
        reviewed_at: Optional[date] = None,
        expires_on: Optional[date] = None,
    ) -> IngestedDocument:
        """Sanitize, chunk, and process raw medical text into approved knowledge chunks."""
        doc_id = document_id.strip()
        doc_title = title.strip()
        if not doc_id:
            raise ValueError("document_id must not be empty or whitespace-only")
        if not doc_title:
            raise ValueError("title must not be empty or whitespace-only")

        # Size check on text bytes
        text_bytes_len = len(text.encode("utf-8"))
        validate_file_size(text_bytes_len, self._max_file_size)

        # Sanitization
        sanitized_text, injection_detected = sanitize_medical_text(text)
        if not sanitized_text.strip():
            raise EmptyDocumentError("Document text is empty after sanitization")

        # Chunking
        raw_chunks = chunk_text(
            sanitized_text,
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
            min_chunk_size=self._min_chunk_size,
        )
        if not raw_chunks:
            raise EmptyDocumentError(
                f"Document text ({len(sanitized_text.strip())} chars) is shorter than minimum chunk size ({self._min_chunk_size})"
            )

        # Normalize tags
        tags = tuple(safety_tags) if safety_tags else DEFAULT_SAFETY_TAGS
        review_date = reviewed_at or date.today()

        chunk_records: list[IngestedChunkRecord] = []
        for idx, chunk_content in enumerate(raw_chunks, start=1):
            chunk_id = f"{doc_id}#c{idx}"
            chunk_hash = compute_content_hash(chunk_content)

            chunk_keywords = (
                tuple(k.lower().strip() for k in keywords if k.strip())
                if keywords
                else extract_keywords(chunk_content, topic)
            )
            if not chunk_keywords:
                chunk_keywords = extract_keywords(chunk_content, topic)

            k_chunk = KnowledgeChunk(
                document_id=doc_id,
                chunk_id=chunk_id,
                title=doc_title,
                content=chunk_content,
                source_name=source_name.strip() or DEFAULT_SOURCE_NAME,
                source_url=source_url.strip() if source_url else None,
                topic=topic.strip() or DEFAULT_TOPIC,
                language=language.strip() or DEFAULT_LANGUAGE,
                reviewed_at=review_date,
                review_status=ReviewStatus.APPROVED,
                safety_tags=tags,
                keywords=chunk_keywords,
                version=version.strip() or DEFAULT_VERSION,
                expires_on=expires_on,
            )

            chunk_records.append(
                IngestedChunkRecord(
                    chunk=k_chunk,
                    content_hash=chunk_hash,
                    char_count=len(chunk_content),
                )
            )

        ingested_doc = IngestedDocument(
            document_id=doc_id,
            title=doc_title,
            chunks=tuple(chunk_records),
            injection_detected=injection_detected,
            sanitized=True,
            total_chars=sum(c.char_count for c in chunk_records),
        )

        if self._kb_path is not None:
            save_document_to_jsonl(self._kb_path, ingested_doc)

        return ingested_doc

    def ingest_file(
        self,
        path: Path | str,
        document_id: str,
        title: Optional[str] = None,
        topic: str = DEFAULT_TOPIC,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_url: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        version: str = DEFAULT_VERSION,
        safety_tags: Optional[Sequence[str]] = None,
        keywords: Optional[Sequence[str]] = None,
    ) -> IngestedDocument:
        """Extract text from a file (.txt, .md, .pdf) and ingest it."""
        file_path = Path(path)
        extracted = extract_text_from_file(file_path)
        resolved_title = (title or file_path.stem).strip()
        return self.ingest_text(
            text=extracted,
            document_id=document_id,
            title=resolved_title,
            topic=topic,
            source_name=source_name,
            source_url=source_url,
            language=language,
            version=version,
            safety_tags=safety_tags,
            keywords=keywords,
        )

    def ingest_bytes(
        self,
        data: bytes,
        filename: str,
        document_id: str,
        title: Optional[str] = None,
        topic: str = DEFAULT_TOPIC,
        source_name: str = DEFAULT_SOURCE_NAME,
        source_url: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
        version: str = DEFAULT_VERSION,
        safety_tags: Optional[Sequence[str]] = None,
        keywords: Optional[Sequence[str]] = None,
    ) -> IngestedDocument:
        """Extract text from bytes and ingest it."""
        extracted = extract_text_from_bytes(data, filename)
        resolved_title = (title or Path(filename).stem).strip()
        return self.ingest_text(
            text=extracted,
            document_id=document_id,
            title=resolved_title,
            topic=topic,
            source_name=source_name,
            source_url=source_url,
            language=language,
            version=version,
            safety_tags=safety_tags,
            keywords=keywords,
        )

    def delete_document(self, document_id: str) -> int:
        """Delete document from the associated knowledge base file."""
        if self._kb_path is None:
            raise IngestionError("Cannot delete document: no kb_path configured")
        return delete_document_from_jsonl(self._kb_path, document_id)
