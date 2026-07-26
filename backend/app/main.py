import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .db import init_db
from .designs.router import router as designs_router
from .errors import ApiError
from .modules.router import router as modules_router
from .objects.router import router as objects_router
from .projects.router import router as projects_router

logger = logging.getLogger("alarmi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ALARMI Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Every error leaves as { "message": ... } so the frontend (which reads
# err.response.data.message) always has something to show.


@app.exception_handler(ApiError)
async def _api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(IntegrityError)
async def _integrity_handler(request: Request, exc: IntegrityError):
    # A DB constraint (e.g. the unique project name) tripped past a pre-check —
    # typically a concurrent race. Report it as a conflict, not a 500.
    return JSONResponse(
        status_code=409,
        content={"message": "That value conflicts with an existing record."},
    )


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "Invalid value")
        message = f"{loc}: {msg}" if loc else msg
    else:
        message = "Invalid request."
    return JSONResponse(status_code=422, content={"message": message})


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Reshape FastAPI/Starlette's default {"detail": ...} (unknown route, 405…)
    # into the app's {"message": ...} contract.
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(status_code=exc.status_code, content={"message": detail})


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"message": "Internal server error."})


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


# All API routes live under /api.
app.include_router(projects_router, prefix="/api")
app.include_router(designs_router, prefix="/api")
app.include_router(modules_router, prefix="/api")
app.include_router(objects_router, prefix="/api")
