import logging
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.database import engine
from app.middlewares.rate_limit import AuthRateLimitMiddleware
from app.routes.auth_routes import router as auth_router

settings = get_settings()
logging.basicConfig(
    level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("app")
app = FastAPI(title=settings.app_name)
app.add_middleware(AuthRateLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Omit input and ctx: they can contain submitted passwords.
    errors = [{key: error[key] for key in ("type", "loc", "msg")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        # Exception messages can include SQL parameters; never log bodies or tokens.
        logger.error("request_failed error_type=%s", type(exc).__name__)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    route = request.scope.get("route")
    logger.info(
        "%s %s status=%s duration_ms=%.1f",
        request.method,
        getattr(route, "path", "unmatched"),
        response.status_code,
        (perf_counter() - started) * 1000,
    )
    return response


app.include_router(auth_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT id FROM users LIMIT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


# Add CORS last so it surrounds our request/error middleware.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
)
