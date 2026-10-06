"""产销数据管理：产量/销量/价格 CRUD + 市场与病虫害管理 + 数据导入。"""
from datetime import date

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import (
    MarketData,
    PestDiseaseRecord,
    PestDiseaseType,
    PriceData,
    ProductionArea,
    ProductionData,
    Product,
    Region,
    SalesData,
    User,
)
from app.repositories.base import BaseRepository
from app.schemas.common import ApiResponse, PageData, ok
from app.schemas.trade import (
    MarketDataCreate,
    MarketDataOut,
    MarketDataUpdate,
    PestRecordCreate,
    PestRecordOut,
    PestRecordUpdate,
    PestTypeCreate,
    PestTypeOut,
    PriceDataCreate,
    PriceDataOut,
    PriceDataUpdate,
    ProductionDataCreate,
    ProductionDataOut,
    ProductionDataUpdate,
    SalesDataCreate,
    SalesDataOut,
    SalesDataUpdate,
)
from app.services import import_service, log_service

router = APIRouter(tags=["产销数据管理"])


def _page(payload: dict, page: int, page_size: int) -> dict:
    return {"items": payload["items"], "total": payload["total"], "page": page, "page_size": page_size}


# ================= 产量 =================
class ProductionRepo(BaseRepository[ProductionData]):
    model = ProductionData
    load_options = (
        joinedload(ProductionData.production_area),
        joinedload(ProductionData.product),
    )


@router.get("/production", response_model=ApiResponse[PageData[ProductionDataOut]])
def list_production(
    page: int = 1,
    page_size: int = 20,
    production_area_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = ProductionRepo(db)
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={"production_area_id": production_area_id},
        date_range=(start, end),
        date_field=ProductionData.date,
        order_by=ProductionData.date.desc(),
    )
    return ok(
        _page(
            {
                "items": [ProductionDataOut.model_validate(i).model_dump() for i in items],
                "total": total,
            },
            page,
            page_size,
        )
    )


