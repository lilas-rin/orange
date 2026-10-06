"""数据库初始化：创建库 → 生成初始迁移（若无可自动发现）→ 升级到最新。

用法（在 backend/ 目录下）:
    .venv/Scripts/python.exe -m scripts.init_db
"""
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from app.core.config import settings


def create_database() -> None:
    db_name = settings.DATABASE_URL.rsplit("/", 1)[1].split("?")[0]
    server_url = settings.DATABASE_URL.rsplit("/", 1)[0]
    engine = create_engine(server_url)
    with engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    print(f"[OK] 数据库 {db_name} 已就绪")
    engine.dispose()


def run_alembic(*args: str) -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [str(backend_dir / ".venv" / "Scripts" / "python.exe"), "-m", "alembic", *args],
        cwd=backend_dir,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    create_database()
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    has_migration = any(versions_dir.glob("*.py"))
    if not has_migration:
        print("[..] 生成初始迁移 ...")
        run_alembic("revision", "--autogenerate", "-m", "initial tables")
    print("[..] 执行数据库迁移 ...")
    run_alembic("upgrade", "head")
    print("[OK] 数据库结构已就绪")


if __name__ == "__main__":
    main()
