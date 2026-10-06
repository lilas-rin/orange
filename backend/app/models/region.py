"""区域表：全国/省/市/县区 树形结构，含行政区划码（地图钻取用）。"""
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Region(Base, TimestampMixin):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="区域名称")
    type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="类型: country/province/city/county"
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("region.id"), nullable=True, comment="上级区域"
    )
    adcode: Mapped[str | None] = mapped_column(
        String(12), nullable=True, comment="行政区划码（地图钻取）"
    )
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    boundary: Mapped[str | None] = mapped_column(Text, comment="地图边界信息(JSON)")

    parent = relationship("Region", remote_side=[id], backref="children")
