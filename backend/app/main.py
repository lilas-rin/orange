"""应用入口：中间件注册、全局异常处理、健康检查。"""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import new_request_id, request_id_var, setup_logging
from app.db.session import engine
from app.services import forecast_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.DEBUG)
    logger.info("应用启动 %s", settings.APP_NAME)
    # 后台预热预测缓存：market_demand 要为每个省拟合随机森林（约 6s），
    # 不在启动时算完，大屏首位访问者就要自己等，且可能撞破前端请求超时。
    threading.Thread(
        target=forecast_service.warmup, name="forecast-warmup", daemon=True
    ).start()
    yield
    engine.dispose()
    logger.info("应用已优雅停机")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # CORS：显式来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求 ID 中间件
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = new_request_id()
        request_id_var.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # ---- 全局异常处理：统一错误结构，不泄露堆栈 ----
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "code": 40001,
                "message": "请求参数错误",
                "details": exc.errors(),
                "request_id": request_id_var.get(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("未处理异常")
        return JSONResponse(
            status_code=500,
            content={
                "code": 50000,
                "message": "服务器内部错误",
                "request_id": request_id_var.get(),
            },
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # ---- 健康检查 ----
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}

    return app


app = create_app()
