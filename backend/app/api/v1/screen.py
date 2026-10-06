"""数字大屏取数 API（只读聚合数据，免认证，供大屏直接展示）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ok
from app.services import screen_service

router = APIRouter(prefix="/screen", tags=["数字大屏"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return ok(screen_service.overview(db))


@router.get("/china-map")
def china_map(db: Session = Depends(get_db)):
    return ok(screen_service.china_map(db))


@router.get("/ganzhou")
def ganzhou(db: Session = Depends(get_db)):
    return ok(screen_service.ganzhou_counties(db))


@router.get("/county/{region_id}")
def county_detail(region_id: int, db: Session = Depends(get_db)):
    return ok(screen_service.county_detail(db, region_id))


@router.get("/area/{area_id}")
def area_detail(area_id: int, db: Session = Depends(get_db)):
    return ok(screen_service.area_detail(db, area_id))


@router.get("/price-trend")
def price_trend(months: int = 24, db: Session = Depends(get_db)):
    return ok(screen_service.price_trend(db, months))


@router.get("/intelligence")
def intelligence(db: Session = Depends(get_db)):
    """智能预测与产销排产：价格/需求/产量/库存/病虫害 + 排产建议。"""
    return ok(screen_service.intelligence(db))


@router.get("/layers")
def layers(db: Session = Depends(get_db)):
    """地图全部图层（销售流向/市场需求/销地价格/供应压力/病虫害风险/智能排产）。"""
    return ok(screen_service.map_layers(db))


@router.get("/layer/{layer}")
def layer(layer: str, db: Session = Depends(get_db)):
    return ok(screen_service.map_layer(db, layer))


@router.get("/predictions")
def predictions(
    type: str | None = None, limit: int = 20, db: Session = Depends(get_db)
):
    return ok(screen_service.latest_predictions(db, type, limit))


@router.get("/decisions")
def decisions(limit: int = 10, db: Session = Depends(get_db)):
    return ok(screen_service.latest_decisions(db, limit))
