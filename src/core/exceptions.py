"""
统一的异常处理模块
"""
from typing import Optional, Dict, Any


class ZenMetadataException(Exception):
    """Zen Metadata 基础异常类"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            details: 详细信息字典
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GraphStoreException(ZenMetadataException):
    """图存储异常"""
    pass


class CollectorException(ZenMetadataException):
    """采集器异常"""
    pass


class ValidationException(ZenMetadataException):
    """验证异常"""
    pass


class ConfigurationException(ZenMetadataException):
    """配置异常"""
    pass


class TaskException(ZenMetadataException):
    """任务异常"""
    pass


class AuthenticationException(ZenMetadataException):
    """认证异常"""
    pass


class PermissionException(ZenMetadataException):
    """权限异常"""
    pass


