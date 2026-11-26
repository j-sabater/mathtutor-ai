"""API Contracts v1 (Pydantic v2, frozen, extra=forbid)."""

from mathtutor.api.schemas.v1.ingest import IngestRequest, IngestResponse
from mathtutor.api.schemas.v1.review import OCRReviewRequest, OCRReviewResponse
from mathtutor.api.schemas.v1.correction import CorrectionResult, StepFeedback
from mathtutor.api.schemas.v1.progress import (
    ConceptoProgress,
    PatronErrorFrequency,
    ProgressResponse,
)
from mathtutor.api.schemas.v1.notes import GenerateNoteRequest, NoteResponse

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
