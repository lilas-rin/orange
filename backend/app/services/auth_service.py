"""认证服务：登录、刷新令牌轮换（服务端存储可吊销）、登出。"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.schemas.auth import TokenPair, UserInfo


def _issue_tokens(db: Session, user: User) -> TokenPair:
    jti = uuid.uuid4().hex
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.flush()
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id, jti),
    )


def login(db: Session, username: str, password: str) -> tuple[TokenPair, User]:
    user = db.scalar(select(User).where(User.username == username))
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")
    if not user.status:
        raise PermissionDeniedError("账号已被禁用")
    return _issue_tokens(db, user), user


def refresh(db: Session, refresh_token: str) -> TokenPair:
    import jwt as pyjwt

    try:
        payload = decode_token(refresh_token, "refresh")
    except pyjwt.PyJWTError:
        raise AuthError("刷新令牌无效或已过期") from None
    record = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))
    if not record or record.revoked or record.expires_at < datetime.now(timezone.utc):
        raise AuthError("刷新令牌无效或已过期")
    user = db.scalar(select(User).where(User.id == int(payload["sub"])))
    if not user or not user.status:
        raise AuthError("用户不存在或已禁用")
    record.revoked = True  # 轮换：旧刷新令牌立即失效
    return _issue_tokens(db, user)


def logout(db: Session, refresh_token: str) -> None:
    import jwt as pyjwt

    try:
        payload = decode_token(refresh_token, "refresh")
    except pyjwt.PyJWTError:
        return
    record = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))
    if record:
        record.revoked = True
    db.flush()


def user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        role=user.role.code if user.role else "viewer",
        permissions=[p.code for p in user.role.permissions] if user.role else [],
    )
