"""预测/决策/分析/大屏 出参。"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PredictionResultOut(BaseModel):
    id: int
    region_id: int | None
    region_name: str | None = None
    production_area_id: int | None
    production_area_name: str | None = None
    prediction_type: str
    prediction_date: date
    target_date: date
    predicted_value: Decimal | None
    lower_bound: Decimal | None
    upper_bound: Decimal | None
    risk_level: str | None
    model_name: str
    model_version: str

    model_config = {"from_attributes": True}


class ModelInfoOut(BaseModel):
    id: int
    model_name: str
    model_type: str
    version: str
    target: str | None
    algorithm: str | None
    training_dataset: str | None
    evaluation_metric: str | None
    accuracy: Decimal | None
    status: str

    model_config = {"from_attributes": True}


class DecisionAdviceOut(BaseModel):
    id: int
    region_id: int | None
    region_name: str | None = None
    production_area_id: int | None
    production_area_name: str | None = None
    advice_type: str
    risk_level: str | None
    title: str
    content: str
    related_prediction_id: int | None
    created_at: date | None = None

    model_config = {"from_attributes": True}


# ---- 大屏 ----
class ScreenKpi(BaseModel):
    total_production: float
    total_sales_volume: float
    total_sales_amount: float
    avg_wholesale_price: float
    production_sales_rate: float
    yoy_growth_rate: float
    province_count: int


class ScreenProvince(BaseModel):
    name: str
    sales_volume: float
    sales_amount: float
    market_level: str
    growth_rate: float
    longitude: float | None = None
    latitude: float | None = None


class ScreenFlow(BaseModel):
    from_name: str = "赣州"
    to_name: str
    value: float


class PricePoint(BaseModel):
    date: str
    value: float
    is_forecast: bool = False
    lower: float | None = None
    upper: float | None = None


class CountySummary(BaseModel):
    region_id: int
    name: str
    adcode: str | None
    production: float
    sales_volume: float
    sales_amount: float
    avg_price: float
    production_sales_rate: float
    risk_level: str
    planting_area: float
    area_count: int
    score: float | None = None


class EvaluationRadar(BaseModel):
    area_id: int
    name: str
    price: float
    technology: float
    transport: float
    supply: float
    benefit: float
    total: float
