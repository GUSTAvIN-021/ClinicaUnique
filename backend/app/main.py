from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings
from app.routers import administration, appointments, auth, dashboard, patients, professionals, records, users
from app.routers.auth import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


settings = get_settings()
app = FastAPI(title="Unique API", version="1.0.0", docs_url="/docs", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])
app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(professionals.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(administration.router, prefix="/api")


@app.get("/health", tags=["Infraestrutura"])
def health():
    return {"status": "ok"}
