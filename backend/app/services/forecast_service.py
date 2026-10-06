"""智能预测与产销排产服务。

五项预测 → 汇总为智能产销排产建议，构成「现状监测 → 趋势预测 → 风险识别 →
智能排产 → 决策辅助」闭环。所有输出均由现有业务表推导，不引入合成数据。

口径说明
- 产季年：11 月—次年 10 月，取起始自然年（与 KPI 一致）。
- 市场需求：随机森林（产季序 × 产季内月序 + 滞后/同月特征）预测「下一产季首月
  (11 月)」销量，与上一产季同月实际对比得到同比 —— 直接回答「哪个市场值得增加供应」。
- 产量：产季总量序列的 Holt 线性趋势外推。
- 库存/供应保障：期初库存 + 新产季首月产量 对比 首月需求，得到保障系数与风险等级。
- 价格：复用已落库的 prediction_result(price)，另行推导 7 天/30 天与异常概率、置信区间。
- 病虫害：复用已落库的 prediction_result(pest_disease)，叠加近 30 天实际发生趋势。
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.data import real_reference
from app.ml.season_model import SeasonMonthForecaster, holt_linear, season_index, season_month
from app.models import (
    PestDiseaseRecord,
    PredictionResult,
    PriceData,
    ProductionArea,
    ProductionData,
    Region,
    SalesData,
)

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"mild": 1, "moderate": 2, "severe": 3}
RISK_ORDER = {"low": 1, "medium": 2, "high": 3}

PLAN_BUFFER = 1.05  # 排产安全余量（采后损耗、分选淘汰）
SAFETY_DAYS = 30  # 库存安全缓冲天数


# ---------------- 计算结果缓存 ----------------
# 整条链路唯一的性能热点是 market_demand：它为每个省单独拟合一个随机森林
# (n_estimators=240)，单次约 6s，其余步骤均在 0.05s 以内。
# 而大屏首屏会**并发**请求 /intelligence 与 /layers，两者都依赖它 —— 不做共享
# 就会把同一份结果算两遍；进程刚启动时更会叠加模型冷启动开销，足以撞破前端
# 30s 超时，表现就是「大屏没有任何数据显示」。
#
# 这里用「TTL 缓存 + 单飞锁」：同一时刻只允许一个线程真正计算，其余等待复用。
_CACHE_LOCK = threading.RLock()
_CACHE: dict[str, tuple[float, dict]] = {}

DEMAND_TTL = 180.0  # 市场需求：RF 拟合最贵，缓存久一点
INTEL_TTL = 60.0  # 预测汇总：与大屏 60s 轮询对齐，保证每轮拿到新值


def _cached(key: str, ttl: float, producer):
    """带 TTL 的进程内缓存；并发未命中时由锁保证同一份值只计算一次。"""
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        value = producer()
        _CACHE[key] = (time.monotonic(), value)
        return value


def invalidate_cache() -> None:
    """清空预测缓存；后台导入/修改产销数据后可调用，使大屏立刻反映新数据。"""
    with _CACHE_LOCK:
        _CACHE.clear()


def warmup() -> None:
    """预热缓存，让首位访问者不必承担模型冷启动开销。失败不影响服务启动。"""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        started = time.perf_counter()
        intelligence(db, force=True)
        logger.info("预测缓存预热完成，耗时 %.2fs", time.perf_counter() - started)
    except Exception:  # noqa: BLE001 - 预热失败不应阻塞服务
        logger.exception("预测缓存预热失败（不影响服务，首次请求会实时计算）")
    finally:
        db.close()


# ---------------- 通用口径 ----------------


def _season_expr(col):
    """SQL 表达式：日期所属产季年（11 月起算）。"""
    return func.year(col) - case((func.month(col) < 11, 1), else_=0)


def _season_year(d: date) -> int:
    return d.year if d.month >= 11 else d.year - 1


def latest_season(db: Session) -> int:
    latest = db.scalar(select(func.max(ProductionData.date)))
    return _season_year(latest) if latest else _season_year(date.today())


def risk_from_records(db: Session, county_id: int) -> str:
    """近 12 个月病虫害记录严重度加权，估算当前风险等级。"""
    since = date.today() - timedelta(days=365)
    rows = db.execute(
        select(PestDiseaseRecord.severity, func.count(PestDiseaseRecord.id))
        .join(ProductionArea, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .where(ProductionArea.region_id == county_id, PestDiseaseRecord.date >= since)
        .group_by(PestDiseaseRecord.severity)
    ).all()
    if not rows:
        return "low"
    weighted = sum(SEVERITY_ORDER.get(r[0], 1) * r[1] for r in rows)
    cnt = sum(r[1] for r in rows)
    score = weighted / max(cnt, 1)
    if score >= 2.2:
        return "high"
    if score >= 1.5:
        return "medium"
    return "low"


def season_totals(db: Session) -> dict[int, float]:
    """{产季年: 全市产量(吨)}。"""
    rows = db.execute(
        select(_season_expr(ProductionData.date), func.sum(ProductionData.production))
        .group_by(_season_expr(ProductionData.date))
        .order_by(_season_expr(ProductionData.date))
    ).all()
    return {int(r[0]): float(r[1] or 0) for r in rows}


def season_sales_totals(db: Session) -> dict[int, float]:
    rows = db.execute(
        select(_season_expr(SalesData.date), func.sum(SalesData.sales_volume))
        .group_by(_season_expr(SalesData.date))
        .order_by(_season_expr(SalesData.date))
    ).all()
    return {int(r[0]): float(r[1] or 0) for r in rows}


def _first_month_harvest_share(db: Session, year: int) -> float:
    """新产季首月（11 月）采收占全产季比例，由历史实际数据算出。"""
    rows = db.execute(
        select(func.month(ProductionData.date), func.sum(ProductionData.production))
        .where(_season_expr(ProductionData.date) == year)
        .group_by(func.month(ProductionData.date))
    ).all()
    total = sum(float(r[1] or 0) for r in rows)
    if not total:
        return 0.40
    first = sum(float(r[1] or 0) for r in rows if int(r[0]) == 11)
    return round(first / total, 4)


# ---------------- 市场需求预测 ----------------


def _province_monthly_series(db: Session) -> dict[int, list[tuple[int, int, float]]]:
    """{省 region_id: [(产季序, 产季内月序, 销量吨)]}。"""
    rows = db.execute(
        select(SalesData.region_id, SalesData.date, func.sum(SalesData.sales_volume))
        .group_by(SalesData.region_id, SalesData.date)
        .order_by(SalesData.date)
    ).all()
    acc: dict[int, dict[tuple[int, int], float]] = {}
    for rid, d, vol in rows:
        key = (season_index(_season_year(d)), season_month(d.month))
        acc.setdefault(rid, {})
        acc[rid][key] = acc[rid].get(key, 0.0) + float(vol or 0)
    return {rid: sorted((s, m, v) for (s, m), v in items.items()) for rid, items in acc.items()}


def market_demand(db: Session, top_n: int = 8) -> dict:
    """各省市场需求预测（带缓存，避开重复拟合随机森林）。"""
    return _cached(f"demand:{top_n}", DEMAND_TTL, lambda: _compute_market_demand(db, top_n))


def _compute_market_demand(db: Session, top_n: int = 8) -> dict:
    """各省市场需求预测：当前产季累计 → 新产季首月预测 → 同比。"""
    year = latest_season(db)
    cur_idx = season_index(year)
    next_idx = cur_idx + 1
    series = _province_monthly_series(db)
    regions = {r.id: r for r in db.scalars(select(Region)).all()}

    rows: list[dict] = []
    for rid, points in series.items():
        region = regions.get(rid)
        if not region or region.type != "province":
            continue
        try:
            model = SeasonMonthForecaster().fit(points)
            value, lower, upper = model.predict_next_season_month(next_idx, 1)
        except ValueError:
            continue
        prev_actual = next((v for s, m, v in points if s == cur_idx and m == 1), 0.0)
        current_cum = sum(v for s, m, v in points if s == cur_idx)
        growth = round((value - prev_actual) / prev_actual * 100, 1) if prev_actual else None
        if growth is None:
            level, action = "unknown", "数据不足，暂不调整"
        elif growth >= 8:
            level, action = "high", "建议增加供应，抢占份额"
        elif growth >= 2:
            level, action = "steady", "维持现有供应节奏"
        elif growth >= 0:
            level, action = "flat", "小幅上调，观察走货"
        else:
            level, action = "down", "适度减少投放，转向高增市场"
        rows.append(
            {
                "name": region.name,
                "adcode": region.adcode,
                "current": round(current_cum, 2),
                "forecast": round(value, 2),
                "lower": lower,
                "upper": upper,
                "prev_actual": round(prev_actual, 2),
                "growth": growth,
                "level": level,
                "action": action,
            }
        )

    rows.sort(key=lambda r: r["forecast"], reverse=True)
    total_forecast = round(sum(r["forecast"] for r in rows), 2)
    return {
        "season": year,
        "target_season": year + 1,
        "target_month": f"{year + 1}-11",
        "total_forecast": total_forecast,
        "total_prev_actual": round(sum(r["prev_actual"] for r in rows), 2),
        "markets": rows[:top_n],
        "all": rows,
    }


# ---------------- 产量预测 ----------------


def production_forecast(db: Session) -> dict | None:
    totals = season_totals(db)
    if len(totals) < 3:
        return None
    years = sorted(totals)
    values = [totals[y] for y in years]
    pred, std = holt_linear(values, steps=1)
    last = values[-1]
    margin = max(1.96 * std, last * 0.03)
    return {
        "year": years[-1] + 1,
        "value": round(pred, 2),
        "lower": round(max(0.0, pred - margin), 2),
        "upper": round(pred + margin, 2),
        "yoy": round((pred - last) / last * 100, 2) if last else None,
        "history": [{"year": y, "value": round(totals[y], 2)} for y in years],
    }


# ---------------- 价格展望 ----------------


def price_outlook(db: Session) -> dict | None:
    hist_rows = db.execute(
        select(
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.wholesale_price),
        )
        .group_by(func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    ).all()
    history = [(r[0], float(r[1] or 0)) for r in hist_rows]
    if not history:
        return None
    current = history[-1][1]

    batch = db.scalar(
        select(func.max(PredictionResult.prediction_date)).where(
            PredictionResult.prediction_type == "price"
        )
    )
    forecast: list[dict] = []
    if batch:
        rows = db.execute(
            select(
                func.date_format(PredictionResult.target_date, "%Y-%m"),
                func.avg(PredictionResult.predicted_value),
                func.avg(PredictionResult.lower_bound),
                func.avg(PredictionResult.upper_bound),
            )
            .where(
                PredictionResult.prediction_type == "price",
                PredictionResult.prediction_date == batch,
            )
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
            for r in rows
        ]

    current_month = history[-1][0]
    ahead = next((f for f in forecast if f["month"] > current_month), None)
    d30 = ahead["value"] if ahead else current
    # 月度模型插值出 7 天预测（模型粒度为月，7 天按比例内插）
    d7 = round(current + (d30 - current) * 7 / 30, 2)
    chg7 = round((d7 - current) / current * 100, 2) if current else None
    chg30 = round((d30 - current) / current * 100, 2) if current else None

    ci_low = ahead["lower"] if ahead else round(current * 0.95, 2)
    ci_high = ahead["upper"] if ahead else round(current * 1.05, 2)
    width = (ci_high - ci_low) / d30 if d30 else 0
    confidence = int(max(0, min(99, round((1 - width) * 100))))

    # 异常概率：近 12 个月最大月度振幅 + 预测区间相对宽度
    recent = history[-13:]
    swing = 0.0
    for i in range(1, len(recent)):
        a, b = recent[i - 1][1], recent[i][1]
        if a:
            swing = max(swing, abs((b - a) / a * 100))
    score = max(swing / 15, width / 0.25)
    if score >= 1.0:
        anomaly_risk, anomaly_label = "high", "高"
    elif score >= 0.55:
        anomaly_risk, anomaly_label = "medium", "中"
    else:
        anomaly_risk, anomaly_label = "low", "低"

    national = real_reference.NATIONAL_WHOLESALE_AVG
    return {
        "current": round(current, 2),
        "current_month": current_month,
        "d7": d7,
        "d30": d30,
        "target_month": ahead["month"] if ahead else current_month,
        "chg7": chg7,
        "chg30": chg30,
        "ci_low": round(ci_low, 2),
        "ci_high": round(ci_high, 2),
        "confidence": confidence,
        "anomaly_risk": anomaly_risk,
        "anomaly_label": anomaly_label,
        "max_swing": round(swing, 2),
        "gap_to_national": round(national["value"] - current, 2),
        "national_price": national["value"],
        "national_period": national["period"],
    }


# ---------------- 库存与供应保障 ----------------


def stock_outlook(db: Session, year: int, prod_fc: dict | None, demand_total: float) -> dict:
    """期初库存 + 新产季首月产量 对比 首月需求。"""
    totals = season_totals(db)
    sales = season_sales_totals(db)
    production_cur = totals.get(year, 0.0)
    sales_cur = sales.get(year, 0.0)
    opening_stock = max(0.0, production_cur - sales_cur)
    prev_stock = max(0.0, totals.get(year - 1, 0.0) - sales.get(year - 1, 0.0))

    share = _first_month_harvest_share(db, year)
    next_production = prod_fc["value"] if prod_fc else production_cur
    first_month_production = next_production * share
    supply = opening_stock + first_month_production
    demand = demand_total
    coverage = round(supply / demand, 2) if demand else None
    gap = round(supply - demand, 2)

    if coverage is None:
        risk, label, advice = "medium", "待评估", "先补齐产销数据再评估供应保障能力"
    elif coverage >= 1.3:
        risk, label = "low", "供应宽松"
        advice = "供应充足，可适度延后出货，把握价格上行窗口"
    elif coverage >= 1.0:
        risk, label = "medium", "供需平衡"
        advice = "按现有节奏组织采收与调运，跟踪走货速度"
    else:
        risk, label = "high", "供应偏紧"
        advice = "优先保障高需求市场，加快采收与分选入库"

    daily_demand = demand / 30 if demand else 0
    safety_stock = daily_demand * SAFETY_DAYS
    return {
        "opening_stock": round(opening_stock, 2),
        "stock_yoy": round((opening_stock - prev_stock) / prev_stock * 100, 2) if prev_stock else None,
        "first_month_share": share,
        "first_month_production": round(first_month_production, 2),
        "supply": round(supply, 2),
        "demand": round(demand, 2),
        "coverage": coverage,
        "gap": gap,
        "risk": risk,
        "label": label,
        "advice": advice,
        "daily_demand": round(daily_demand, 3),
        "safety_stock": round(safety_stock, 2),
        "days_left": round(opening_stock / daily_demand, 1) if daily_demand else None,
    }


# ---------------- 病虫害未来风险 ----------------


def pest_outlook(db: Session, top_n: int = 6) -> dict:
    ganzhou = db.scalar(select(Region).where(Region.adcode == "360700"))
    counties = (
        db.scalars(select(Region).where(Region.parent_id == ganzhou.id)).all() if ganzhou else []
    )
    today = date.today()

    fc_map: dict[int, tuple[date, str, float]] = {}
    batch = db.scalar(
        select(func.max(PredictionResult.prediction_date)).where(
            PredictionResult.prediction_type == "pest_disease"
        )
    )
    if batch:
        rows = db.execute(
            select(
                PredictionResult.region_id,
                PredictionResult.target_date,
                PredictionResult.risk_level,
                PredictionResult.predicted_value,
            )
            .where(
                PredictionResult.prediction_type == "pest_disease",
                PredictionResult.prediction_date == batch,
            )
            .order_by(PredictionResult.target_date)
        ).all()
        for rid, target, level, proba in rows:
            if target < today or rid in fc_map:
                continue
            fc_map[rid] = (target, level or "low", float(proba or 0))

    since_recent = today - timedelta(days=365)
    recent_rows = db.execute(
        select(ProductionArea.region_id, func.count(PestDiseaseRecord.id))
        .join(PestDiseaseRecord, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .where(PestDiseaseRecord.date >= since_recent)
        .group_by(ProductionArea.region_id)
    ).all()
    recent = {int(r[0]): int(r[1] or 0) for r in recent_rows}

    items = []
    for c in counties:
        cur = risk_from_records(db, c.id)
        fc = fc_map.get(c.id)
        future = fc[1] if fc else cur
        delta = RISK_ORDER.get(future, 1) - RISK_ORDER.get(cur, 1)
        trend = "up" if delta > 0 else "down" if delta < 0 else "flat"
        items.append(
            {
                "region_id": c.id,
                "name": c.name,
                "current": cur,
                "forecast": future,
                "prob": round(fc[2], 3) if fc else None,
                "target_date": fc[0].isoformat() if fc else None,
                "trend": trend,
                "recent_count": recent.get(c.id, 0),
                "recent_window": "近 12 个月",
            }
        )
    items.sort(
        key=lambda x: (RISK_ORDER.get(x["forecast"], 0), x["recent_count"]),
        reverse=True,
    )
    return {
        "window": "未来 7 天",
        "target_month": items[0]["target_date"] if items else None,
        "high_count": sum(1 for i in items if i["forecast"] == "high"),
        "items": items[:top_n],
        "all": items,
    }


# ---------------- 智能产销排产 ----------------


def production_plan(
    db: Session,
    year: int,
    demand: dict,
    stock: dict,
    pest: dict,
) -> dict:
    """综合需求 / 供应 / 风险，输出排产量、区域排产与市场供应建议。"""
    total_next_month = demand["total_forecast"]
    total_prev_month = demand["total_prev_actual"]
    plan_7d = total_next_month / 30 * 7 * PLAN_BUFFER
    baseline_7d = total_prev_month / 30 * 7
    change = round((plan_7d - baseline_7d) / baseline_7d * 100, 1) if baseline_7d else None

    # —— 区域排产：按县区产量份额分摊，并叠加病虫害风险与产量趋势修正 ——
    county_prod = dict(
        db.execute(
            select(ProductionArea.region_id, func.sum(ProductionData.production))
            .join(ProductionData, ProductionData.production_area_id == ProductionArea.id)
            .where(_season_expr(ProductionData.date) == year)
            .group_by(ProductionArea.region_id)
        ).all()
    )
    county_prod = {int(k): float(v or 0) for k, v in county_prod.items()}
    prev_prod = dict(
        db.execute(
            select(ProductionArea.region_id, func.sum(ProductionData.production))
            .join(ProductionData, ProductionData.production_area_id == ProductionArea.id)
            .where(_season_expr(ProductionData.date) == year - 1)
            .group_by(ProductionArea.region_id)
        ).all()
    )
    prev_prod = {int(k): float(v or 0) for k, v in prev_prod.items()}

    names = {r.id: r.name for r in db.scalars(select(Region)).all()}
    risk_map = {i["region_id"]: i["forecast"] for i in pest["all"]}
    total_prod = sum(county_prod.values()) or 1.0

    weighted: list[tuple[int, float, float]] = []
    for rid, prod in county_prod.items():
        if prod <= 0:
            continue
        base_share = prod / total_prod
        risk = risk_map.get(rid, "low")
        risk_factor = {"high": 0.85, "medium": 0.95, "low": 1.0}[risk]
        # 产量趋势修正：同比增长的产区具备扩产条件
        pv = prev_prod.get(rid, 0.0)
        trend_factor = 1.0
        if pv:
            growth = (prod - pv) / pv
            trend_factor = max(0.9, min(1.12, 1 + growth * 0.6))
        weighted.append((rid, base_share, base_share * risk_factor * trend_factor))

    norm = sum(w for _, _, w in weighted) or 1.0
    regions = []
    for rid, base_share, w in weighted:
        share = w / norm
        regions.append(
            {
                "region_id": rid,
                "name": names.get(rid, str(rid)),
                "plan": round(plan_7d * share, 2),
                "base_plan": round(plan_7d * base_share, 2),
                "delta": round((share - base_share) / base_share * 100, 1) if base_share else 0.0,
                "risk": risk_map.get(rid, "low"),
            }
        )
    regions.sort(key=lambda r: r["plan"], reverse=True)

    # —— 市场供应建议：新产季首月预测 vs 上一产季同月实际 ——
    markets = []
    for m in demand["all"]:
        delta = m["forecast"] - m["prev_actual"]
        if abs(delta) < 500:
            action, level = "维持供应", "flat"
        elif delta > 0:
            action, level = f"建议增加供应 {delta / 10000:.2f} 万吨", "high"
        else:
            action, level = f"建议减少供应 {abs(delta) / 10000:.2f} 万吨", "down"
        markets.append(
            {
                "name": m["name"],
                "delta": round(delta, 2),
                "delta_wan": round(delta / 10000, 2),
                "growth": m["growth"],
                "forecast": m["forecast"],
                "action": action,
                "level": level,
            }
        )
    markets.sort(key=lambda m: m["delta"], reverse=True)
    # 供应建议：优先给「增量最大」的 2 个市场 + 「减量最大」的 1 个市场；
    # 若所有市场都在增长，则补足第 3 个增量市场，保证面板三行信息量。
    supply_advice = markets[:2]
    decreases = [m for m in reversed(markets) if m["delta"] < 0]
    if decreases:
        supply_advice = supply_advice + decreases[:1]
    elif len(markets) > 2:
        supply_advice = supply_advice + [markets[2]]

    return {
        "plan_7d": round(plan_7d, 2),
        "baseline_7d": round(baseline_7d, 2),
        "change": change,
        "coverage": stock["coverage"],
        "supply_state": stock["label"],
        "regions": regions,
        "markets": supply_advice[:3],
        "basis": [
            f"首月需求预测 {total_next_month / 10000:.1f} 万吨",
            f"供应保障系数 {stock['coverage'] if stock['coverage'] is not None else '-'}",
            f"高风险产区 {pest['high_count']} 个",
        ],
    }


# ---------------- 汇总 ----------------


def intelligence(db: Session, force: bool = False) -> dict:
    """大屏智能预测与排产总入口；带 TTL 缓存 + 单飞，避免并发重复计算。"""
    if force:
        invalidate_cache()
    return _cached("intelligence", INTEL_TTL, lambda: _compute_intelligence(db))


def _compute_intelligence(db: Session) -> dict:
    """大屏智能预测与排产总入口。"""
    year = latest_season(db)
    demand = market_demand(db)
    prod_fc = production_forecast(db)
    price = price_outlook(db)
    stock = stock_outlook(db, year, prod_fc, demand["total_forecast"])
    pest = pest_outlook(db)
    plan = production_plan(db, year, demand, stock, pest)

    return {
        "season": year,
        "target_season": year + 1,
        "price": price,
        "demand": demand,
        "production": prod_fc,
        "stock": stock,
        "pest": pest,
        "plan": plan,
    }


# ---------------- 地图图层 ----------------


LAYER_META = {
    "flow": {"title": "销售流向", "unit": "万吨", "scope": "china"},
    "demand": {"title": "市场需求", "unit": "同比%", "scope": "china"},
    "price": {"title": "销地价格", "unit": "元/kg", "scope": "china"},
    "supply": {"title": "供应压力", "unit": "万吨", "scope": "ganzhou"},
    "risk": {"title": "病虫害风险", "unit": "风险等级", "scope": "ganzhou"},
    "plan": {"title": "智能排产", "unit": "万吨", "scope": "ganzhou"},
}

RISK_VALUE = {"low": 1, "medium": 2, "high": 3}
RISK_TEXT = {1: "低风险", 2: "中风险", 3: "高风险"}


def map_layer(db: Session, layer: str, intel: dict | None = None) -> dict:
    """地图多图层数据。china 指全国省份维度，ganzhou 指赣州县区维度。"""
    meta = LAYER_META.get(layer)
    if not meta:
        return {"layer": layer, "items": [], "error": "未知图层"}

    intel = intel or intelligence(db)
    items: list[dict] = []

    if layer == "demand":
        for m in intel["demand"]["all"]:
            items.append(
                {
                    "name": m["name"],
                    "value": m["growth"],
                    "label": f"需求同比 {m['growth']}%" if m["growth"] is not None else "数据不足",
                }
            )
    elif layer == "price":
        for p in intel["demand"]["all"]:
            ref = real_reference.province_market_price(p["name"])
            if not ref:
                continue
            items.append(
                {"name": p["name"], "value": ref["price"], "label": f"{ref['price']} 元/kg"}
            )
    elif layer == "supply":
        totals = season_totals(db)
        ganzhou = db.scalar(select(Region).where(Region.adcode == "360700"))
        counties = db.scalars(select(Region).where(Region.parent_id == ganzhou.id)).all() if ganzhou else []
        county_prod = dict(
            db.execute(
                select(ProductionArea.region_id, func.sum(ProductionData.production))
                .join(ProductionData, ProductionData.production_area_id == ProductionArea.id)
                .where(_season_expr(ProductionData.date) == intel["season"])
                .group_by(ProductionArea.region_id)
            ).all()
        )
        _ = totals
        for c in counties:
            v = float(county_prod.get(c.id, 0) or 0)
            if v <= 0:
                continue
            items.append({"name": c.name, "value": round(v / 10000, 2), "label": f"{v / 10000:.2f} 万吨"})
    elif layer == "risk":
        for p in intel["pest"]["all"]:
            lv = RISK_ORDER.get(p["forecast"], 1)
            items.append(
                {
                    "name": p["name"],
                    "value": lv,
                    "level": p["forecast"],
                    "label": RISK_TEXT[lv],
                }
            )
    elif layer == "plan":
        for r in intel["plan"]["regions"]:
            items.append(
                {
                    "name": r["name"],
                    "value": round(r["plan"] / 10000, 2),
                    "label": f"{r['plan'] / 10000:.2f} 万吨",
                    "delta": r["delta"],
                }
            )

    values = [i["value"] for i in items if isinstance(i.get("value"), (int, float))]
    return {
        "layer": layer,
        "title": meta["title"],
        "unit": meta["unit"],
        "scope": meta["scope"],
        "min": min(values) if values else 0,
        "max": max(values) if values else 1,
        "items": items,
    }


LAYER_KEYS = ["demand", "price", "supply", "risk", "plan"]


def all_layers(db: Session) -> dict:
    """一次算完所有图层（共用同一份预测结果，避免重复建模）。"""
    intel = intelligence(db)
    return {key: map_layer(db, key, intel) for key in LAYER_KEYS}
