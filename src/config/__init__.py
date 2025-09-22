"""配置模块"""
from .settings import (
    ai_config,
    db_config, 
    assessment_config,
    path_config,
    system_config,
    AIConfig,
    DatabaseConfig,
    AssessmentConfig,
    PathConfig,
    SystemConfig
)
from functools import lru_cache


@lru_cache()
def get_settings():
    """获取系统设置"""
    class Settings:
        # 应用基本信息
        app_name: str = "AI助教评估系统"
        app_version: str = "1.0.0"
        environment: str = "development"
        
        # 服务配置
        host: str = system_config.host
        port: int = system_config.port
        debug: bool = system_config.debug
        
        # 日志配置
        log_level: str = system_config.log_level
        
        # 数据库配置
        database_url: str = db_config.database_url
        
        # CORS配置
        cors_origins: list = ["*"]
        
    return Settings()


__all__ = [
    "get_settings",
    "ai_config",
    "db_config", 
    "assessment_config",
    "path_config",
    "system_config",
    "AIConfig",
    "DatabaseConfig", 
    "AssessmentConfig",
    "PathConfig",
    "SystemConfig"
]