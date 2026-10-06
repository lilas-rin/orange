"""产量/销量/价格 三类业务数据表。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProductionData(Base, TimestampMixin):
    __tablename__ = "production_data"
    __table_args__ = (
        UniqueConstraint(
            "production_area_id", "product_id", "date", name="uq_production_area_product_date"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    production_area_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production_area.id"), nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="生产时间")
    planting_area: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), comment="种植面积(亩)")
    production: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="产量(吨)")
    yield_per_area: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), comment="单位面积产量(吨/亩)"
    )

    production_area = relationship("ProductionArea")
    product = relationship("Product")

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None

    @property
    def product_name(self) -> str | None:
        return self.product.name if self.product else None


class SalesData(Base, TimestampMixin):
    __tablename__ = "sales_data"
    __table_args__ = (
        UniqueConstraint("region_id", "product_id", "date", "sales_channel", name="uq_sales_row"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("region.id"), nullable=False, comment="销售地区"
    )
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False, comment="销售时间")
    sales_volume: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, comment="销量(吨)")
    sales_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, comment="销售额(万元)"
    )
    sales_channel: Mapped[str | None] = mapped_column(
        String(32), comment="渠道: 批发/电商/出口/商超"
    )

    region = relationship("Region")
    product = relationship("Product")

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None

    @property
    def product_name(self) -> str | None:
        return self.product.name if self.product else None


class PriceData(Base, TimestampMixin):
    __tablename__ = "price_data"
    __table_args__ = (
        UniqueConstraint(
            "production_area_id", "product_id", "date", name="uq_price_area_product_date"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    production_area_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production_area.id"), nullable=False, comment="产地"
    )
    product_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("product.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, comment="平均价(元/kg)")
    highest_price: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    lowest_price: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), comment="批发价(元/kg)")

    production_area = relationship("ProductionArea")
    product = relationship("Product")

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None

    @property
    def product_name(self) -> str | None:
        return self.product.name if self.product else None
