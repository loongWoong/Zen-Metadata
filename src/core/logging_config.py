"""
统一的日志配置模块
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    配置统一的日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        log_format: 日志格式（可选）
        
    Returns:
        配置好的 logger 实例
    """
    # 默认日志格式
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 创建 handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        handlers.append(file_handler)
    
    # 配置根 logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
        force=True  # 覆盖现有配置
    )
    
    # 返回根 logger
    logger = logging.getLogger("zen_metadata")
    logger.info(f"日志系统已初始化，级别: {log_level}, 文件: {log_file or '仅控制台'}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger
    
    Args:
        name: logger 名称（通常是模块名）
        
    Returns:
        Logger 实例
    """
    return logging.getLogger(f"zen_metadata.{name}")


