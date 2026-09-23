"""FastAPI application wiring (lifespan, middleware, exception handlers)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.connectors.config import init_argus_config
from app.core.config import environment, logger
from app.core.database import init_database, shutdown_database
from app.core.exceptions import format_validation_errors
from app.core.helpers import APIResponse
from app.core.redis import get_redis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_argus_config()
    await init_database()

    redis_client = get_redis()
    try:
        await redis_client.connect()
    except Exception:
        # Keep serving so the dashboard can report the connection as down.
        logger.error("Redis unavailable at startup")

    try:
        yield
    finally:
        await shutdown_database()
        await redis_client.disconnect()


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
