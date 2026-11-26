"""Estrategia OCR local con Pix2Text."""

from __future__ import annotations

import tempfile
from pathlib import Path
from returns.result import Result, Success, Failure

from mathtutor.ingestion.strategies.protocol import OCRStrategy, OCRRequest, OCRResponse, OCRError


class Pix2TextStrategy(OCRStrategy):
    """Estrategia OCR local usando Pix2Text (requiere GPU)."""

    name = "pix2text"
    requires_gpu = True

    def __init__(self, model_path: str = "pix2text", device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self._model = None

    def _get_model(self):
        """Lazy loading del modelo."""
        if self._model is None:
            try:
                from pix2text import Pix2Text
                self._model = Pix2Text(model_path=self.model_path, device=self.device)
            except ImportError:
                raise RuntimeError("pix2text no instalado. Instala con: pip install mathtutor-ai[ocr-local]")
        return self._model

    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]:
        try:
            model = self._get_model()

            # Pix2Text espera rutas de archivo
            with tempfile.TemporaryDirectory() as tmpdir:
                paths = []
                for i, img_bytes in enumerate(request.images):
                    path = Path(tmpdir) / f"img_{i}.png"
                    path.write_bytes(img_bytes)
                    paths.append(str(path))

                results = model.recognize(paths)
                latex = "\n".join(r.get("text", "") for r in results)
                confidence = sum(r.get("confidence", 0.9) for r in results) / max(len(results), 1)

            return Success(OCRResponse(
                latex_raw=latex,
                confidence=confidence,
                strategy_name=self.name,
                metadata={"pages": len(request.images)}
            ))
        except Exception as e:
            return Failure(OCRError(
                code="LOCAL_OCR_FAILED",
                message=str(e),
                strategy=self.name,
                recoverable=True  # Trigger fallback
            ))
