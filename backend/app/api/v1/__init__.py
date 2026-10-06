from fastapi import APIRouter

from app.api.v1 import analysis, auth, base_data, prediction, screen, system, trade

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(system.router)
api_router.include_router(base_data.router)
api_router.include_router(trade.router)
api_router.include_router(analysis.router)
api_router.include_router(prediction.router)
api_router.include_router(screen.router)
