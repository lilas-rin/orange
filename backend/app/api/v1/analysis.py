"""数据分析 API。"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.common import ApiResponse, ok
from app.services import analysis_service

router = APIRouter(prefix="/analysis", tags=["数据分析"])


@router.get("/production-sales")
def production_sales(
    start: date | None = None,
    end: date | None = None,
    area_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(analysis_service.production_sales_analysis(db, start, end, area_id))


@router.get("/price")
def price(
    start: date | None = None,
    end: date | None = None,
    area_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(analysis_service.price_analysis(db, start, end, area_id))


@router.get("/market")
def market(
    year: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(analysis_service.market_analysis(db, year))


@router.get("/pest")
def pest(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(analysis_service.pest_analysis(db, start, end))


@router.get("/evaluation")
def evaluation(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(analysis_service.evaluation_analysis(db))
