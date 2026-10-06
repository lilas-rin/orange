"""数字大屏取数服务：KPI、全国地图、赣州县区、县区/产地联动、价格走势+预测。"""
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    DecisionAdvice,
    MarketData,
    PestDiseaseRecord,
    PredictionResult,
    PriceData,
    ProductionArea,
    ProductionData,
    ProductionEvaluation,
    Region,
    SalesData,
)
from app.data import real_reference
from app.services import analysis_service, forecast_service

SEVERITY_ORDER = {"mild": 1, "moderate": 2, "severe": 3}
RISK_ORDER = {"low": 1, "medium": 2, "high": 3}

# 脐橙产季口径：11月—次年10月，产季年取起始自然年
def _season_expr(col):
    """SQL 表达式：日期所属产季年（11月起算）。"""
    return func.year(col) - case((func.month(col) < 11, 1), else_=0)


def _season_year(d: date) -> int:
    return d.year if d.month >= 11 else d.year - 1


def _latest_year(db: Session) -> int:
    """最新产季年（有产量数据的最新产季）。"""
    latest = db.scalar(select(func.max(ProductionData.date)))
    return _season_year(latest) if latest else _season_year(date.today())


def _risk_from_records(db: Session, county_id: int) -> str:
    """根据近 12 个月病虫害记录严重度估算当前风险（统一由 forecast_service 提供）。"""
    return forecast_service.risk_from_records(db, county_id)


def intelligence(db: Session) -> dict:
    """智能预测与产销排产汇总（价格/需求/产量/库存/病虫害 + 排产建议）。"""
    return forecast_service.intelligence(db)


def map_layers(db: Session) -> dict:
    """全部地图图层一次返回；flow 复用全国销售流向，其余来自预测服务。"""
    layers = forecast_service.all_layers(db)
    data = china_map(db)
    flows = [
        {"name": f["to_name"], "value": f["value"], "label": f"{f['value'] / 10000:.2f} 万吨"}
        for f in data["flows"]
    ]
    values = [f["value"] for f in flows]
    layers["flow"] = {
        "layer": "flow",
        "title": "销售流向",
        "unit": "万吨",
        "scope": "china",
        "min": min(values) if values else 0,
        "max": max(values) if values else 1,
        "items": flows,
    }
    return layers


def map_layer(db: Session, layer: str) -> dict:
    """单个地图图层数据；flow 图层复用全国销售流向。"""
    if layer == "flow":
        return map_layers(db)["flow"]
    return forecast_service.map_layer(db, layer)


def _yoy(cur: float, prev: float) -> float | None:
    """同比：相对变化百分比；基期为 0 时返回 None，避免出现无意义的无穷大。"""
    return round((cur - prev) / prev * 100, 2) if prev else None


def _supply_state(rate: float) -> str:
    """按产销率判定供需状态：tight 偏紧 / balanced 基本平衡 / loose 宽松 / surplus 过剩。"""
    if rate >= 100:
        return "tight"
    if rate >= 92:
        return "balanced"
    if rate >= 85:
        return "loose"
    return "surplus"