@router.post("/production", response_model=ApiResponse[ProductionDataOut])
def create_production(
    body: ProductionDataCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(ProductionArea, body.production_area_id):
        raise NotFoundError("产地不存在")
    obj = ProductionRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(ProductionDataOut.model_validate(obj).model_dump())


@router.put("/production/{data_id}", response_model=ApiResponse[ProductionDataOut])
def update_production(
    data_id: int, body: ProductionDataUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = ProductionRepo(db).update(data_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(ProductionDataOut.model_validate(obj).model_dump())


@router.delete("/production/{data_id}")
def delete_production(
    data_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    ProductionRepo(db).delete(data_id)
    db.commit()
    return ok()


# ================= 销量 =================
class SalesRepo(BaseRepository[SalesData]):
    model = SalesData
    load_options = (joinedload(SalesData.region), joinedload(SalesData.product))


@router.get("/sales", response_model=ApiResponse[PageData[SalesDataOut]])
def list_sales(
    page: int = 1,
    page_size: int = 20,
    region_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = SalesRepo(db)
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={"region_id": region_id},
        date_range=(start, end),
        date_field=SalesData.date,
        order_by=SalesData.date.desc(),
    )
    return ok(
        _page(
            {
                "items": [SalesDataOut.model_validate(i).model_dump() for i in items],
                "total": total,
            },
            page,
            page_size,
        )
    )


@router.post("/sales", response_model=ApiResponse[SalesDataOut])
def create_sales(
    body: SalesDataCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(Region, body.region_id):
        raise NotFoundError("销售地区不存在")
    obj = SalesRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(SalesDataOut.model_validate(obj).model_dump())


@router.put("/sales/{data_id}", response_model=ApiResponse[SalesDataOut])
def update_sales(
    data_id: int, body: SalesDataUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = SalesRepo(db).update(data_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(SalesDataOut.model_validate(obj).model_dump())


@router.delete("/sales/{data_id}")
def delete_sales(
    data_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    SalesRepo(db).delete(data_id)
    db.commit()
    return ok()


# ================= 价格 =================
class PriceRepo(BaseRepository[PriceData]):
    model = PriceData
    load_options = (
        joinedload(PriceData.production_area),
        joinedload(PriceData.product),
    )


@router.get("/prices", response_model=ApiResponse[PageData[PriceDataOut]])
def list_prices(
    page: int = 1,
    page_size: int = 20,
    production_area_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = PriceRepo(db)
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={"production_area_id": production_area_id},
        date_range=(start, end),
        date_field=PriceData.date,
        order_by=PriceData.date.desc(),
    )
    return ok(
        _page(
            {
                "items": [PriceDataOut.model_validate(i).model_dump() for i in items],
                "total": total,
            },
            page,
            page_size,
        )
    )


@router.post("/prices", response_model=ApiResponse[PriceDataOut])
def create_price(
    body: PriceDataCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(ProductionArea, body.production_area_id):
        raise NotFoundError("产地不存在")
    obj = PriceRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(PriceDataOut.model_validate(obj).model_dump())


@router.put("/prices/{data_id}", response_model=ApiResponse[PriceDataOut])
def update_price(
    data_id: int, body: PriceDataUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = PriceRepo(db).update(data_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(PriceDataOut.model_validate(obj).model_dump())


@router.delete("/prices/{data_id}")
def delete_price(
    data_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    PriceRepo(db).delete(data_id)
    db.commit()
    return ok()


# ================= 全国市场 =================
class MarketRepo(BaseRepository[MarketData]):
    model = MarketData
    load_options = (joinedload(MarketData.region),)


@router.get("/markets", response_model=ApiResponse[PageData[MarketDataOut]])
def list_markets(
    page: int = 1,
    page_size: int = 20,
    region_id: int | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = MarketRepo(db)
    date_range = (date(year, 1, 1), date(year, 12, 31)) if year else None
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={"region_id": region_id},
        date_range=date_range,
        date_field=MarketData.date,
        order_by=MarketData.date.desc(),
    )
    return ok(
        _page(
            {
                "items": [MarketDataOut.model_validate(i).model_dump() for i in items],
                "total": total,
            },
            page,
            page_size,
        )
    )


@router.post("/markets", response_model=ApiResponse[MarketDataOut])
def create_market(
    body: MarketDataCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(Region, body.region_id):
        raise NotFoundError("销售省份不存在")
    obj = MarketRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(MarketDataOut.model_validate(obj).model_dump())


@router.put("/markets/{data_id}", response_model=ApiResponse[MarketDataOut])
def update_market(
    data_id: int, body: MarketDataUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = MarketRepo(db).update(data_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(MarketDataOut.model_validate(obj).model_dump())


@router.delete("/markets/{data_id}")
def delete_market(
    data_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    MarketRepo(db).delete(data_id)
    db.commit()
    return ok()


# ================= 病虫害 =================
class PestTypeRepo(BaseRepository[PestDiseaseType]):
    model = PestDiseaseType


class PestRecordRepo(BaseRepository[PestDiseaseRecord]):
    model = PestDiseaseRecord
    load_options = (
        joinedload(PestDiseaseRecord.production_area),
        joinedload(PestDiseaseRecord.pest_disease_type),
    )


@router.get("/pest-types", response_model=ApiResponse[list[PestTypeOut]])
def list_pest_types(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    items = db.scalars(select(PestDiseaseType).order_by(PestDiseaseType.id)).all()
    return ok([PestTypeOut.model_validate(i).model_dump() for i in items])


@router.post("/pest-types", response_model=ApiResponse[PestTypeOut])
def create_pest_type(
    body: PestTypeCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = PestTypeRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(PestTypeOut.model_validate(obj).model_dump())


@router.get("/pest-records", response_model=ApiResponse[PageData[PestRecordOut]])
def list_pest_records(
    page: int = 1,
    page_size: int = 20,
    production_area_id: int | None = None,
    pest_disease_type_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = PestRecordRepo(db)
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={
            "production_area_id": production_area_id,
            "pest_disease_type_id": pest_disease_type_id,
        },
        date_range=(start, end),
        date_field=PestDiseaseRecord.date,
        order_by=PestDiseaseRecord.date.desc(),
    )
    return ok(
        _page(
            {
                "items": [PestRecordOut.model_validate(i).model_dump() for i in items],
                "total": total,
            },
            page,
            page_size,
        )
    )


@router.post("/pest-records", response_model=ApiResponse[PestRecordOut])
def create_pest_record(
    body: PestRecordCreate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(ProductionArea, body.production_area_id):
        raise NotFoundError("产地不存在")
    if not db.get(PestDiseaseType, body.pest_disease_type_id):
        raise NotFoundError("病虫害类型不存在")
    obj = PestRecordRepo(db).create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(PestRecordOut.model_validate(obj).model_dump())


@router.put("/pest-records/{data_id}", response_model=ApiResponse[PestRecordOut])
def update_pest_record(
    data_id: int, body: PestRecordUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    obj = PestRecordRepo(db).update(data_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(PestRecordOut.model_validate(obj).model_dump())


@router.delete("/pest-records/{data_id}")
def delete_pest_record(
    data_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    PestRecordRepo(db).delete(data_id)
    db.commit()
    return ok()


# ================= 数据导入 =================
@router.post("/import/preview")
async def import_preview(
    request: Request,
    target: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("operator")),
):
    content = await file.read()
    result = import_service.preview(db, content, file.filename or "", target)
    log_service.record(
        db,
        f"预览导入 {target}（{file.filename}）",
        "import",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
        result="success" if result["error_count"] == 0 else "failure",
    )
    db.commit()
    return ok(result)


@router.post("/import/commit")
async def import_commit(
    request: Request,
    target: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("operator")),
):
    content = await file.read()
    result = import_service.commit(db, content, file.filename or "", target)
    log_service.record(
        db,
        f"导入 {target} 数据 {result['imported']} 条（{file.filename}）",
        "import",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
    )
    db.commit()
    return ok(result)
