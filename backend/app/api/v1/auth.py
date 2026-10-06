from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserInfo
from app.schemas.common import ApiResponse, ok
from app.services import auth_service, log_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[TokenPair])
def login(
    body: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    tokens, user = auth_service.login(db, body.username, body.password)
    log_service.record(
        db,
        operation=f"用户 {user.username} 登录",
        module="auth",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return ok(tokens)


@router.post("/refresh", response_model=ApiResponse[TokenPair])
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return ok(auth_service.refresh(db, body.refresh_token))


@router.post("/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    auth_service.logout(db, body.refresh_token)
    db.commit()
    return ok()


@router.get("/me", response_model=ApiResponse[UserInfo])
def me(user: User = Depends(get_current_user)):
    return ok(auth_service.user_info(user))
