"""FastAPI application wiring (lifespan, middleware, exception handlers)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import environment, logger
from app.core.exceptions import format_validation_errors
from app.core.helpers import APIResponse
from app.core.storage.dependency import get_database_engine, get_redis_cache


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    database_engine = get_database_engine()
    await database_engine.start(logger)

    redis_cache = None
    if environment.REDIS_URL:
        redis_cache = get_redis_cache()
        await redis_cache.connect()

    try:
        yield
    finally:
        await database_engine.turn_off(logger)
        if redis_cache is not None:
            await redis_cache.disconnect()


app = FastAPI(
    debug=not environment.IS_PRODUCTION,
    title=environment.APP_NAME,
    version=environment.APP_CURRENT_VERSION,
    lifespan=lifespan,
    docs_url=None if environment.IS_PRODUCTION else "/docs",
    redoc_url=None if environment.IS_PRODUCTION else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=environment.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return APIResponse.error(msg=str(exc.detail), status=exc.status_code)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return APIResponse.validation(errors=format_validation_errors(exc.errors()))


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return APIResponse.server_error()
