"""区域/产地/产品 的入参与出参。"""
from decimal import Decimal

from pydantic import BaseModel, Field


# ---- 区域 ----
class RegionCreate(BaseModel):
    name: str = Field(max_length=64)
    type: str = Field(pattern="^(country|province|city|county)$")
    parent_id: int | None = None
    adcode: str | None = Field(default=None, max_length=12)
    longitude: Decimal | None = None
    latitude: Decimal | None = None


class RegionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    type: str | None = Field(default=None, pattern="^(country|province|city|county)$")
    parent_id: int | None = None
    adcode: str | None = Field(default=None, max_length=12)
    longitude: Decimal | None = None
    latitude: Decimal | None = None


class RegionOut(BaseModel):
    id: int
    name: str
    type: str
    parent_id: int | None
    adcode: str | None
    longitude: Decimal | None
    latitude: Decimal | None

    model_config = {"from_attributes": True}


# ---- 产地 ----
class ProductionAreaCreate(BaseModel):
    name: str = Field(max_length=64)
    region_id: int
    longitude: Decimal | None = None
    latitude: Decimal | None = None
    planting_area: Decimal | None = None
    main_variety: str | None = Field(default=None, max_length=64)
    production_technology_score: Decimal | None = Field(default=None, ge=0, le=100)
    transport_score: Decimal | None = Field(default=None, ge=0, le=100)
    supply_score: Decimal | None = Field(default=None, ge=0, le=100)
    benefit_score: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None


class ProductionAreaUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    region_id: int | None = None
    longitude: Decimal | None = None
    latitude: Decimal | None = None
    planting_area: Decimal | None = None
    main_variety: str | None = Field(default=None, max_length=64)
    production_technology_score: Decimal | None = Field(default=None, ge=0, le=100)
    transport_score: Decimal | None = Field(default=None, ge=0, le=100)
    supply_score: Decimal | None = Field(default=None, ge=0, le=100)
    benefit_score: Decimal | None = Field(default=None, ge=0, le=100)
    description: str | None = None


class ProductionAreaOut(BaseModel):
    id: int
    name: str
    region_id: int
    region_name: str | None = None
    longitude: Decimal | None
    latitude: Decimal | None
    planting_area: Decimal | None
    main_variety: str | None
    production_technology_score: Decimal | None
    transport_score: Decimal | None
    supply_score: Decimal | None
    benefit_score: Decimal | None
    description: str | None

    model_config = {"from_attributes": True}


# ---- 产品 ----
class ProductCreate(BaseModel):
    name: str = Field(max_length=64)
    variety: str | None = Field(default=None, max_length=64)
    grade: str | None = Field(default=None, max_length=32)
    specification: str | None = Field(default=None, max_length=64)
    listing_time: str | None = Field(default=None, max_length=32)
    description: str | None = None
    production_area_id: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    variety: str | None = Field(default=None, max_length=64)
    grade: str | None = Field(default=None, max_length=32)
    specification: str | None = Field(default=None, max_length=64)
    listing_time: str | None = Field(default=None, max_length=32)
    description: str | None = None
    production_area_id: int | None = None


class ProductOut(BaseModel):
    id: int
    name: str
    variety: str | None
    grade: str | None
    specification: str | None
    listing_time: str | None
    description: str | None
    production_area_id: int | None
    production_area_name: str | None = None

    model_config = {"from_attributes": True}
