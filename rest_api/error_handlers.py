from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.exceptions import AppError
from schemas.sch_base import ErrorSchema


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    body = ErrorSchema(code=exc.code, detail=exc.detail)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"), headers=exc.headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
