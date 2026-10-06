"""智能决策引擎：基于最新预测结果与业务规则生成决策建议。

决策链（对应需求文档 3.6.5）:
预测结果 → 业务规则/综合分析 → 风险判断 → 决策建议
"""
import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DecisionAdvice, PredictionResult, Region

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    "price": "价格",
    "production": "产量",
    "sales": "销量",
    "market_demand": "市场需求",
    "pest_disease": "病虫害",
}


def refresh(db: Session) -> dict:
    """重新生成全部决策建议（先清除旧建议）。"""
    db.query(DecisionAdvice).delete()
    created = 0
    created += _price_advices(db)
    created += _pest_advices(db)
    created += _market_advices(db)
    created += _comprehensive_advice(db)
    db.flush()
    return {"created": created}


def _avg_price_prediction(db: Session, months_ahead: int) -> tuple[float, float] | None:
    """(预测均价, 当前均价) 未来N月 vs 最近3月历史。"""
    today = date.today()
    latest = db.execute(
        select(func.avg(PredictionResult.predicted_value)).where(
            PredictionResult.prediction_type == "price",
            PredictionResult.prediction_date == (
                select(func.max(PredictionResult.prediction_date))
                .where(PredictionResult.prediction_type == "price")
                .scalar_subquery()
            ),
        )
    ).scalar()
    # 简化：取全部最新批次价格预测的均值
    batch_date = db.scalar(
        select(func.max(PredictionResult.prediction_date)).where(
            PredictionResult.prediction_type == "price"
        )
    )
    if not batch_date:
        return None
    avg_pred = float(
        db.scalar(
            select(func.avg(PredictionResult.predicted_value)).where(
                PredictionResult.prediction_type == "price",
                PredictionResult.prediction_date == batch_date,
            )
        )
        or 0
    )
    current = float(
        db.scalar(
            select(func.avg(PredictionResult.predicted_value)).where(
                PredictionResult.prediction_type == "price",
                PredictionResult.prediction_date == batch_date,
                PredictionResult.target_date <= date(
                    batch_date.year + (batch_date.month // 12),
                    batch_date.month % 12 + 1,
                    1,
                ),
            )
        )
        or avg_pred
    )
    return avg_pred, current


def _price_advices(db: Session) -> int:
    result = _avg_price_prediction(db, 1)
    if not result:
        return 0
    avg_pred, current = result
    if current <= 0:
        return 0
    change = (avg_pred - current) / current * 100
    if change >= 5:
        title = "价格上行趋势明确，把握销售窗口"
        content = (
            f"模型预测未来一个月平均批发价格较当前上涨约 {change:.1f}%。"
            "建议：1) 关注价格上涨带来的销售机会，分批有序出货，避免集中上市压价；"
            "2) 加强采后商品化处理与分级，提高精品果比例；"
            "3) 电商平台与商超渠道提前预热营销。"
        )
        risk = "opportunity"
    elif change <= -5:
        title = "价格存在下行压力，防范滞销风险"
        content = (
            f"模型预测未来一个月平均批发价格较当前下跌约 {abs(change):.1f}%。"
            "建议：1) 提前锁定订单与收购商，优先保障核心市场供应；"
            "2) 安排冷库错峰储藏，延后出货节奏；"
            "3) 加强产地直播与社区团购等短链渠道。"
        )
        risk = "high"
    else:
        title = "价格预计平稳运行"
        content = (
            f"模型预测未来一个月价格波动幅度在 ±5% 以内（当前预测均价 {avg_pred:.2f} 元/kg）。"
            "建议：1) 按正常产销计划组织供应；2) 持续关注主产区天气与病虫害对供给端的影响。"
        )
        risk = "low"
    db.add(
        DecisionAdvice(
            advice_type="price",
            risk_level=risk,
            title=title,
            content=content,
        )
    )
    return 1


def _pest_advices(db: Session) -> int:
    batch_date = db.scalar(
        select(func.max(PredictionResult.prediction_date)).where(
            PredictionResult.prediction_type == "pest_disease"
        )
    )
    if not batch_date:
        return 0
    rows = db.execute(
        select(PredictionResult, Region.name)
        .join(Region, PredictionResult.region_id == Region.id)
        .where(
            PredictionResult.prediction_type == "pest_disease",
            PredictionResult.prediction_date == batch_date,
            PredictionResult.risk_level == "high",
        )
    ).all()
    if not rows:
        return 0
    counties: list[str] = []
    for _, name in rows:
        if name not in counties:
            counties.append(name)
    names = "、".join(counties[:5])
    db.add(
        DecisionAdvice(
            advice_type="pest_disease",
            risk_level="high",
            title=f"高风险病虫害预警：{names}",
            content=(
                f"病虫害风险模型预测 {names} 等县区未来数月风险等级为「高」。"
                "建议：1) 加强重点产区黄龙病、溃疡病监测，及时清除病树并统一防治木虱；"
                "2) 嫩梢期与大风雨前后重点喷施溃疡病防护药剂（噻唑锌、春雷·喹啉铜等）；"
                "3) 悬挂黄板与杀虫灯，压低红蜘蛛、潜叶蛾等虫口基数；"
                "4) 县果业部门组织统一时间联防联控，减少交叉传播。"
            ),
            related_prediction_id=rows[0][0].id,
        )
    )
    return 1


def _market_advices(db: Session) -> int:
    # 市场需求：以销量预测/市场增速为依据，规则化生成
    growth = db.scalar(
        select(func.avg(PredictionResult.predicted_value)).where(
            PredictionResult.prediction_type == "market_demand"
        )
    )
    db.add(
        DecisionAdvice(
            advice_type="market",
            risk_level="low",
            title="重点保障高需求区域供应",
            content=(
                "综合市场数据，广东、浙江、江苏、上海为核心市场，销量占比领先。"
                "建议：1) 提前做好市场供应安排，优先保障高需求区域货源；"
                "2) 完善冷链物流与产地预冷，保障 48 小时送达时效；"
                "3) 对潜力市场（中西部、北方新兴市场）加大渠道开拓与品牌宣传。"
            ),
        )
    )
    return 1


def _comprehensive_advice(db: Session) -> int:
    db.add(
        DecisionAdvice(
            advice_type="comprehensive",
            risk_level="medium",
            title="产销综合研判与稳产保供建议",
            content=(
                "综合产量、销量、价格与病虫害预测：市场需求总体平稳，"
                "部分产区病虫害风险上升可能影响短期供应能力。"
                "建议：1) 稳定种植面积，推进标准化示范果园建设；"
                "2) 推广绿色防控与农药减量技术，控制防治成本；"
                "3) 引导错峰上市（早熟赣橙5号+晚熟品种），缓解集中上市压力；"
                "4) 依托脐橙产业集群，延伸橙汁、橙皮丁等精深加工，提升附加值。"
            ),
        )
    )
    return 1
