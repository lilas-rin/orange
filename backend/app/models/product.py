"""产品/品种表。"""
from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="产品名称")
    variety: Mapped[str | None] = mapped_column(String(64), comment="品种，如纽荷尔/朋娜")
    grade: Mapped[str | None] = mapped_column(String(32), comment="产品等级")
    specification: Mapped[str | None] = mapped_column(String(64), comment="产品规格")
    listing_time: Mapped[str | None] = mapped_column(String(32), comment="上市时间")
    description: Mapped[str | None] = mapped_column(Text, comment="产品特点")
    production_area_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("production_area.id"), comment="所属产地"
    )

    production_area = relationship("ProductionArea")

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None
