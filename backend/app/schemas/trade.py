"""产量/销量/价格/市场/病虫害 数据的入参与出参。"""
from datetime import date as date_t
from decimal import Decimal

from pydantic import BaseModel, Field


# ---- 产量 ----
class ProductionDataCreate(BaseModel):
    production_area_id: int
    product_id: int | None = None
    date: date_t
    planting_area: Decimal | None = None
    production: Decimal = Field(gt=0)
    yield_per_area: Decimal | None = None


class ProductionDataUpdate(BaseModel):
    production_area_id: int | None = None
    product_id: int | None = None
    date: date_t | None = None
    planting_area: Decimal | None = None
    production: Decimal | None = Field(default=None, gt=0)
    yield_per_area: Decimal | None = None


class ProductionDataOut(BaseModel):
    id: int
    production_area_id: int
    production_area_name: str | None = None
    product_id: int | None
    date: date_t
    planting_area: Decimal | None
    production: Decimal
    yield_per_area: Decimal | None

    model_config = {"from_attributes": True}


# ---- 销量 ----
class SalesDataCreate(BaseModel):
    region_id: int
    product_id: int | None = None
    date: date_t
    sales_volume: Decimal = Field(gt=0)
    sales_amount: Decimal = Field(gt=0)
    sales_channel: str | None = Field(default=None, max_length=32)


class SalesDataUpdate(BaseModel):
    region_id: int | None = None
    product_id: int | None = None
    date: date_t | None = None
    sales_volume: Decimal | None = Field(default=None, gt=0)
    sales_amount: Decimal | None = Field(default=None, gt=0)
    sales_channel: str | None = Field(default=None, max_length=32)


class SalesDataOut(BaseModel):
    id: int
    region_id: int
    region_name: str | None = None
    product_id: int | None
    date: date_t
    sales_volume: Decimal
    sales_amount: Decimal
    sales_channel: str | None

    model_config = {"from_attributes": True}


# ---- 价格 ----
class PriceDataCreate(BaseModel):
    production_area_id: int
    product_id: int | None = None
    date: date_t
    average_price: Decimal = Field(gt=0)
    highest_price: Decimal | None = Field(default=None, gt=0)
    lowest_price: Decimal | None = Field(default=None, gt=0)
    wholesale_price: Decimal | None = Field(default=None, gt=0)


class PriceDataUpdate(BaseModel):
    production_area_id: int | None = None
    product_id: int | None = None
    date: date_t | None = None
    average_price: Decimal | None = Field(default=None, gt=0)
    highest_price: Decimal | None = Field(default=None, gt=0)
    lowest_price: Decimal | None = Field(default=None, gt=0)
    wholesale_price: Decimal | None = Field(default=None, gt=0)


class PriceDataOut(BaseModel):
    id: int
    production_area_id: int
    production_area_name: str | None = None
    product_id: int | None
    date: date_t
    average_price: Decimal
    highest_price: Decimal | None
    lowest_price: Decimal | None
    wholesale_price: Decimal | None

    model_config = {"from_attributes": True}


# ---- 市场 ----
class MarketDataCreate(BaseModel):
    region_id: int
    date: date_t
    sales_volume: Decimal = Field(gt=0)
    sales_amount: Decimal = Field(gt=0)
    market_share: Decimal | None = Field(default=None, ge=0, le=100)
    market_level: str = Field(pattern="^(core|main|potential)$")
    growth_rate: Decimal | None = None


class MarketDataUpdate(BaseModel):
    region_id: int | None = None
    date: date_t | None = None
    sales_volume: Decimal | None = Field(default=None, gt=0)
    sales_amount: Decimal | None = Field(default=None, gt=0)
    market_share: Decimal | None = Field(default=None, ge=0, le=100)
    market_level: str | None = Field(default=None, pattern="^(core|main|potential)$")
    growth_rate: Decimal | None = None


class MarketDataOut(BaseModel):
    id: int
    region_id: int
    region_name: str | None = None
    date: date_t
    sales_volume: Decimal
    sales_amount: Decimal
    market_share: Decimal | None
    market_level: str
    growth_rate: Decimal | None

    model_config = {"from_attributes": True}


# ---- 病虫害类型 ----
class PestTypeCreate(BaseModel):
    name: str = Field(max_length=64)
    type: str = Field(pattern="^(disease|pest)$")
    description: str | None = None
    prevention_method: str | None = None


class PestTypeOut(BaseModel):
    id: int
    name: str
    type: str
    description: str | None
    prevention_method: str | None

    model_config = {"from_attributes": True}


# ---- 病虫害记录 ----
class PestRecordCreate(BaseModel):
    production_area_id: int
    pest_disease_type_id: int
    date: date_t
    affected_area: Decimal | None = Field(default=None, ge=0)
    severity: str = Field(pattern="^(mild|moderate|severe)$")
    production_impact: Decimal | None = None
    prevention_cost: Decimal | None = None
    description: str | None = None


class PestRecordUpdate(BaseModel):
    production_area_id: int | None = None
    pest_disease_type_id: int | None = None
    date: date_t | None = None
    affected_area: Decimal | None = Field(default=None, ge=0)
    severity: str | None = Field(default=None, pattern="^(mild|moderate|severe)$")
    production_impact: Decimal | None = None
    prevention_cost: Decimal | None = None
    description: str | None = None


class PestRecordOut(BaseModel):
    id: int
    production_area_id: int
    production_area_name: str | None = None
    pest_disease_type_id: int
    pest_disease_type_name: str | None = None
    date: date_t
    affected_area: Decimal | None
    severity: str
    production_impact: Decimal | None
    prevention_cost: Decimal | None
    description: str | None

    model_config = {"from_attributes": True}
