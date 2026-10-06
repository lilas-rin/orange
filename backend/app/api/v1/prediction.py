"""智能预测与决策 API：模型训练、执行预测、决策建议。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.screen import DecisionAdviceOut, ModelInfoOut, PredictionResultOut
from app.services import decision_service, log_service, ml_service, screen_service

router = APIRouter(tags=["智能预测与决策"])


@router.post("/predictions/train")
def train_model(
    request: Request,
    model_type: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("operator")),
):
    """model_type: price / pest_disease"""
    try:
        if model_type == "price":
            result = ml_service.train_price_model(db)
        elif model_type == "pest_disease":
            result = ml_service.train_pest_model(db)
        else:
            raise ValidationError("model_type 必须为 price 或 pest_disease")
    except ValueError as e:
        raise ValidationError(str(e)) from e
    log_service.record(
        db,
        f"训练模型 {result['model']}({result['version']})",
        "prediction",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
    )
    db.commit()
    return ok(result)


@router.post("/predictions/run")
def run_prediction(
    request: Request,
    model_type: str,
    months: int = 6,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("operator")),
):
    try:
        if model_type == "price":
            result = ml_service.predict_price(db, months)
        elif model_type == "pest_disease":
            result = ml_service.predict_pest(db, months)
        else:
            raise ValidationError("model_type 必须为 price 或 pest_disease")
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except FileNotFoundError as e:
        raise ValidationError("模型尚未训练，请先执行训练") from e
    log_service.record(
        db,
        f"执行 {model_type} 预测，生成 {result['created']} 条结果",
        "prediction",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
    )
    db.commit()
    return ok(result)


@router.get("/predictions")
def list_predictions(
    type: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(screen_service.latest_predictions(db, type, limit))


@router.get("/models", response_model=ApiResponse[list[ModelInfoOut]])
def list_models(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    models = ml_service.list_models(db)
    return ok([ModelInfoOut.model_validate(m).model_dump() for m in models])


@router.post("/decisions/refresh")
def refresh_decisions(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("operator")),
):
    result = decision_service.refresh(db)
    log_service.record(
        db,
        f"生成决策建议 {result['created']} 条",
        "decision",
        user_id=user.id,
        method="POST",
        path=str(request.url.path),
    )
    db.commit()
    return ok(result)


@router.get("/decisions", response_model=ApiResponse[list[dict]])
def list_decisions(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(screen_service.latest_decisions(db, limit))
