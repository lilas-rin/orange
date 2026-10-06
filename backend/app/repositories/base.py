"""通用仓储层：泛型 CRUD，避免各路由手写重复查询；列表查询统一 joinedload 防 N+1。"""
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[Base]
    """joinedload 的关系属性列表，子类按需覆盖。"""
    load_options: tuple = ()

    def __init__(self, db: Session):
        self.db = db

    def get(self, obj_id: int) -> ModelT:
        stmt = select(self.model).where(self.model.id == obj_id)
        for opt in self.load_options:
            stmt = stmt.options(opt)
        obj = self.db.scalar(stmt)
        if not obj:
            raise NotFoundError(f"{self.model.__name__} id={obj_id} 不存在")
        return obj

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
        date_range: tuple | None = None,
        date_field: Any = None,
    ) -> tuple[list[ModelT], int]:
        stmt = select(self.model)
        for opt in self.load_options:
            stmt = stmt.options(opt)
        if filters:
            for field, value in filters.items():
                if value is not None:
                    col = getattr(self.model, field)
                    if isinstance(value, str) and value:
                        stmt = stmt.where(col.like(f"%{value}%"))
                    else:
                        stmt = stmt.where(col == value)
        if date_range and date_field is not None:
            start, end = date_range
            if start is not None:
                stmt = stmt.where(date_field >= start)
            if end is not None:
                stmt = stmt.where(date_field <= end)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        total = self.db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        items = list(
            self.db.scalars(
                stmt.offset((page - 1) * page_size).limit(page_size)
            ).all()
        )
        return items, int(total or 0)

    def create(self, data: dict) -> ModelT:
        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, obj_id: int, data: dict) -> ModelT:
        obj = self.get(obj_id)
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        self.db.flush()
        return obj

    def delete(self, obj_id: int) -> None:
        obj = self.get(obj_id)
        self.db.delete(obj)
        self.db.flush()
