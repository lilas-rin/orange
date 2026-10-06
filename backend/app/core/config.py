"""集中配置：全部来自环境变量，启动时校验，快速失败。"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "信丰脐橙产销数据分析与智能决策平台"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # 数据库（必填，缺失时启动即失败）
    DATABASE_URL: str

    # 安全（必填）
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS：显式来源，生产环境禁用通配符
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 机器学习模型存储目录
    ML_STORE_DIR: str = "ml_store"

    @property
    def is_production(self) -> bool:
        return not self.DEBUG


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
