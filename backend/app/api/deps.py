"""API 依赖：数据库会话、当前用户、角色鉴权。"""
import jwt as pyjwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_token(token, "access")
    except pyjwt.PyJWTError:
        raise AuthError("访问令牌无效或已过期") from None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.status:
        raise AuthError("用户不存在或已禁用")
    return user


def require_roles(*codes: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        role = user.role.code if user.role else ""
        if role == "admin" or role in codes:
            return user
        raise PermissionDeniedError(f"需要角色权限: {', '.join(codes)}")

    return checker
