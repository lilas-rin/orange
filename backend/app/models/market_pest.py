"""市场数据表 + 病虫害类型/记录表。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class MarketData(Base, TimestampMixin):
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("region.id"), nullable=False, comment="销售省份"
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    sales_volume: Mapped[Decimal] = mapped_column(Numeric(12, 2), comment="销售数量(吨)")
    sales_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), comment="销售额(万元)")
    market_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), comment="市场占比(%)")
    market_level: Mapped[str] = mapped_column(
        String(16), comment="等级: core核心/main主要/potential潜力"
    )
    growth_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), comment="同比增长率(%)")

    region = relationship("Region")

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None


class PestDiseaseType(Base, TimestampMixin):
    __tablename__ = "pest_disease_type"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="病虫害名称")
    type: Mapped[str] = mapped_column(String(16), nullable=False, comment="disease病害/pest虫害")
    description: Mapped[str | None] = mapped_column(Text)
    prevention_method: Mapped[str | None] = mapped_column(Text, comment="防治措施")


class PestDiseaseRecord(Base, TimestampMixin):
    __tablename__ = "pest_disease_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    production_area_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production_area.id"), nullable=False
    )
    pest_disease_type_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pest_disease_type.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="发生时间")
    affected_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), comment="影响面积(亩)")
    severity: Mapped[str] = mapped_column(String(16), comment="影响程度: mild/moderate/severe")
    production_impact: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), comment="产量影响(吨)")
    prevention_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), comment="防治成本(万元)")
    description: Mapped[str | None] = mapped_column(Text)

    production_area = relationship("ProductionArea")
    pest_disease_type = relationship("PestDiseaseType")

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None

    @property
    def pest_disease_type_name(self) -> str | None:
        return self.pest_disease_type.name if self.pest_disease_type else None
