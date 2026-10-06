"""Excel / CSV 批量导入：解析 → 校验 → 预览 → 确认写入。
支持的目标表：production(产量) / sales(销量) / price(价格)。"""
import io
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ImportValidationError, ValidationError
from app.models import PriceData, ProductionArea, ProductionData, Product, Region, SalesData

# 目标表 -> 列定义（必填列与可选列、类型）
SPECS = {
    "production": {
        "model": ProductionData,
        "required": ["产地", "日期", "产量(吨)"],
        "optional": ["品种", "种植面积(亩)", "单产(吨/亩)"],
    },
    "sales": {
        "model": SalesData,
        "required": ["销售地区", "日期", "销量(吨)", "销售额(万元)"],
        "optional": ["渠道"],
    },
    "price": {
        "model": PriceData,
        "required": ["产地", "日期", "平均价(元/kg)"],
        "optional": ["最高价(元/kg)", "最低价(元/kg)", "批发价(元/kg)"],
    },
}


def _parse_date(v) -> date | None:
    if pd.isna(v):
        return None
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(v) -> float | None:
    if pd.isna(v) or str(v).strip() == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_file(content: bytes, filename: str, target: str) -> pd.DataFrame:
    if target not in SPECS:
        raise ValidationError(f"不支持的导入目标: {target}")
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:  # noqa: BLE001
        raise ImportValidationError(f"文件解析失败: {e}") from e
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in SPECS[target]["required"] if c not in df.columns]
    if missing:
        raise ImportValidationError(f"缺少必需列: {', '.join(missing)}")
    return df


def preview(db: Session, content: bytes, filename: str, target: str) -> dict:
    """校验每一行，返回可预览的合法行与错误行，不写库。"""
    df = parse_file(content, filename, target)
    areas = {a.name: a.id for a in db.scalars(select(ProductionArea)).all()}
    products = {p.name: p.id for p in db.scalars(select(Product)).all()}
    regions = {r.name: r.id for r in db.scalars(select(Region)).all()}

    valid_rows: list[dict] = []
    error_rows: list[dict] = []
    for idx, row in df.iterrows():
        row_no = int(idx) + 2  # Excel 含表头，从第 2 行开始
        errors: list[str] = []
        item: dict = {}

        d = _parse_date(row.get("日期"))
        if not d:
            errors.append("日期为空或格式不正确")
        item["date"] = d.isoformat() if d else None

        if target in ("production", "price"):
            area_name = str(row.get("产地", "")).strip()
            area_id = areas.get(area_name)
            if not area_id:
                errors.append(f"产地「{area_name}」不存在")
            item["production_area_id"] = area_id
            pname = str(row.get("品种", "")).strip() if pd.notna(row.get("品种")) else ""
            item["product_id"] = products.get(pname) if pname else None
        else:
            region_name = str(row.get("销售地区", "")).strip()
            region_id = regions.get(region_name)
            if not region_id:
                errors.append(f"销售地区「{region_name}」不存在")
            item["region_id"] = region_id

        num_cols = {
            "production": [("产量(吨)", "production")],
            "sales": [("销量(吨)", "sales_volume"), ("销售额(万元)", "sales_amount")],
            "price": [("平均价(元/kg)", "average_price")],
        }[target]
        for col, field in num_cols:
            v = _to_float(row.get(col))
            if v is None or v <= 0:
                errors.append(f"{col} 必须为正数")
            item[field] = v

        if target == "production":
            item["planting_area"] = _to_float(row.get("种植面积(亩)"))
            item["yield_per_area"] = _to_float(row.get("单产(吨/亩)"))
        elif target == "sales":
            ch = row.get("渠道")
            item["sales_channel"] = str(ch).strip() if pd.notna(ch) else None
        elif target == "price":
            for col, field in [
                ("最高价(元/kg)", "highest_price"),
                ("最低价(元/kg)", "lowest_price"),
                ("批发价(元/kg)", "wholesale_price"),
            ]:
                item[field] = _to_float(row.get(col))

        if errors:
            error_rows.append({"row": row_no, "data": item, "errors": errors})
        else:
            valid_rows.append(item)

    return {
        "total": len(df),
        "valid_count": len(valid_rows),
        "error_count": len(error_rows),
        "valid_rows": valid_rows[:50],
        "error_rows": error_rows[:50],
    }


def commit(db: Session, content: bytes, filename: str, target: str) -> dict:
    """校验并写入数据库（多步写入在调用方事务中完成）。"""
    df = parse_file(content, filename, target)
    result = preview(db, content, filename, target)
    if result["error_count"] > 0:
        raise ImportValidationError(
            f"存在 {result['error_count']} 行错误数据，请先修正后重试",
            details=result["error_rows"][:20],
        )
    model = SPECS[target]["model"]
    for item in result["valid_rows"]:
        db.add(model(**item))
    db.flush()
    return {"imported": result["valid_count"]}
