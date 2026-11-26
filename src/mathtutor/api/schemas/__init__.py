"""Esquemas Pydantic versionados para API."""

from mathtutor.api.schemas.v1 import (
    IngestRequest,
    IngestResponse,
    OCRReviewRequest,
    OCRReviewResponse,
    CorrectionResult,
    StepFeedback,
    ConceptoProgress,
    PatronErrorFrequency,
    ProgressResponse,
    GenerateNoteRequest,
    NoteResponse,
)

__all__ = [
    "IngestRequest",
    "IngestResponse",
    "OCRReviewRequest",
    "OCRReviewResponse",
    "CorrectionResult",
    "StepFeedback",
    "ConceptoProgress",
    "PatronErrorFrequency",
    "ProgressResponse",
    "GenerateNoteRequest",
    "NoteResponse",
]
