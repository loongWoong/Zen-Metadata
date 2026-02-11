"""
菜单管理API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import uuid

from ..core.auth import User, PermissionEngine
from ..core.user_storage import UserStorage
from ..api.auth import get_current_user

router = APIRouter(prefix="/api/menu", tags=["菜单管理"])

# 全局依赖
user_storage: Optional[UserStorage] = None
permission_engine: Optional[PermissionEngine] = None


def set_dependencies(storage: UserStorage, engine: PermissionEngine):
    """设置依赖"""
    global user_storage, permission_engine
    user_storage = storage
    permission_engine = engine


class MenuItem(BaseModel):
    """菜单项模型"""
    id: str
    key: str
    label: str
    icon: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0
    required_roles: List[str] = []
    required_permissions: List[Dict[str, Any]] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class CreateMenuRequest(BaseModel):
    """创建菜单请求"""
    key: str
    label: str
    icon: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0
    required_roles: List[str] = []
    required_permissions: List[Dict[str, Any]] = []


class UpdateMenuRequest(BaseModel):
    """更新菜单请求"""
    label: Optional[str] = None
    icon: Optional[str] = None
    path: Optional[str] = None
    parent_id: Optional[str] = None
    order: Optional[int] = None
    required_roles: Optional[List[str]] = None
    required_permissions: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None


# 内存存储（实际应该使用数据库）
_menu_storage: Dict[str, MenuItem] = {}


def _init_default_menus():
    """初始化默认菜单"""
    default_menus = [
        {"key": "/dashboard", "label": "仪表板", "icon": "DashboardOutlined", "path": "/dashboard", "order": 1},
        {"key": "/graph", "label": "图可视化", "icon": "NodeIndexOutlined", "path": "/graph", "order": 2},
        {"key": "/entities", "label": "实体浏览器", "icon": "DatabaseOutlined", "path": "/entities", "order": 3},
        {"key": "/collection", "label": "采集管理", "icon": "CloudUploadOutlined", "path": "/collection", "order": 4},
        {"key": "/agents", "label": "代理管理", "icon": "CloudServerOutlined", "path": "/agents", "order": 5},
        {"key": "/analytics", "label": "统计分析", "icon": "BarChartOutlined", "path": "/analytics", "order": 6},
        {"key": "/quality", "label": "质量管理", "icon": "SafetyOutlined", "path": "/quality", "order": 7},
        {"key": "/metamodel", "label": "元模型管理", "icon": "ApartmentOutlined", "path": "/metamodel", "order": 8},
        {"key": "/lineage", "label": "血缘追踪", "icon": "ShareAltOutlined", "path": "/lineage", "order": 9},
        {"key": "/search", "label": "搜索检索", "icon": "SearchOutlined", "path": "/search", "order": 10},
        {"key": "/version", "label": "版本控制", "icon": "HistoryOutlined", "path": "/version", "order": 11},
        {"key": "/collaboration", "label": "协作", "icon": "CommentOutlined", "path": "/collaboration", "order": 12},
        {"key": "/users", "label": "用户管理", "icon": "TeamOutlined", "path": "/users", "order": 13, "required_roles": ["admin"]},
        {"key": "/governance", "label": "数据治理", "icon": "TagsOutlined", "path": "/governance", "order": 14, "children": [
            {"key": "/governance/tags", "label": "标签管理", "icon": "TagsOutlined", "path": "/governance/tags", "order": 1},
            {"key": "/governance/standards", "label": "数据标准", "icon": "FileTextOutlined", "path": "/governance/standards", "order": 2},
            {"key": "/governance/catalog", "label": "数据目录", "icon": "FolderOpenOutlined", "path": "/governance/catalog", "order": 3},
        ]},
    ]
    
    for menu_data in default_menus:
        menu_id = str(uuid.uuid4())
        menu = MenuItem(
            id=menu_id,
            key=menu_data["key"],
            label=menu_data["label"],
            icon=menu_data.get("icon"),
            path=menu_data.get("path"),
            order=menu_data.get("order", 0),
            required_roles=menu_data.get("required_roles", []),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        _menu_storage[menu_id] = menu
        
        # 处理子菜单
        if "children" in menu_data:
            for child_data in menu_data["children"]:
                child_id = str(uuid.uuid4())
                child = MenuItem(
                    id=child_id,
                    key=child_data["key"],
                    label=child_data["label"],
                    icon=child_data.get("icon"),
                    path=child_data.get("path"),
                    parent_id=menu_id,
                    order=child_data.get("order", 0),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                _menu_storage[child_id] = child


# 初始化默认菜单
_init_default_menus()


@router.get("/items", response_model=Dict[str, Any])
async def list_menu_items(
    current_user: User = Depends(get_current_user)
):
    """列出菜单项（根据用户权限过滤）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 获取所有菜单
    all_menus = list(_menu_storage.values())
    
    # 根据用户权限过滤
    filtered_menus = []
    for menu in all_menus:
        if not menu.is_active:
            continue
        
        # 检查角色权限
        if menu.required_roles:
            if not any(role in current_user.roles for role in menu.required_roles):
                continue
        
        # 检查权限
        if menu.required_permissions:
            has_permission = False
            for perm_data in menu.required_permissions:
                if permission_engine.check_permission(
                    current_user,
                    perm_data.get("resource", ""),
                    perm_data.get("action", ""),
                ):
                    has_permission = True
                    break
            if not has_permission:
                continue
        
        filtered_menus.append(menu)
    
    # 构建树形结构
    menu_dict = {menu.id: menu for menu in filtered_menus}
    root_menus = [menu for menu in filtered_menus if not menu.parent_id]
    
    def build_tree(menu: MenuItem) -> Dict[str, Any]:
        children = [m for m in filtered_menus if m.parent_id == menu.id]
        result = {
            "id": menu.id,
            "key": menu.key,
            "label": menu.label,
            "icon": menu.icon,
            "path": menu.path,
            "order": menu.order,
            "required_roles": menu.required_roles,
            "required_permissions": menu.required_permissions,
        }
        if children:
            result["children"] = [build_tree(child) for child in sorted(children, key=lambda x: x.order)]
        return result
    
    tree = [build_tree(menu) for menu in sorted(root_menus, key=lambda x: x.order)]
    
    return {
        "menus": tree,
        "count": len(filtered_menus)
    }


