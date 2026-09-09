"""Routes for CSV and Parquet upload and ingestion."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from src.schema import (
    SuccessResponseSchema,
    ErrorResponseSchema,
    IngestionUploadResponseSchema,
)
from src.services.ingestion_service import start_ingestion
from src.utils import ALLOWED_INGESTION_FILE_FORMATS
from src.utils.algorithm import normalize_algorithm

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def _allowed_extension(filename: str) -> bool:

    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[-1].lower() in ALLOWED_INGESTION_FILE_FORMATS


@router.post(
    "/upload",
    summary="Upload CSV/Parquet for ingestion",
    status_code=202,
    response_model=SuccessResponseSchema,
    responses={
        400: {"model": ErrorResponseSchema},
        500: {"model": ErrorResponseSchema},
    },
)
async def upload(
    file: UploadFile = File(...),
    file_ref: str | None = Form(None),
    algorithm: str = Form("simplex"),
) -> dict:
    """POST /ingestion/upload — recebe file multipart; body: file, file_ref, algorithm."""

    filename = file.filename or ""
    if not _allowed_extension(filename):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "INVALID_FILE_EXTENSION",
                "message": "Extensao not permitida. Use CSV or Parquet.",
                "details": {"allowed_formats": list(ALLOWED_INGESTION_FILE_FORMATS)},
            },
        )

    contents = await file.read()
    if not contents:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "EMPTY_FILE",
                "message": "The uploaded file is empty.",
                "details": {},
            },
        )

    try:
        normalized_algorithm = normalize_algorithm(algorithm)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "code": "INVALID_ALGORITHM",
                "message": str(exc),
                "details": {"algorithm": algorithm},
            },
        )

    try:
        result = await start_ingestion(
            contents, filename, file_ref, algorithm=normalized_algorithm
        )
    except Exception as exc:  # pragma: no cover - placeholder
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "code": "INGESTION_SERVICE_ERROR",
                "message": "Internal error while starting ingestion.",
                "details": {"error": str(exc)},
            },
        )

    ingestion_resp = IngestionUploadResponseSchema(
        run_id=result["run_id"],
        filename=result["filename"],
        algorithm=result["algorithm"],
        state=result.get("state", "queued"),
    )

    return {
        "status": "ok",
        "data": ingestion_resp.model_dump(),
        "meta": {
            "accepted_formats": list(ALLOWED_INGESTION_FILE_FORMATS),
            "queue": result.get("queue"),
        },
    }