def overview(db: Session) -> dict:
    year = _latest_year(db)
    prev_year = year - 1

    total_production = float(
        db.scalar(
            select(func.sum(ProductionData.production)).where(
                _season_expr(ProductionData.date) == year
            )
        )
        or 0
    )
    prev_production = float(
        db.scalar(
            select(func.sum(ProductionData.production)).where(
                _season_expr(ProductionData.date) == prev_year
            )
        )
        or 0
    )
    total_sales = float(
        db.scalar(
            select(func.sum(SalesData.sales_volume)).where(
                _season_expr(SalesData.date) == year
            )
        )
        or 0
    )
    total_amount = float(
        db.scalar(
            select(func.sum(SalesData.sales_amount)).where(
                _season_expr(SalesData.date) == year
            )
        )
        or 0
    )
    avg_price = float(
        db.scalar(
            select(func.avg(PriceData.wholesale_price)).where(
                _season_expr(PriceData.date) == year
            )
        )
        or 0
    )
    province_count = int(
        db.scalar(
            select(func.count(func.distinct(SalesData.region_id))).where(
                _season_expr(SalesData.date) == year
            )
        )
        or 0
    )

    # 上产季同口径数据，用于各指标同比与库存同比。
    total_sales_prev = float(
        db.scalar(
            select(func.sum(SalesData.sales_volume)).where(
                _season_expr(SalesData.date) == prev_year
            )
        )
        or 0
    )
    total_amount_prev = float(
        db.scalar(
            select(func.sum(SalesData.sales_amount)).where(
                _season_expr(SalesData.date) == prev_year
            )
        )
        or 0
    )
    avg_price_prev = float(
        db.scalar(
            select(func.avg(PriceData.wholesale_price)).where(
                _season_expr(PriceData.date) == prev_year
            )
        )
        or 0
    )

    # 库存按「产季产量 − 产季销量」口径推导（未售出量），非独立表字段。
    stock = total_production - total_sales
    prev_stock = prev_production - total_sales_prev
    rate = round(total_sales / total_production * 100, 2) if total_production else 0
    prev_rate = round(total_sales_prev / prev_production * 100, 2) if prev_production else 0

    kpi = {
        "year": year,
        "total_production": round(total_production, 2),
        "total_sales_volume": round(total_sales, 2),
        "total_sales_amount": round(total_amount, 2),
        "avg_wholesale_price": round(avg_price, 2),
        "production_sales_rate": rate,
        "yoy_growth_rate": _yoy(total_production, prev_production),
        "province_count": province_count,
        # —— 以下为新增：同比 / 库存 / 供需状态（均由现有表推导） ——
        "total_sales_volume_yoy": _yoy(total_sales, total_sales_prev),
        "total_sales_amount_yoy": _yoy(total_amount, total_amount_prev),
        "avg_wholesale_price_yoy": _yoy(avg_price, avg_price_prev),
        "production_sales_rate_yoy": _yoy(rate, prev_rate),
        "stock": round(stock, 2),
        "stock_yoy": _yoy(stock, prev_stock),
        "supply_demand_status": _supply_state(rate),
    }

    market = analysis_service.market_analysis(db, year)
    price = price_trend(db, months=24)
    pest = analysis_service.pest_analysis(db, None, None)
    predictions = latest_predictions(db, None, limit=6)
    decisions = latest_decisions(db, limit=5)

    # 平台价格数据无省份区分度，补充外部真实销地批发价供对照（不参与 KPI 计算）。
    top10 = []
    for row in market["top10"]:
        ref = real_reference.province_market_price(row["name"])
        top10.append(
            {
                **row,
                "market_price": ref["price"] if ref else None,
                "market_price_period": ref["period"] if ref else None,
                "market_price_market": ref["market"] if ref else None,
            }
        )

    return {
        "kpi": kpi,
        "top10": top10,
        "price_trend": price,
        "pest_top": pest["by_type"][:5],
        "predictions": predictions,
        "decisions": decisions,
        "reference": {
            "collected_at": real_reference.COLLECTED_AT,
            "national_market_price": real_reference.NATIONAL_WHOLESALE_AVG,
            "province_price_source": "农业农村部信息中心 / 各省农业农村厅 / 一亩田",
        },
    }


def china_map(db: Session) -> dict:
    year = _latest_year(db)
    rows = db.execute(
        select(MarketData, Region)
        .join(Region, MarketData.region_id == Region.id)
        .where(_season_expr(MarketData.date) == year)
        .order_by(MarketData.sales_volume.desc())
    ).all()
    provinces = []
    flows = []
    for md, region in rows:
        vol = float(md.sales_volume or 0)
        provinces.append(
            {
                "name": region.name,
                "adcode": region.adcode,
                "sales_volume": round(vol, 2),
                "sales_amount": round(float(md.sales_amount or 0), 2),
                "market_level": md.market_level,
                "growth_rate": round(float(md.growth_rate or 0), 2),
                "longitude": float(region.longitude) if region.longitude else None,
                "latitude": float(region.latitude) if region.latitude else None,
            }
        )
        if vol > 0:
            flows.append({"from_name": "赣州市", "to_name": region.name, "value": round(vol, 2)})
    return {"year": year, "provinces": provinces, "flows": flows}


