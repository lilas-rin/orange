"""数据分析服务：产销/价格/市场/病虫害/产地评价 多维统计。"""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    MarketData,
    PestDiseaseRecord,
    PestDiseaseType,
    PriceData,
    ProductionArea,
    ProductionData,
    ProductionEvaluation,
    Region,
    SalesData,
)


def _month_series(rows: list[tuple]) -> list[dict]:
    return [{"month": r[0], "value": float(r[1] or 0)} for r in rows]


def production_sales_analysis(
    db: Session, start: date | None, end: date | None, area_id: int | None
) -> dict:
    """月度产量/销量对比、产销率、产销缺口、分产地对比、分县区年度产量。"""
    p_conds, s_conds = [], []
    if start:
        p_conds.append(ProductionData.date >= start)
        s_conds.append(SalesData.date >= start)
    if end:
        p_conds.append(ProductionData.date <= end)
        s_conds.append(SalesData.date <= end)
    if area_id:
        p_conds.append(ProductionData.production_area_id == area_id)

    prod_month = db.execute(
        select(
            func.date_format(ProductionData.date, "%Y-%m"),
            func.sum(ProductionData.production),
        )
        .where(*p_conds)
        .group_by(func.date_format(ProductionData.date, "%Y-%m"))
        .order_by(func.date_format(ProductionData.date, "%Y-%m"))
    ).all()
    sales_month = db.execute(
        select(
            func.date_format(SalesData.date, "%Y-%m"),
            func.sum(SalesData.sales_volume),
        )
        .where(*s_conds)
        .group_by(func.date_format(SalesData.date, "%Y-%m"))
        .order_by(func.date_format(SalesData.date, "%Y-%m"))
    ).all()

    prod_map = {r[0]: float(r[1] or 0) for r in prod_month}
    sales_map = {r[0]: float(r[1] or 0) for r in sales_month}
    months = sorted(set(prod_map) | set(sales_map))
    monthly = []
    for m in months:
        p, s = prod_map.get(m, 0), sales_map.get(m, 0)
        monthly.append(
            {
                "month": m,
                "production": round(p, 2),
                "sales": round(s, 2),
                "rate": round(s / p * 100, 2) if p else None,
                "gap": round(p - s, 2),
            }
        )

    area_conds = [ProductionData.date >= start] if start else []
    if end:
        area_conds.append(ProductionData.date <= end)
    if area_id:
        area_conds.append(ProductionData.production_area_id == area_id)
    by_area = db.execute(
        select(
            ProductionArea.name,
            func.sum(ProductionData.production),
        )
        .join(ProductionData, ProductionData.production_area_id == ProductionArea.id)
        .where(*area_conds)
        .group_by(ProductionArea.id)
        .order_by(func.sum(ProductionData.production).desc())
    ).all()

    by_county = db.execute(
        select(
            Region.name,
            func.sum(ProductionData.production),
        )
        .join(ProductionArea, ProductionData.production_area_id == ProductionArea.id)
        .join(Region, ProductionArea.region_id == Region.id)
        .where(*area_conds)
        .group_by(Region.id)
        .order_by(func.sum(ProductionData.production).desc())
    ).all()

    total_p = sum(x["production"] for x in monthly)
    total_s = sum(x["sales"] for x in monthly)
    return {
        "monthly": monthly,
        "by_area": [{"name": r[0], "production": round(float(r[1] or 0), 2)} for r in by_area],
        "by_county": [{"name": r[0], "production": round(float(r[1] or 0), 2)} for r in by_county],
        "summary": {
            "total_production": round(total_p, 2),
            "total_sales": round(total_s, 2),
            "rate": round(total_s / total_p * 100, 2) if total_p else None,
        },
    }


def price_analysis(
    db: Session, start: date | None, end: date | None, area_id: int | None
) -> dict:
    """历史趋势、波动、产地对比、极值。"""
    conds = []
    if start:
        conds.append(PriceData.date >= start)
    if end:
        conds.append(PriceData.date <= end)
    if area_id:
        conds.append(PriceData.production_area_id == area_id)

    monthly = db.execute(
        select(
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.average_price),
            func.max(PriceData.highest_price),
            func.min(PriceData.lowest_price),
        )
        .where(*conds)
        .group_by(func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    ).all()

    by_area = db.execute(
        select(
            ProductionArea.name,
            func.avg(PriceData.average_price),
            func.max(PriceData.highest_price),
            func.min(PriceData.lowest_price),
        )
        .join(PriceData, PriceData.production_area_id == ProductionArea.id)
        .where(*conds)
        .group_by(ProductionArea.id)
        .order_by(func.avg(PriceData.average_price).desc())
    ).all()

    values = [float(r[1] or 0) for r in monthly]
    avg = sum(values) / len(values) if values else 0
    variance = sum((v - avg) ** 2 for v in values) / len(values) if values else 0
    std = variance**0.5

    return {
        "monthly": [
            {
                "month": r[0],
                "avg": round(float(r[1] or 0), 2),
                "max": round(float(r[2] or 0), 2),
                "min": round(float(r[3] or 0), 2),
            }
            for r in monthly
        ],
        "by_area": [
            {
                "name": r[0],
                "avg": round(float(r[1] or 0), 2),
                "max": round(float(r[2] or 0), 2),
                "min": round(float(r[3] or 0), 2),
            }
            for r in by_area
        ],
        "summary": {
            "avg_price": round(avg, 2),
            "highest": round(max(values), 2) if values else None,
            "lowest": round(min(values), 2) if values else None,
            "volatility": round(std / avg * 100, 2) if avg else None,  # 变异系数%
        },
    }


