"""
统一的配置管理模块
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class FalkorDBConfig(BaseModel):
    """FalkorDB 配置"""
    host: str = Field(default="localhost", description="FalkorDB 主机地址")
    port: int = Field(default=6379, description="端口")
    password: str = Field(default="", description="密码")
    graph_name: str = Field(default="zen_metadata", description="图名称")


class SQLiteConfig(BaseModel):
    """SQLite 配置"""
    database: str = Field(default="data/zen_metadata.db", description="数据库路径")


class DuckDBConfig(BaseModel):
    """DuckDB 配置"""
    database: str = Field(default="data/zen_metadata_analytics.duckdb", description="数据库路径")


class APIConfig(BaseModel):
    """API 配置"""
    host: str = Field(default="0.0.0.0", description="主机地址")
    port: int = Field(default=8000, description="端口")
    debug: bool = Field(default=False, description="调试模式")


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    file: Optional[str] = Field(default=None, description="日志文件路径")


class AppConfig(BaseModel):
    """应用配置"""
    falkordb: FalkorDBConfig = Field(default_factory=FalkorDBConfig)
    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig)
    duckdb: DuckDBConfig = Field(default_factory=DuckDBConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # CORS 允许的 origins
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5175",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="CORS 允许的源"
    )
    
    # 元模型配置
    metamodel: Dict[str, Any] = Field(
        default_factory=lambda: {
            "metamodels_dir": "metamodels",
            "plugins_dir": "plugins",
            "enabled": True,
            "auto_load": True
        }
    )
    
    # 质量管理配置
    quality: Dict[str, Any] = Field(default_factory=dict)
    
    # 用户存储配置
    user_storage: Dict[str, Any] = Field(
        default_factory=lambda: {"database": "data/users.db"}
    )
    
    # 认证配置
    auth: Dict[str, Any] = Field(
        default_factory=lambda: {"secret_key": "your-secret-key-change-in-production"}
    )


# 全局配置实例
_config: Optional[AppConfig] = None


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置对象
    """
    global _config
    
    config_file = Path(config_path)
    config_dict: Dict[str, Any] = {}
    
    # 从文件加载配置
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}，使用默认配置")
    
    # 从环境变量覆盖配置
    config_dict = _apply_env_overrides(config_dict)
    
    # 构建配置对象
    try:
        # 如果配置文件中没有 cors_origins，使用 None 让 Pydantic 使用默认值
        cors_origins = config_dict.get('cors_origins')
        config_kwargs = {
            'falkordb': FalkorDBConfig(**config_dict.get('falkordb', {})),
            'sqlite': SQLiteConfig(**config_dict.get('sqlite', {})),
            'duckdb': DuckDBConfig(**config_dict.get('duckdb', {})),
            'api': APIConfig(**config_dict.get('api', {})),
            'logging': LoggingConfig(**config_dict.get('logging', {})),
            'metamodel': config_dict.get('metamodel', {}),
            'quality': config_dict.get('quality', {}),
            'user_storage': config_dict.get('user_storage', {}),
            'auth': config_dict.get('auth', {}),
        }
        # 只有当配置文件中明确指定了 cors_origins 时才传递，否则使用默认值
        if cors_origins is not None:
            config_kwargs['cors_origins'] = cors_origins
        
        _config = AppConfig(**config_kwargs)
    except Exception as e:
        print(f"警告: 配置解析失败: {e}，使用默认配置")
        _config = AppConfig()
    
    return _config


def _apply_env_overrides(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用环境变量覆盖
    
    Args:
        config_dict: 配置字典
        
    Returns:
        更新后的配置字典
    """
    # FalkorDB
    if os.getenv('FALKORDB_HOST'):
        config_dict.setdefault('falkordb', {})['host'] = os.getenv('FALKORDB_HOST')
    if os.getenv('FALKORDB_PORT'):
        config_dict.setdefault('falkordb', {})['port'] = int(os.getenv('FALKORDB_PORT', '6379'))
    if os.getenv('FALKORDB_PASSWORD'):
        config_dict.setdefault('falkordb', {})['password'] = os.getenv('FALKORDB_PASSWORD')
    
    # API
    if os.getenv('API_HOST'):
        config_dict.setdefault('api', {})['host'] = os.getenv('API_HOST')
    if os.getenv('API_PORT'):
        config_dict.setdefault('api', {})['port'] = int(os.getenv('API_PORT', '8000'))
    if os.getenv('API_DEBUG'):
        config_dict.setdefault('api', {})['debug'] = os.getenv('API_DEBUG').lower() == 'true'
    
    # Logging
    if os.getenv('LOG_LEVEL'):
        config_dict.setdefault('logging', {})['level'] = os.getenv('LOG_LEVEL')
    if os.getenv('LOG_FILE'):
        config_dict.setdefault('logging', {})['file'] = os.getenv('LOG_FILE')
    
    return config_dict


def get_config() -> AppConfig:
    """
    获取全局配置实例
    
    Returns:
        配置对象
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config

