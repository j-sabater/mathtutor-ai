"""API REST (FastAPI) + WebSocket."""

from mathtutor.api.schemas.v1.ingest import IngestRequest, IngestResponse
from mathtutor.api.schemas.v1.review import OCRReviewRequest, OCRReviewResponse
from mathtutor.api.schemas.v1.correction import CorrectionResult
from mathtutor.api.schemas.v1.progress import ProgressResponse

__all__ = [
    "IngestRequest",
    "IngestResponse",
    "OCRReviewRequest",
    "OCRReviewResponse",
    "CorrectionResult",
    "ProgressResponse",
]
