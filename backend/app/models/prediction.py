"""产地评价表 + 预测结果表 + 模型信息表 + 决策建议表。"""
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProductionEvaluation(Base, TimestampMixin):
    __tablename__ = "production_evaluation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    production_area_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("production_area.id"), nullable=False
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="价格分")
    technology_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    transport_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    supply_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    benefit_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), comment="综合竞争力评分")

    production_area = relationship("ProductionArea")


class PredictionResult(Base, TimestampMixin):
    __tablename__ = "prediction_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("region.id"))
    production_area_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("production_area.id")
    )
    prediction_type: Mapped[str] = mapped_column(
        String(32),
        comment="price/production/sales/market_demand/pest_disease",
    )
    prediction_date: Mapped[date] = mapped_column(Date, comment="预测生成时间")
    target_date: Mapped[date] = mapped_column(Date, comment="预测目标时间")
    predicted_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    lower_bound: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    risk_level: Mapped[str | None] = mapped_column(
        String(16), comment="low低/medium中/high高（病虫害预测用）"
    )
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(32))

    region = relationship("Region")
    production_area = relationship("ProductionArea")

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None


class ModelInfo(Base, TimestampMixin):
    __tablename__ = "model_info"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), comment="price/pest_disease")
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str | None] = mapped_column(String(64), comment="预测目标")
    algorithm: Mapped[str | None] = mapped_column(String(64))
    training_dataset: Mapped[str | None] = mapped_column(String(255))
    evaluation_metric: Mapped[str | None] = mapped_column(String(64), comment="评估指标名")
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), comment="指标值")
    model_path: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="active", comment="active/retired")


class DecisionAdvice(Base, TimestampMixin):
    __tablename__ = "decision_advice"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    region_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("region.id"))
    production_area_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("production_area.id")
    )
    advice_type: Mapped[str] = mapped_column(String(32), comment="price/pest_disease/market/supply")
    risk_level: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    related_prediction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("prediction_result.id")
    )

    region = relationship("Region")
    production_area = relationship("ProductionArea")

    @property
    def region_name(self) -> str | None:
        return self.region.name if self.region else None

    @property
    def production_area_name(self) -> str | None:
        return self.production_area.name if self.production_area else None
