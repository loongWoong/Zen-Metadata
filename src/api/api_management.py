"""
API管理API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import uuid
import inspect
from fastapi.routing import APIRoute

from ..core.auth import User, PermissionEngine
from ..core.user_storage import UserStorage
from ..api.auth import get_current_user
from ..api import server

router = APIRouter(prefix="/api/api-management", tags=["API管理"])

# 全局依赖
user_storage: Optional[UserStorage] = None
permission_engine: Optional[PermissionEngine] = None


def set_dependencies(storage: UserStorage, engine: PermissionEngine):
    """设置依赖"""
    global user_storage, permission_engine
    user_storage = storage
    permission_engine = engine


class APIRouteConfig(BaseModel):
    """API路由配置"""
    id: str
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    required_roles: List[str] = []
    required_permissions: List[Dict[str, Any]] = []
    is_public: bool = False
    created_at: datetime
    updated_at: datetime


# 内存存储（实际应该使用数据库）
_api_route_storage: Dict[str, APIRouteConfig] = {}


def _scan_routes():
    """扫描所有路由"""
    routes = []
    for route in server.app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                if method != "HEAD" and method != "OPTIONS":
                    route_id = f"{method}:{route.path}"
                    if route_id not in _api_route_storage:
                        # 创建默认配置
                        config = APIRouteConfig(
                            id=str(uuid.uuid4()),
                            path=route.path,
                            method=method,
                            summary=route.summary or route.name,
                            description=route.description,
                            required_roles=[],
                            required_permissions=[],
                            is_public=False,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        _api_route_storage[route_id] = config
                    routes.append({
                        "id": _api_route_storage[route_id].id,
                        "path": route.path,
                        "method": method,
                        "summary": route.summary or route.name,
                        "description": route.description,
                        "required_roles": _api_route_storage[route_id].required_roles,
                        "required_permissions": _api_route_storage[route_id].required_permissions,
                        "is_public": _api_route_storage[route_id].is_public,
                    })
    return routes


class UpdateAPIRouteRequest(BaseModel):
    """更新API路由请求"""
    summary: Optional[str] = None
    description: Optional[str] = None
    required_roles: Optional[List[str]] = None
    required_permissions: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None


@router.get("/routes", response_model=Dict[str, Any])
async def list_api_routes(
    current_user: User = Depends(get_current_user)
):
    """列出所有API路由"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "api", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    routes = _scan_routes()
    
    return {
        "routes": routes,
        "count": len(routes)
    }


@router.get("/routes/{route_id}", response_model=Dict[str, Any])
async def get_api_route(
    route_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取API路由详情"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "api", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    config = next((c for c in _api_route_storage.values() if c.id == route_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="路由不存在")
    
    return {
        "id": config.id,
        "path": config.path,
        "method": config.method,
        "summary": config.summary,
        "description": config.description,
        "required_roles": config.required_roles,
        "required_permissions": config.required_permissions,
        "is_public": config.is_public,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }


@router.put("/routes/{route_id}", response_model=Dict[str, Any])
async def update_api_route(
    route_id: str,
    request: UpdateAPIRouteRequest,
    current_user: User = Depends(get_current_user)
):
    """更新API路由配置（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "api", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 获取配置
    config = next((c for c in _api_route_storage.values() if c.id == route_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="路由不存在")
    
    # 更新配置
    if request.summary is not None:
        config.summary = request.summary
    if request.description is not None:
        config.description = request.description
    if request.required_roles is not None:
        config.required_roles = request.required_roles
    if request.required_permissions is not None:
        config.required_permissions = request.required_permissions
    if request.is_public is not None:
        config.is_public = request.is_public
    
    config.updated_at = datetime.now()
    
    # 更新存储
    route_key = f"{config.method}:{config.path}"
    _api_route_storage[route_key] = config
    
    return {"success": True, "route_id": route_id}


@router.get("/statistics", response_model=Dict[str, Any])
async def get_api_statistics(
    current_user: User = Depends(get_current_user)
):
    """获取API统计信息"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "api", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    routes = _scan_routes()
    
    # 统计信息
    total_routes = len(routes)
    public_routes = len([r for r in routes if r.get("is_public", False)])
    protected_routes = total_routes - public_routes
    
    methods = {}
    for route in routes:
        method = route["method"]
        methods[method] = methods.get(method, 0) + 1
    
    return {
        "total_routes": total_routes,
        "public_routes": public_routes,
        "protected_routes": protected_routes,
        "methods": methods,
    }


