"""产地表：具体脐橙生产区域及四维能力分（价格分在评价表）。"""
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProductionArea(Base, TimestampMixin):
    __tablename__ = "production_area"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="产地名称")
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("region.id"), nullable=False, comment="所属县区"
    )
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    planting_area: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), comment="种植面积(亩)"
    )
    main_variety: Mapped[str | None] = mapped_column(String(64), comment="主要品种")
    production_technology_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), comment="生产技术分"
    )
    transport_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="运输能力分")
    supply_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="供应能力分")
    benefit_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), comment="综合效益分")
    description: Mapped[str | None] = mapped_column(Text, comment="产地特点")

    region = relationship("Region")

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None
