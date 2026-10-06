"""基础数据管理：区域（树）、产地、产品 CRUD。"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import ProductionArea, Product, Region, User
from app.repositories.base import BaseRepository
from app.schemas.base_data import (
    ProductionAreaCreate,
    ProductionAreaOut,
    ProductionAreaUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    RegionCreate,
    RegionOut,
    RegionUpdate,
)
from app.schemas.common import ApiResponse, PageData, ok

router = APIRouter(prefix="/base-data", tags=["基础数据管理"])


# ---------- 区域 ----------
class RegionRepo(BaseRepository[Region]):
    model = Region
    load_options = ()


@router.get("/regions", response_model=ApiResponse[list[RegionOut]])
def list_regions(
    type: str | None = None,
    parent_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Region).order_by(Region.id)
    if type:
        stmt = stmt.where(Region.type == type)
    if parent_id is not None:
        stmt = stmt.where(Region.parent_id == parent_id)
    items = db.scalars(stmt).all()
    return ok([RegionOut.model_validate(r).model_dump() for r in items])


@router.get("/regions/tree")
def region_tree(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """区域树（全国→省→市→县区）。"""
    regions = db.scalars(select(Region).order_by(Region.id)).all()
    nodes = {r.id: {**RegionOut.model_validate(r).model_dump(), "children": []} for r in regions}
    roots = []
    for r in regions:
        node = nodes[r.id]
        if r.parent_id and r.parent_id in nodes:
            nodes[r.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return ok(roots)


@router.post("/regions", response_model=ApiResponse[RegionOut])
def create_region(
    body: RegionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = RegionRepo(db)
    obj = repo.create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(RegionOut.model_validate(obj).model_dump())


@router.put("/regions/{region_id}", response_model=ApiResponse[RegionOut])
def update_region(
    region_id: int,
    body: RegionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = RegionRepo(db)
    obj = repo.update(region_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(RegionOut.model_validate(obj).model_dump())


@router.delete("/regions/{region_id}")
def delete_region(
    region_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if db.scalar(select(Region.id).where(Region.parent_id == region_id)):
        raise NotFoundError("该区域下存在子区域，无法删除")
    repo = RegionRepo(db)
    repo.delete(region_id)
    db.commit()
    return ok()


# ---------- 产地 ----------
class AreaRepo(BaseRepository[ProductionArea]):
    model = ProductionArea
    load_options = (joinedload(ProductionArea.region),)


@router.get("/areas", response_model=ApiResponse[PageData[ProductionAreaOut]])
def list_areas(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    region_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = AreaRepo(db)
    items, total = repo.list(
        page=page,
        page_size=page_size,
        filters={"name": name, "region_id": region_id},
        order_by=ProductionArea.id,
    )
    return ok(
        {
            "items": [ProductionAreaOut.model_validate(a).model_dump() for a in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/areas", response_model=ApiResponse[ProductionAreaOut])
def create_area(
    body: ProductionAreaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    if not db.get(Region, body.region_id):
        raise NotFoundError("所属县区不存在")
    repo = AreaRepo(db)
    obj = repo.create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(ProductionAreaOut.model_validate(obj).model_dump())


@router.put("/areas/{area_id}", response_model=ApiResponse[ProductionAreaOut])
def update_area(
    area_id: int,
    body: ProductionAreaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = AreaRepo(db)
    obj = repo.update(area_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(ProductionAreaOut.model_validate(obj).model_dump())


@router.delete("/areas/{area_id}")
def delete_area(
    area_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = AreaRepo(db)
    repo.delete(area_id)
    db.commit()
    return ok()


# ---------- 产品 ----------
class ProductRepo(BaseRepository[Product]):
    model = Product
    load_options = (joinedload(Product.production_area),)


@router.get("/products", response_model=ApiResponse[PageData[ProductOut]])
def list_products(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = ProductRepo(db)
    items, total = repo.list(
        page=page, page_size=page_size, filters={"name": name}, order_by=Product.id
    )
    return ok(
        {
            "items": [ProductOut.model_validate(p).model_dump() for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/products", response_model=ApiResponse[ProductOut])
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = ProductRepo(db)
    obj = repo.create(body.model_dump())
    db.commit()
    db.refresh(obj)
    return ok(ProductOut.model_validate(obj).model_dump())


@router.put("/products/{product_id}", response_model=ApiResponse[ProductOut])
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = ProductRepo(db)
    obj = repo.update(product_id, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return ok(ProductOut.model_validate(obj).model_dump())


@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    repo = ProductRepo(db)
    repo.delete(product_id)
    db.commit()
    return ok()
