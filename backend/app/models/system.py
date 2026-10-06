"""系统表：用户/角色/权限/刷新令牌/操作日志。"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Table,
    Column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("role.id"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("permission.id"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False, comment="角色名")
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, comment="admin/operator/viewer")
    description: Mapped[str | None] = mapped_column(String(128))

    permissions = relationship("Permission", secondary=role_permission, lazy="selectin")


class Permission(Base, TimestampMixin):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(128))


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(64))
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("role.id"), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=True, comment="启用/禁用")

    role = relationship("Role", lazy="joined")

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role else None


class RefreshToken(Base):
    """服务端存储的刷新令牌（支持吊销）。"""

    __tablename__ = "refresh_token"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class OperationLog(Base):
    __tablename__ = "operation_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user.id"))
    operation: Mapped[str] = mapped_column(String(128), comment="操作描述")
    module: Mapped[str | None] = mapped_column(String(64), comment="模块")
    request_method: Mapped[str | None] = mapped_column(String(8))
    request_path: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str | None] = mapped_column(String(16), comment="success/failure")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
