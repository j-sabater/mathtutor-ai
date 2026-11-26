"""Pipeline de ingesta multimodal OCR (Strategy Pattern)."""

from mathtutor.ingestion.pipeline import OCRPipeline, OCRResult
from mathtutor.ingestion.strategies.protocol import OCRStrategy, OCRRequest, OCRResponse

__all__ = [
    "OCRPipeline",
    "OCRResult",
    "OCRStrategy",
    "OCRRequest",
    "OCRResponse",
]
