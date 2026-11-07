# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Stateless HTTP adapter for text/TXT reviews; no retained review history."""
from __future__ import annotations
import logging
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ..pipeline.runner import ReviewInputError, decode_txt, run_review, MAX_TXT_BYTES
from ..pipeline.state import ReviewStatus

logger = logging.getLogger(__name__)
app = FastAPI(title="Multi-Agent Contract Review", description="Stateless four-stage review workflow", version="1.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

class ReviewRequest(BaseModel):
    text: str = Field(description="Contract text")

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    created_at: str
    document_hash: str
    jurisdiction: str
    as_of_date: str
    knowledge_status: str
    knowledge_version: str
    contract_type: str
    clauses_count: int
    clauses: list[dict]
    risk_findings: list[dict]
    risk_summary: str
    overall_risk_level: str
    compliance_findings: list[dict]
    missing_clauses: list[str]
    overall_compliance: str
    suggestions_count: int
    suggestions: list[dict]
    version_diff: str
    errors: list[str]
    failed_stage: str
    diagnostics: list[dict]
    message: str = ""

@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Do not include exc.errors(): it contains rejected input values.
    logger.warning("Invalid request code=INVALID_REQUEST")
    return JSONResponse(status_code=422, content={"detail": {
        "code": "INVALID_REQUEST", "message": "Request must contain a valid text string or TXT upload."}})

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "contract-review", "version": "1.2.0"}

async def _submit(text: str) -> JSONResponse:
    try:
        state = await run_review(text)
    except ReviewInputError as exc:
        status = 413 if exc.code in {"TEXT_TOO_LONG", "FILE_TOO_LARGE"} else 422
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from None
    except Exception:
        logger.error("Review execution failed code=INTERNAL_ERROR")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": "Review execution failed"}) from None
    status_code = 200
    message = ""
    if state.status == ReviewStatus.TIMED_OUT:
        status_code, message = 504, "Review timed out; available diagnostics are included."
    elif state.status == ReviewStatus.FAILED:
        status_code, message = 502, "Review failed; available diagnostics are included."
    response = ReviewResponse(**state.model_dump(mode="json"),
        clauses_count=len(state.clauses), suggestions_count=len(state.suggestions), message=message)
    # No store/checkpoint/cache: response data is released after this request completes.
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"),
                        headers={"Cache-Control": "no-store"})

@app.post("/api/v1/review", response_model=ReviewResponse,
          responses={502: {"model": ReviewResponse}, 504: {"model": ReviewResponse}})
async def create_review(request: ReviewRequest):
    return await _submit(request.text)

@app.post("/api/v1/review/upload", response_model=ReviewResponse,
          responses={502: {"model": ReviewResponse}, 504: {"model": ReviewResponse}})
async def upload_review(file: UploadFile = File(...)):
    """Decode TXT without retaining it; multipart parsing may use temporary disk."""
    try:
        if not file.filename or Path(file.filename).suffix.lower() != ".txt":
            raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_FORMAT", "message": "Only TXT files are supported"})
        text = decode_txt(await file.read(MAX_TXT_BYTES + 1))
    except ReviewInputError as exc:
        status = 413 if exc.code == "FILE_TOO_LARGE" else 422
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from None
    finally:
        await file.close()
    return await _submit(text)

def start():
    import uvicorn
    from ..config import settings
    uvicorn.run("src.api.main:app", host=settings.APP_HOST, port=settings.APP_PORT)

if __name__ == "__main__":
    start()
