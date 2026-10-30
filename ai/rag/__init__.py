"""Member 3 RAG (Retrieval-Augmented Generation) package."""

from .models import KnowledgeChunk, ReviewStatus
from .loader import KnowledgeBaseLoader, LoaderError, DuplicateChunkError, MalformedRecordError
from .retriever import LocalKeywordRetriever, RetrievalRecord
from .ingestion import (
    MedicalDocumentIngestor,
    IngestedChunkRecord,
    IngestedDocument,
    IngestionError,
    FileValidationError,
    FileSizeLimitError,
    EmptyDocumentError,
    chunk_text,
    sanitize_medical_text,
    compute_content_hash,
    extract_text_from_file,
    extract_text_from_bytes,
    delete_document_from_jsonl,
    save_document_to_jsonl,
)

__all__ = [
    "KnowledgeChunk", "ReviewStatus",
    "KnowledgeBaseLoader", "LoaderError", "DuplicateChunkError", "MalformedRecordError",
    "LocalKeywordRetriever", "RetrievalRecord",
    "MedicalDocumentIngestor",
    "IngestedChunkRecord",
    "IngestedDocument",
    "IngestionError",
    "FileValidationError",
    "FileSizeLimitError",
    "EmptyDocumentError",
    "chunk_text",
    "sanitize_medical_text",
    "compute_content_hash",
    "extract_text_from_file",
    "extract_text_from_bytes",
    "delete_document_from_jsonl",
    "save_document_to_jsonl",
]
