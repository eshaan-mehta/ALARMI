from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db import init_db
from .designs.router import router as designs_router
from .errors import ApiError
from .modules.router import router as modules_router
from .projects.router import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ALARMI Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def _api_error_handler(request: Request, exc: ApiError):
    # Match the frontend's expected error shape: { "message": ... }
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


# All API routes live under /api.
app.include_router(projects_router, prefix="/api")
app.include_router(designs_router, prefix="/api")
app.include_router(modules_router, prefix="/api")