def ganzhou_counties(db: Session) -> dict:
    """赣州市各县区概览：产量、销量(产地口径)、价格、风险、评分。"""
    year = _latest_year(db)
    ganzhou = db.scalar(select(Region).where(Region.adcode == "360700"))
    if not ganzhou:
        return {"year": year, "counties": []}
    counties = db.scalars(
        select(Region).where(Region.parent_id == ganzhou.id).order_by(Region.id)
    ).all()

    rate = _global_rate(db, year)

    # 县区五维评价均值（价格/生产技术/运输能力/供应能力/效益），用于大屏 hover 雷达图。
    county_ids = [c.id for c in counties]
    radar_map: dict[int, dict] = {}
    if county_ids:
        eval_rows = db.execute(
            select(
                ProductionArea.region_id,
                func.avg(ProductionEvaluation.price_score),
                func.avg(ProductionEvaluation.technology_score),
                func.avg(ProductionEvaluation.transport_score),
                func.avg(ProductionEvaluation.supply_score),
                func.avg(ProductionEvaluation.benefit_score),
            )
            .join(ProductionEvaluation, ProductionEvaluation.production_area_id == ProductionArea.id)
            .where(ProductionArea.region_id.in_(county_ids))
            .group_by(ProductionArea.region_id)
        ).all()
        for rid, price, tech, trans, supply, benefit in eval_rows:
            radar_map[rid] = {
                "price": round(float(price or 0), 1),
                "technology": round(float(tech or 0), 1),
                "transport": round(float(trans or 0), 1),
                "supply": round(float(supply or 0), 1),
                "benefit": round(float(benefit or 0), 1),
            }

    # 近 12 个月病虫害统计，供大屏「病虫害高风险区域」使用。
    # 与 _risk_from_records 采用同一时间窗，保证风险等级与影响面积口径一致。
    pest_since = date.today() - timedelta(days=365)
    pest_map: dict[int, tuple[int, float, float]] = {}
    if county_ids:
        pest_rows = db.execute(
            select(
                ProductionArea.region_id,
                func.count(PestDiseaseRecord.id),
                func.sum(PestDiseaseRecord.affected_area),
                func.sum(PestDiseaseRecord.production_impact),
            )
            .join(PestDiseaseRecord, PestDiseaseRecord.production_area_id == ProductionArea.id)
            .where(
                ProductionArea.region_id.in_(county_ids),
                PestDiseaseRecord.date >= pest_since,
            )
            .group_by(ProductionArea.region_id)
        ).all()
        for rid, cnt, area, impact in pest_rows:
            pest_map[rid] = (
                int(cnt or 0),
                round(float(area or 0), 2),
                round(float(impact or 0), 2),
            )

    county_list = []
    for county in counties:
        production = float(
            db.scalar(
                select(func.sum(ProductionData.production))
                .join(ProductionArea, ProductionData.production_area_id == ProductionArea.id)
                .where(
                    ProductionArea.region_id == county.id,
                    _season_expr(ProductionData.date) == year,
                )
            )
            or 0
        )
        if production <= 0:
            continue
        avg_price = float(
            db.scalar(
                select(func.avg(PriceData.wholesale_price))
                .join(ProductionArea, PriceData.production_area_id == ProductionArea.id)
                .where(
                    ProductionArea.region_id == county.id,
                    _season_expr(PriceData.date) == year,
                )
            )
            or 0
        )
        area_count = int(
            db.scalar(
                select(func.count(ProductionArea.id)).where(
                    ProductionArea.region_id == county.id
                )
            )
            or 0
        )
        planting = float(
            db.scalar(
                select(func.sum(ProductionArea.planting_area)).where(
                    ProductionArea.region_id == county.id
                )
            )
            or 0
        )
        score = db.scalar(
            select(func.avg(ProductionEvaluation.total_score))
            .join(ProductionArea, ProductionEvaluation.production_area_id == ProductionArea.id)
            .where(ProductionArea.region_id == county.id)
        )
        sales_volume = production * rate
        pest_count, pest_area, pest_impact = pest_map.get(county.id, (0, 0.0, 0.0))
        farm_ref = real_reference.county_farm_price(county.name)
        control_ref = real_reference.county_pest_control(county.name)
        county_list.append(
            {
                "region_id": county.id,
                "name": county.name,
                "adcode": county.adcode,
                "production": round(production, 2),
                "sales_volume": round(sales_volume, 2),
                "sales_amount": round(sales_volume * avg_price, 2),
                "avg_price": round(avg_price, 2),
                "production_sales_rate": round(rate * 100, 2),
                "risk_level": _risk_from_records(db, county.id),
                "planting_area": round(planting, 2),
                "area_count": area_count,
                "score": round(float(score), 1) if score else None,
                "radar": radar_map.get(county.id),
                "pest_count": pest_count,
                "pest_affected_area": pest_area,
                "pest_impact": pest_impact,
                # 外部真实参考数据（不参与 KPI 计算）
                "real_price_per_kg": farm_ref["price_per_kg"] if farm_ref else None,
                "real_price_period": farm_ref["period"] if farm_ref else None,
                "pest_control": control_ref,
            }
        )
    county_list.sort(key=lambda x: x["production"], reverse=True)
    return {
        "year": year,
        "counties": county_list,
        "reference": {
            "collected_at": real_reference.COLLECTED_AT,
            "city_pest_control": real_reference.CITY_PEST_CONTROL,
            "price_source": "中国报告大厅 / 宇博数据库 · 全国橙子报价分析",
            "pest_source": "赣州市及各县区人民政府《2025 年柑橘黄龙病防控工作方案》",
            "planting_reference": real_reference.CITY_PLANTING_REFERENCE,
        },
    }


