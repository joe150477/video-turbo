"""Application implementation - ASGI."""

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import config
from app.models.exception import HttpException
from app.router import root_api_router
from app.utils import error_messages, utils


def exception_handler(request: Request, e: HttpException):
    return JSONResponse(
        status_code=e.status_code,
        content=utils.get_response(e.status_code, e.data, e.message),
    )


def validation_exception_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=utils.get_response(status=400, data=e.errors(), message="field required"),
    )


def unhandled_exception_handler(request: Request, e: Exception):
    """Catch-all for exceptions no controller anticipated.

    Without this, FastAPI's default handler would return the raw exception
    message (potentially a Python-level string) to the client. The desktop
    app must never surface that, so every unhandled exception is translated
    to a short Spanish message here, with the real cause only in the logs.
    """
    message, code = error_messages.translate_exception(e, context=request.url.path)
    return JSONResponse(
        status_code=500,
        content=utils.get_response(500, {"error_code": code}, message),
    )


def get_application() -> FastAPI:
    """Initialize FastAPI application.

    Returns:
       FastAPI: Application object instance.

    """
    instance = FastAPI(
        title=config.project_name,
        description=config.project_description,
        version=config.project_version,
        debug=False,
    )
    instance.include_router(root_api_router)
    instance.add_exception_handler(HttpException, exception_handler)
    instance.add_exception_handler(RequestValidationError, validation_exception_handler)
    instance.add_exception_handler(Exception, unhandled_exception_handler)
    return instance


app = get_application()

# Configures the CORS middleware for the FastAPI app
cors_allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
origins = cors_allowed_origins_str.split(",") if cors_allowed_origins_str else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

task_dir = utils.task_dir()
app.mount("/tasks", StaticFiles(directory=task_dir, html=True, follow_symlink=True), name="")


# In the packaged desktop app, Electron points MPT_FRONTEND_DIR at the built
# React app and loads it over HTTP from this backend (http://127.0.0.1:port)
# instead of via file://. Serving over HTTP is what makes the SPA's absolute
# asset paths (/assets/...) and ES modules load correctly — file:// blocks
# them, which is what caused the blank-window bug. The "/" mount must be
# registered last so it doesn't shadow /api/v1 and /tasks.
class _SpaStaticFiles(StaticFiles):
    """StaticFiles that never lets index.html be cached.

    The JS/CSS bundles carry a content hash in their filename, so a new build
    produces new URLs and can be cached forever. index.html keeps a stable URL
    but points at those hashed files — if the shell (Electron) caches it, an
    updated app keeps loading the OLD bundle and the user never sees the new UI.
    Serving the HTML with no-store forces the shell to re-fetch it every launch,
    which is essential for auto-update to actually take effect.
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        # path is "." for the directory root (html=True serves index.html).
        if path in (".", "", "index.html") or path.endswith(".html"):
            response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


_frontend_dir = os.getenv("MPT_FRONTEND_DIR", "").strip()
if _frontend_dir and os.path.isdir(_frontend_dir):
    app.mount("/", _SpaStaticFiles(directory=_frontend_dir, html=True), name="frontend")
else:
    public_dir = utils.public_dir()
    app.mount("/", _SpaStaticFiles(directory=public_dir, html=True), name="")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("shutdown event")


@app.on_event("startup")
def startup_event():
    logger.info("startup event")