def market_analysis(db: Session, year: int | None) -> dict:
    """TOP10、市场占比、等级分布、同比增长。"""
    latest = db.scalar(
        select(func.max(MarketData.date))
    )
    y = year or (latest.year if latest else date.today().year)
    rows = db.execute(
        select(MarketData, Region.name)
        .join(Region, MarketData.region_id == Region.id)
        .where(func.year(MarketData.date) == y)
        .order_by(MarketData.sales_volume.desc())
    ).all()
    prev_rows = db.execute(
        select(MarketData.region_id, func.sum(MarketData.sales_volume))
        .where(func.year(MarketData.date) == y - 1)
        .group_by(MarketData.region_id)
    ).all()
    prev_map = {r[0]: float(r[1] or 0) for r in prev_rows}

    provinces = []
    for md, name in rows:
        vol = float(md.sales_volume or 0)
        prev = prev_map.get(md.region_id)
        provinces.append(
            {
                "name": name,
                "sales_volume": round(vol, 2),
                "sales_amount": round(float(md.sales_amount or 0), 2),
                "market_share": round(float(md.market_share or 0), 2),
                "market_level": md.market_level,
                "growth_rate": round(float(md.growth_rate or 0), 2)
                if md.growth_rate is not None
                else (round((vol - prev) / prev * 100, 2) if prev else None),
            }
        )
    level_count = {"core": 0, "main": 0, "potential": 0}
    for md, _ in rows:
        level_count[md.market_level] = level_count.get(md.market_level, 0) + 1

    return {
        "year": y,
        "provinces": provinces,
        "top10": provinces[:10],
        "level_distribution": level_count,
    }


def pest_analysis(db: Session, start: date | None, end: date | None) -> dict:
    """发生次数、影响面积、产量影响、区域风险、趋势。"""
    conds = []
    if start:
        conds.append(PestDiseaseRecord.date >= start)
    if end:
        conds.append(PestDiseaseRecord.date <= end)

    by_type = db.execute(
        select(
            PestDiseaseType.name,
            PestDiseaseType.type,
            func.count(PestDiseaseRecord.id),
            func.sum(PestDiseaseRecord.affected_area),
            func.sum(PestDiseaseRecord.production_impact),
        )
        .join(PestDiseaseRecord, PestDiseaseRecord.pest_disease_type_id == PestDiseaseType.id)
        .where(*conds)
        .group_by(PestDiseaseType.id)
        .order_by(func.count(PestDiseaseRecord.id).desc())
    ).all()

    by_county = db.execute(
        select(
            Region.name,
            func.count(PestDiseaseRecord.id),
            func.sum(PestDiseaseRecord.affected_area),
            func.sum(PestDiseaseRecord.production_impact),
        )
        .join(ProductionArea, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .join(Region, ProductionArea.region_id == Region.id)
        .where(*conds)
        .group_by(Region.id)
    ).all()

    by_month = db.execute(
        select(
            func.date_format(PestDiseaseRecord.date, "%Y-%m"),
            func.count(PestDiseaseRecord.id),
            func.sum(PestDiseaseRecord.affected_area),
        )
        .where(*conds)
        .group_by(func.date_format(PestDiseaseRecord.date, "%Y-%m"))
        .order_by(func.date_format(PestDiseaseRecord.date, "%Y-%m"))
    ).all()

    severity_map = {"mild": 1, "moderate": 2, "severe": 3}
    counties = []
    for name, cnt, area, impact in by_county:
        counties.append(
            {
                "name": name,
                "count": int(cnt or 0),
                "affected_area": round(float(area or 0), 2),
                "production_impact": round(float(impact or 0), 2),
            }
        )

    return {
        "by_type": [
            {
                "name": r[0],
                "kind": r[1],
                "count": int(r[2] or 0),
                "affected_area": round(float(r[3] or 0), 2),
                "production_impact": round(float(r[4] or 0), 2),
            }
            for r in by_type
        ],
        "by_county": counties,
        "by_month": [
            {"month": r[0], "count": int(r[1] or 0), "affected_area": round(float(r[2] or 0), 2)}
            for r in by_month
        ],
    }


def evaluation_analysis(db: Session) -> dict:
    """产地五维评价与综合排名（取每个产地最新一期评价）。"""
    areas = db.scalars(select(ProductionArea).order_by(ProductionArea.id)).all()
    latest_dates = db.execute(
        select(
            ProductionEvaluation.production_area_id,
            func.max(ProductionEvaluation.evaluation_date),
        ).group_by(ProductionEvaluation.production_area_id)
    ).all()
    latest_map = dict(latest_dates)

    result = []
    for area in areas:
        d = latest_map.get(area.id)
        if not d:
            continue
        ev = db.scalar(
            select(ProductionEvaluation).where(
                ProductionEvaluation.production_area_id == area.id,
                ProductionEvaluation.evaluation_date == d,
            )
        )
        result.append(
            {
                "area_id": area.id,
                "name": area.name,
                "price": float(ev.price_score),
                "technology": float(ev.technology_score),
                "transport": float(ev.transport_score),
                "supply": float(ev.supply_score),
                "benefit": float(ev.benefit_score),
                "total": float(ev.total_score),
            }
        )
    result.sort(key=lambda x: x["total"], reverse=True)
    for i, item in enumerate(result):
        item["rank"] = i + 1
    return {"ranking": result}