def _global_rate(db: Session, year: int) -> float:
    production = float(
        db.scalar(
            select(func.sum(ProductionData.production)).where(
                _season_expr(ProductionData.date) == year
            )
        )
        or 0
    )
    sales = float(
        db.scalar(
            select(func.sum(SalesData.sales_volume)).where(
                _season_expr(SalesData.date) == year
            )
        )
        or 0
    )
    return min(1.0, sales / production) if production else 0.9


def county_detail(db: Session, region_id: int, months: int = 24) -> dict:
    """县区联动数据：产销趋势、价格走势(含预测)、病虫害、风险预测、产地列表。"""
    county = db.scalar(select(Region).where(Region.id == region_id))
    if not county:
        return {}
    year = _latest_year(db)

    prod_rows = db.execute(
        select(
            func.date_format(ProductionData.date, "%Y-%m"),
            func.sum(ProductionData.production),
        )
        .join(ProductionArea, ProductionData.production_area_id == ProductionArea.id)
        .where(ProductionArea.region_id == region_id)
        .group_by(func.date_format(ProductionData.date, "%Y-%m"))
        .order_by(func.date_format(ProductionData.date, "%Y-%m"))
    ).all()

    price_rows = db.execute(
        select(
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.wholesale_price),
        )
        .join(ProductionArea, PriceData.production_area_id == ProductionArea.id)
        .where(ProductionArea.region_id == region_id)
        .group_by(func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    ).all()

    pest_rows = db.execute(
        select(
            PestDiseaseRecord.date,
            PestDiseaseRecord.severity,
            PestDiseaseRecord.affected_area,
        )
        .join(ProductionArea, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .where(ProductionArea.region_id == region_id)
        .order_by(PestDiseaseRecord.date.desc())
        .limit(10)
    ).all()

    areas = db.execute(
        select(ProductionArea, ProductionEvaluation)
        .outerjoin(
            ProductionEvaluation, ProductionEvaluation.production_area_id == ProductionArea.id
        )
        .where(ProductionArea.region_id == region_id)
    ).all()

    risk_predictions = db.scalars(
        select(PredictionResult)
        .where(
            PredictionResult.region_id == region_id,
            PredictionResult.prediction_type == "pest_disease",
        )
        .order_by(PredictionResult.target_date.desc())
        .limit(6)
    ).all()

    return {
        "region_id": county.id,
        "name": county.name,
        "adcode": county.adcode,
        "production_trend": [
            {"month": r[0], "value": round(float(r[1] or 0), 2)} for r in prod_rows
        ],
        "price_trend": [
            {"month": r[0], "value": round(float(r[1] or 0), 2)} for r in price_rows
        ],
        "recent_pests": [
            {
                "date": r[0].isoformat(),
                "severity": r[1],
                "affected_area": round(float(r[2] or 0), 2),
            }
            for r in pest_rows
        ],
        "current_risk": _risk_from_records(db, region_id),
        "risk_predictions": [
            {
                "target_date": p.target_date.isoformat(),
                "risk_level": p.risk_level,
                "predicted_value": float(p.predicted_value) if p.predicted_value else None,
            }
            for p in risk_predictions
        ],
        "areas": [
            {
                "id": a.id,
                "name": a.name,
                "longitude": float(a.longitude) if a.longitude else None,
                "latitude": float(a.latitude) if a.latitude else None,
                "planting_area": float(a.planting_area or 0),
                "main_variety": a.main_variety,
                "score": float(e.total_score) if e else None,
            }
            for a, e in areas
        ],
    }


def area_detail(db: Session, area_id: int) -> dict:
    area = db.scalar(select(ProductionArea).where(ProductionArea.id == area_id))
    if not area:
        return {}

    ev = db.scalar(
        select(ProductionEvaluation)
        .where(ProductionEvaluation.production_area_id == area_id)
        .order_by(ProductionEvaluation.evaluation_date.desc())
        .limit(1)
    )
    prod_rows = db.execute(
        select(
            func.date_format(ProductionData.date, "%Y-%m"),
            func.sum(ProductionData.production),
        )
        .where(ProductionData.production_area_id == area_id)
        .group_by(func.date_format(ProductionData.date, "%Y-%m"))
        .order_by(func.date_format(ProductionData.date, "%Y-%m"))
    ).all()
    price_rows = db.execute(
        select(
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.wholesale_price),
        )
        .where(PriceData.production_area_id == area_id)
        .group_by(func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    ).all()
    predictions = db.scalars(
        select(PredictionResult)
        .where(
            PredictionResult.production_area_id == area_id,
            PredictionResult.prediction_type == "price",
        )
        .order_by(PredictionResult.target_date)
        .limit(12)
    ).all()

    return {
        "id": area.id,
        "name": area.name,
        "region_id": area.region_id,
        "region_name": area.region_name,
        "longitude": float(area.longitude) if area.longitude else None,
        "latitude": float(area.latitude) if area.latitude else None,
        "planting_area": float(area.planting_area or 0),
        "main_variety": area.main_variety,
        "description": area.description,
        "scores": {
            "technology": float(area.production_technology_score or 0),
            "transport": float(area.transport_score or 0),
            "supply": float(area.supply_score or 0),
            "benefit": float(area.benefit_score or 0),
        },
        "evaluation": {
            "price": float(ev.price_score),
            "technology": float(ev.technology_score),
            "transport": float(ev.transport_score),
            "supply": float(ev.supply_score),
            "benefit": float(ev.benefit_score),
            "total": float(ev.total_score),
        }
        if ev
        else None,
        "production_trend": [
            {"month": r[0], "value": round(float(r[1] or 0), 2)} for r in prod_rows
        ],
        "price_trend": [
            {"month": r[0], "value": round(float(r[1] or 0), 2)} for r in price_rows
        ],
        "price_predictions": [
            {
                "target_date": p.target_date.isoformat(),
                "value": float(p.predicted_value or 0),
                "lower": float(p.lower_bound or 0),
                "upper": float(p.upper_bound or 0),
            }
            for p in predictions
        ],
    }


def price_trend(db: Session, months: int = 24) -> dict:
    """历史批发价月度均值 + 模型预测（虚线段），历史实线、预测虚线。"""
    rows = db.execute(
        select(
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.wholesale_price),
        )
        .group_by(func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    ).all()
    history = [{"month": r[0], "value": round(float(r[1] or 0), 2)} for r in rows][-months:]

    pred_rows = db.execute(
        select(
            func.date_format(PredictionResult.target_date, "%Y-%m"),
            func.avg(PredictionResult.predicted_value),
            func.avg(PredictionResult.lower_bound),
            func.avg(PredictionResult.upper_bound),
        )
        .where(PredictionResult.prediction_type == "price")
        .group_by(func.date_format(PredictionResult.target_date, "%Y-%m"))
        .order_by(func.date_format(PredictionResult.target_date, "%Y-%m"))
    ).all()
    forecast = [
        {
            "month": r[0],
            "value": round(float(r[1] or 0), 2),
            "lower": round(float(r[2] or 0), 2),
            "upper": round(float(r[3] or 0), 2),
        }
        for r in pred_rows
    ]
    return {"history": history, "forecast": forecast}


def latest_predictions(db: Session, p_type: str | None, limit: int = 20) -> list[dict]:
    stmt = select(PredictionResult).order_by(PredictionResult.id.desc())
    if p_type:
        stmt = stmt.where(PredictionResult.prediction_type == p_type)
    rows = db.scalars(stmt.limit(limit)).all()
    return [
        {
            "id": p.id,
            "prediction_type": p.prediction_type,
            "prediction_date": p.prediction_date.isoformat(),
            "target_date": p.target_date.isoformat(),
            "predicted_value": float(p.predicted_value) if p.predicted_value else None,
            "risk_level": p.risk_level,
            "region_name": p.region_name,
            "production_area_name": p.production_area_name,
            "model_name": p.model_name,
        }
        for p in rows
    ]


def latest_decisions(db: Session, limit: int = 10) -> list[dict]:
    rows = db.scalars(
        select(DecisionAdvice).order_by(DecisionAdvice.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": d.id,
            "advice_type": d.advice_type,
            "risk_level": d.risk_level,
            "title": d.title,
            "content": d.content,
            "region_name": d.region_name,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]
