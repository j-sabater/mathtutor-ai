"""Estrategia OCR fallback con Mathpix API."""

from __future__ import annotations

import httpx
from returns.result import Result, Success, Failure

from mathtutor.ingestion.strategies.protocol import OCRStrategy, OCRRequest, OCRResponse, OCRError


class MathpixStrategy(OCRStrategy):
    """Estrategia OCR vía Mathpix API (fallback cloud)."""

    name = "mathpix"
    requires_gpu = False

    def __init__(self, app_id: str, app_key: str):
        if not app_id or not app_key:
            raise ValueError("MATHPIX_APP_ID y MATHPIX_APP_KEY son requeridos")
        self.app_id = app_id
        self.app_key = app_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def process(self, request: OCRRequest) -> Result[OCRResponse, OCRError]:
        try:
            # Preparar archivos para multipart upload
            files = []
            for i, img_bytes in enumerate(request.images):
                files.append(("file", (f"img_{i}.png", img_bytes, "image/png")))

            resp = await self.client.post(
                "https://api.mathpix.com/v3/latex",
                files=files,
                headers={
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                },
                data={"options_json": '{"math_inline_delimiters": ["$", "$"]}'}
            )
            resp.raise_for_status()
            data = resp.json()

            return Success(OCRResponse(
                latex_raw=data.get("latex", ""),
                confidence=data.get("confidence", 0.95),
                strategy_name=self.name,
                metadata={"mathpix_id": data.get("latex_id")}
            ))
        except httpx.HTTPStatusError as e:
            return Failure(OCRError(
                code="API_OCR_FAILED",
                message=f"HTTP {e.response.status_code}: {e.response.text}",
                strategy=self.name,
                recoverable=False
            ))
        except Exception as e:
            return Failure(OCRError(
                code="API_OCR_ERROR",
                message=str(e),
                strategy=self.name,
                recoverable=False
            ))
