"""操作日志服务。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OperationLog, User


def record(
    db: Session,
    operation: str,
    module: str,
    user_id: int | None = None,
    method: str | None = None,
    path: str | None = None,
    ip: str | None = None,
    result: str = "success",
) -> None:
    db.add(
        OperationLog(
            user_id=user_id,
            operation=operation,
            module=module,
            request_method=method,
            request_path=path,
            ip=ip,
            result=result,
        )
    )
    db.flush()


def list_logs(
    db: Session, page: int, page_size: int, module: str | None, result: str | None
) -> tuple[list[dict], int]:
    conds = []
    if module:
        conds.append(OperationLog.module == module)
    if result:
        conds.append(OperationLog.result == result)

    count_stmt = select(func.count()).select_from(OperationLog)
    for c in conds:
        count_stmt = count_stmt.where(c)
    total = int(db.scalar(count_stmt) or 0)

    stmt = (
        select(OperationLog, User.username)
        .outerjoin(User, OperationLog.user_id == User.id)
        .order_by(OperationLog.id.desc())
    )
    for c in conds:
        stmt = stmt.where(c)
    rows_raw = db.execute(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()

    rows = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "operation": log.operation,
            "module": log.module,
            "request_method": log.request_method,
            "request_path": log.request_path,
            "ip": log.ip,
            "result": log.result,
            "created_at": log.created_at,
        }
        for log, username in rows_raw
    ]
    return rows, total
