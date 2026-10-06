"""系统管理：用户 CRUD、角色列表、操作日志。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Role, User
from app.schemas.common import ApiResponse, PageData, ok
from app.schemas.system import OperationLogOut, RoleOut, UserCreate, UserOut, UserUpdate
from app.services import log_service

router = APIRouter(prefix="/system", tags=["系统管理"])


# ---------- 用户 ----------
@router.get("/users", response_model=ApiResponse[PageData[UserOut]])
def list_users(
    page: int = 1,
    page_size: int = 20,
    username: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    stmt = select(User).options(joinedload(User.role)).order_by(User.id)
    if username:
        stmt = stmt.where(User.username.like(f"%{username}%"))
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return ok(
        PageData[UserOut](
            items=[UserOut.model_validate(u) for u in items],
            total=total, page=page, page_size=page_size,
        ).model_dump()
    )


@router.post("/users", response_model=ApiResponse[UserOut])
def create_user(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    if db.scalar(select(User).where(User.username == body.username)):
        raise ConflictError(f"用户名 {body.username} 已存在")
    role = db.get(Role, body.role_id)
    if not role:
        raise NotFoundError("角色不存在")
    obj = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        role_id=body.role_id,
        status=body.status,
    )
    db.add(obj)
    db.flush()
    log_service.record(
        db, f"新增用户 {obj.username}", "system",
        user_id=user.id, method="POST", path=str(request.url.path),
    )
    db.commit()
    db.refresh(obj)
    return ok(UserOut.model_validate(obj).model_dump())


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("用户不存在")
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        if not data["password"]:
            raise ValidationError("密码不能为空")
        obj.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(obj, k, v)
    db.flush()
    log_service.record(
        db, f"修改用户 {obj.username}", "system",
        user_id=admin.id, method="PUT", path=str(request.url.path),
    )
    db.commit()
    db.refresh(obj)
    return ok(UserOut.model_validate(obj).model_dump())


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("用户不存在")
    if obj.id == admin.id:
        raise ValidationError("不能删除当前登录用户")
    username = obj.username
    db.delete(obj)
    db.flush()
    log_service.record(
        db, f"删除用户 {username}", "system",
        user_id=admin.id, method="DELETE", path=str(request.url.path),
    )
    db.commit()
    return ok()


# ---------- 角色 ----------
@router.get("/roles", response_model=ApiResponse[list[RoleOut]])
def list_roles(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    roles = db.scalars(select(Role).order_by(Role.id)).all()
    return ok([RoleOut.model_validate(r).model_dump() for r in roles])


# ---------- 操作日志 ----------
@router.get("/logs", response_model=ApiResponse[PageData[OperationLogOut]])
def list_logs(
    page: int = 1,
    page_size: int = 20,
    module: str | None = None,
    result: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator")),
):
    items, total = log_service.list_logs(db, page, page_size, module, result)
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
