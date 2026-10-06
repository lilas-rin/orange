"""机器学习服务：训练价格/病虫害模型，执行预测并落库 prediction_result。"""
import logging
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ModelInfo,
    PestDiseaseRecord,
    PestDiseaseType,
    PredictionResult,
    PriceData,
    ProductionArea,
    Region,
)
from app.ml.pest_model import PestRiskClassifier, label_from_severity
from app.ml.price_model import PriceForecaster

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1"


def _store_path(filename: str) -> Path:
    p = Path(settings.ML_STORE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p / filename


# ---------------- 价格 ----------------

def _load_price_series(db: Session, area_id: int | None = None) -> dict[int, pd.Series]:
    """{production_area_id: 月度批发价序列(Period 索引)}"""
    stmt = (
        select(
            PriceData.production_area_id,
            func.date_format(PriceData.date, "%Y-%m"),
            func.avg(PriceData.wholesale_price),
        )
        .group_by(PriceData.production_area_id, func.date_format(PriceData.date, "%Y-%m"))
        .order_by(func.date_format(PriceData.date, "%Y-%m"))
    )
    if area_id:
        stmt = stmt.where(PriceData.production_area_id == area_id)
    rows = db.execute(stmt).all()
    series_map: dict[int, list] = {}
    for area_id_, ym, price in rows:
        series_map.setdefault(area_id_, []).append((ym, float(price or 0)))
    out = {}
    for aid, points in series_map.items():
        s = pd.Series(
            [v for _, v in points],
            index=pd.PeriodIndex([m for m, _ in points], freq="M"),
            dtype=float,
        )
        if len(s) >= 10:
            out[aid] = s
    return out


def train_price_model(db: Session) -> dict:
    series_map = _load_price_series(db)
    if not series_map:
        raise ValueError("价格数据不足，无法训练价格模型")
    forecaster = PriceForecaster()
    mapes = []
    for series in series_map.values():
        f = PriceForecaster().fit(series)
        if f.mape:
            mapes.append(f.mape)
    # 用全量（所有产地拼接）再训练一个最终模型，兼顾各产地特征
    all_series = pd.concat(
        [s for s in series_map.values()], axis=1
    ).mean(axis=1)  # 全市均价
    forecaster.fit(all_series)
    # 每个产地单独模型保存为 dict
    models = {}
    for aid, series in series_map.items():
        models[aid] = PriceForecaster().fit(series)
    models["__avg__"] = forecaster
    path = _store_path("price_model_v1.joblib")
    joblib.dump(models, path)

    info = ModelInfo(
        model_name="orange_price_rf",
        model_type="price",
        version=MODEL_VERSION,
        target="批发价格(元/kg)",
        algorithm="RandomForestRegressor",
        training_dataset=f"price_data({len(series_map)}个产地)",
        evaluation_metric="MAPE",
        accuracy=round(float(np.mean(mapes)), 4) if mapes else None,
        model_path=str(path),
        status="active",
    )
    _retire_old(db, "price")
    db.add(info)
    db.flush()
    logger.info("价格模型训练完成 mape=%s", info.accuracy)
    return {"model": "orange_price_rf", "version": MODEL_VERSION, "mape": info.accuracy}


def predict_price(db: Session, months: int = 6) -> dict:
    models = joblib.load(_store_path("price_model_v1.joblib"))
    series_map = _load_price_series(db)
    today = date.today()
    created = 0
    # 清除同类型未过期旧预测，避免重复
    db.query(PredictionResult).filter(
        PredictionResult.prediction_type == "price",
        PredictionResult.prediction_date == today,
    ).delete()
    for aid, series in series_map.items():
        model = models.get(aid)
        if not model:
            continue
        steps = min(months, 12)
        forecast = model.forecast(series, steps)
        for item in forecast:
            year, month = item["month"].split("-")
            db.add(
                PredictionResult(
                    production_area_id=aid,
                    prediction_type="price",
                    prediction_date=today,
                    target_date=date(int(year), int(month), 1),
                    predicted_value=item["value"],
                    lower_bound=item["lower"],
                    upper_bound=item["upper"],
                    model_name="orange_price_rf",
                    model_version=MODEL_VERSION,
                )
            )
            created += 1
    db.flush()
    return {"created": created, "months": months}


# ---------------- 病虫害 ----------------

def _build_pest_dataset(db: Session) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """构建 (X, y, meta)。meta 记录县区与月份，用于预测阶段的特征构造。"""
    ganzhou = db.scalar(select(Region).where(Region.adcode == "360700"))
    counties = db.scalars(
        select(Region).where(Region.parent_id == ganzhou.id)
    ).all() if ganzhou else []
    county_ids = [c.id for c in counties]

    planting = {
        r[0]: float(r[1] or 0)
        for r in db.execute(
            select(ProductionArea.region_id, func.sum(ProductionArea.planting_area)).group_by(
                ProductionArea.region_id
            )
        ).all()
    }

    records = db.execute(
        select(
            PestDiseaseRecord.date,
            PestDiseaseRecord.severity,
            PestDiseaseRecord.affected_area,
            ProductionArea.region_id,
        )
        .join(ProductionArea, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .order_by(PestDiseaseRecord.date)
    ).all()

    # (county, month) -> [ (severity_w, affected_area) ]
    occ: dict[tuple[int, str], list[tuple[float, float]]] = {}
    for d, sev, area, rid in records:
        ym = f"{d.year}-{d.month:02d}"
        occ.setdefault((rid, ym), []).append((SEVERITY_W.get(sev, 1), float(area or 0)))

    all_months = sorted({m for _, m in occ.keys()})
    if len(all_months) < 6:
        raise ValueError("病虫害历史数据不足，无法训练模型")

    X, y, meta = [], [], []
    for i, ym in enumerate(all_months):
        month_num = int(ym.split("-")[1])
        for rid in county_ids:
            hist = [
                (m, occ.get((rid, m), [])) for m in all_months[max(0, i - 12):i]
            ]
            hist_count = sum(len(v) for _, v in hist)
            hist_area = sum(a for _, v in hist for _, a in v)
            hist_sev = (
                np.mean([w for _, v in hist for w, _ in v]) if hist_count else 0.0
            )
            cur = occ.get((rid, ym), [])
            # 标签：当月若有发生记录取最严重程度映射，否则 low
            label = (
                label_from_severity(
                    max(cur, key=lambda t: t[0]) and
                    {1: "mild", 2: "moderate", 3: "severe"}[max(w for w, _ in cur)]
                )
                if cur
                else "low"
            )
            X.append(
                [
                    month_num,
                    (month_num - 1) // 3 + 1,
                    county_ids.index(rid),
                    planting.get(rid, 0) / 10000,
                    hist_count,
                    hist_area / 1000,
                    hist_sev,
                ]
            )
            y.append(label)
            meta.append({"county_id": rid, "month": ym})
    return np.array(X), np.array(y), meta


SEVERITY_W = {"mild": 1, "moderate": 2, "severe": 3}


def train_pest_model(db: Session) -> dict:
    X, y, _ = _build_pest_dataset(db)
    clf = PestRiskClassifier().fit(X, y)
    path = _store_path("pest_model_v1.joblib")
    joblib.dump(clf, path)
    _retire_old(db, "pest_disease")
    db.add(
        ModelInfo(
            model_name="pest_risk_rf",
            model_type="pest_disease",
            version=MODEL_VERSION,
            target="县区月度风险等级",
            algorithm="RandomForestClassifier",
            training_dataset=f"pest_disease_record({len(X)}样本)",
            evaluation_metric="accuracy/f1_macro",
            accuracy=clf.accuracy,
            model_path=str(path),
            status="active",
        )
    )
    db.flush()
    logger.info("病虫害模型训练完成 acc=%s f1=%s", clf.accuracy, clf.f1)
    return {"model": "pest_risk_rf", "version": MODEL_VERSION, "accuracy": clf.accuracy, "f1": clf.f1}


def predict_pest(db: Session, months: int = 3) -> dict:
    clf = joblib.load(_store_path("pest_model_v1.joblib"))
    ganzhou = db.scalar(select(Region).where(Region.adcode == "360700"))
    counties = db.scalars(select(Region).where(Region.parent_id == ganzhou.id)).all()
    county_ids = [c.id for c in counties]

    planting = {
        r[0]: float(r[1] or 0)
        for r in db.execute(
            select(ProductionArea.region_id, func.sum(ProductionArea.planting_area)).group_by(
                ProductionArea.region_id
            )
        ).all()
    }
    records = db.execute(
        select(
            PestDiseaseRecord.date,
            PestDiseaseRecord.severity,
            PestDiseaseRecord.affected_area,
            ProductionArea.region_id,
        )
        .join(ProductionArea, PestDiseaseRecord.production_area_id == ProductionArea.id)
        .order_by(PestDiseaseRecord.date)
    ).all()
    occ: dict[tuple[int, str], list[tuple[float, float]]] = {}
    for d, sev, area, rid in records:
        ym = f"{d.year}-{d.month:02d}"
        occ.setdefault((rid, ym), []).append((SEVERITY_W.get(sev, 1), float(area or 0)))

    all_months = sorted({m for _, m in occ.keys()})
    today = date.today()
    future_months = []
    cur = pd.Period(today, freq="M")
    for _ in range(min(months, 6)):
        future_months.append(str(cur))
        cur += 1

    db.query(PredictionResult).filter(
        PredictionResult.prediction_type == "pest_disease",
        PredictionResult.prediction_date == today,
    ).delete()

    created = 0
    for ym in future_months:
        month_num = int(ym.split("-")[1])
        # 用截至目前的12个月历史窗口
        hist_months = all_months[-12:]
        for rid in county_ids:
            hist = [(m, occ.get((rid, m), [])) for m in hist_months]
            hist_count = sum(len(v) for _, v in hist)
            hist_area = sum(a for _, v in hist for _, a in v)
            hist_sev = (
                np.mean([w for _, v in hist for w, _ in v]) if hist_count else 0.0
            )
            x = np.array(
                [[
                    month_num,
                    (month_num - 1) // 3 + 1,
                    county_ids.index(rid),
                    planting.get(rid, 0) / 10000,
                    hist_count,
                    hist_area / 1000,
                    hist_sev,
                ]]
            )
            proba = clf.predict_proba(x)[0]
            level = max(proba, key=proba.get)
            year, month = ym.split("-")
            db.add(
                PredictionResult(
                    region_id=rid,
                    prediction_type="pest_disease",
                    prediction_date=today,
                    target_date=date(int(year), int(month), 1),
                    predicted_value=round(float(proba.get(level, 0)), 4),
                    risk_level=level,
                    model_name="pest_risk_rf",
                    model_version=MODEL_VERSION,
                )
            )
            created += 1
    db.flush()
    return {"created": created, "months": len(future_months)}


def _retire_old(db: Session, model_type: str) -> None:
    db.query(ModelInfo).filter(
        ModelInfo.model_type == model_type, ModelInfo.status == "active"
    ).update({"status": "retired"}, synchronize_session=False)


def list_models(db: Session) -> list[ModelInfo]:
    return list(
        db.scalars(
            select(ModelInfo).order_by(ModelInfo.id.desc()).limit(50)
        ).all()
    )