@router.get("/items/all", response_model=Dict[str, Any])
async def list_all_menu_items(
    current_user: User = Depends(get_current_user)
):
    """列出所有菜单项（管理员）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "menu", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    all_menus = list(_menu_storage.values())
    
    # 构建树形结构
    menu_dict = {menu.id: menu for menu in all_menus}
    root_menus = [menu for menu in all_menus if not menu.parent_id]
    
    def build_tree(menu: MenuItem) -> Dict[str, Any]:
        children = [m for m in all_menus if m.parent_id == menu.id]
        result = {
            "id": menu.id,
            "key": menu.key,
            "label": menu.label,
            "icon": menu.icon,
            "path": menu.path,
            "parent_id": menu.parent_id,
            "order": menu.order,
            "required_roles": menu.required_roles,
            "required_permissions": menu.required_permissions,
            "is_active": menu.is_active,
            "created_at": menu.created_at.isoformat(),
            "updated_at": menu.updated_at.isoformat(),
        }
        if children:
            result["children"] = [build_tree(child) for child in sorted(children, key=lambda x: x.order)]
        return result
    
    tree = [build_tree(menu) for menu in sorted(root_menus, key=lambda x: x.order)]
    
    return {
        "menus": tree,
        "count": len(all_menus)
    }


@router.post("/items", response_model=Dict[str, Any])
async def create_menu_item(
    request: CreateMenuRequest,
    current_user: User = Depends(get_current_user)
):
    """创建菜单项（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "menu", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查key是否已存在
    existing_menu = next((m for m in _menu_storage.values() if m.key == request.key), None)
    if existing_menu:
        raise HTTPException(status_code=400, detail="菜单key已存在")
    
    # 检查父菜单是否存在
    if request.parent_id:
        parent_menu = _menu_storage.get(request.parent_id)
        if not parent_menu:
            raise HTTPException(status_code=400, detail="父菜单不存在")
    
    # 创建菜单
    menu = MenuItem(
        id=str(uuid.uuid4()),
        key=request.key,
        label=request.label,
        icon=request.icon,
        path=request.path,
        parent_id=request.parent_id,
        order=request.order,
        required_roles=request.required_roles,
        required_permissions=request.required_permissions,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    _menu_storage[menu.id] = menu
    
    return {"success": True, "menu_id": menu.id}


@router.put("/items/{menu_id}", response_model=Dict[str, Any])
async def update_menu_item(
    menu_id: str,
    request: UpdateMenuRequest,
    current_user: User = Depends(get_current_user)
):
    """更新菜单项（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "menu", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 获取菜单
    menu = _menu_storage.get(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    
    # 更新菜单
    if request.label is not None:
        menu.label = request.label
    if request.icon is not None:
        menu.icon = request.icon
    if request.path is not None:
        menu.path = request.path
    if request.parent_id is not None:
        if request.parent_id:
            parent_menu = _menu_storage.get(request.parent_id)
            if not parent_menu:
                raise HTTPException(status_code=400, detail="父菜单不存在")
        menu.parent_id = request.parent_id
    if request.order is not None:
        menu.order = request.order
    if request.required_roles is not None:
        menu.required_roles = request.required_roles
    if request.required_permissions is not None:
        menu.required_permissions = request.required_permissions
    if request.is_active is not None:
        menu.is_active = request.is_active
    
    menu.updated_at = datetime.now()
    _menu_storage[menu_id] = menu
    
    return {"success": True, "menu_id": menu_id}


@router.delete("/items/{menu_id}", response_model=Dict[str, Any])
async def delete_menu_item(
    menu_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除菜单项（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "menu", "delete"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 获取菜单
    menu = _menu_storage.get(menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")
    
    # 检查是否有子菜单
    children = [m for m in _menu_storage.values() if m.parent_id == menu_id]
    if children:
        raise HTTPException(status_code=400, detail="无法删除：该菜单下有子菜单")
    
    # 删除菜单
    del _menu_storage[menu_id]
    
    return {"success": True, "message": f"菜单 {menu.label} 已删除"}


