"""
认证与授权API
"""
from fastapi import APIRouter, HTTPException, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import secrets
import uuid

from ..core.auth import (
    User, Team, Space, APIToken, Role, Permission,
    AuthService, PermissionEngine
)
from ..core.user_storage import UserStorage
from ..core.collaboration import ApprovalStatus, ApprovalLevel, Approval

router = APIRouter(prefix="/api/auth", tags=["认证与授权"])

# 全局依赖
user_storage: Optional[UserStorage] = None
auth_service: Optional[AuthService] = None
permission_engine: Optional[PermissionEngine] = None

security = HTTPBearer()


def set_dependencies(storage: UserStorage, auth: AuthService, engine: PermissionEngine):
    """设置依赖"""
    global user_storage, auth_service, permission_engine
    user_storage = storage
    auth_service = auth
    permission_engine = engine


# 请求模型
class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    email: Optional[EmailStr] = None
    password: str


class CreateUserRequest(BaseModel):
    """创建用户请求"""
    username: str
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    roles: list[str] = []
    is_active: bool = True
    is_superuser: bool = False
    auth_provider: str = "builtin"
    auth_provider_id: Optional[str] = None


class CreateTeamRequest(BaseModel):
    """创建团队请求"""
    name: str
    description: Optional[str] = None
    members: list[str] = []


class CreateSpaceRequest(BaseModel):
    """创建工作空间请求"""
    name: str
    description: Optional[str] = None
    team_id: Optional[str] = None
    is_public: bool = False
    members: list[str] = []


class CreateAPITokenRequest(BaseModel):
    """创建API Token请求"""
    name: str
    permissions: list[Dict[str, Any]] = []
    expires_days: Optional[int] = None


# 依赖函数
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """获取当前用户"""
    if not auth_service or not user_storage:
        raise HTTPException(status_code=500, detail="认证服务未初始化")
    
    token = credentials.credentials
    payload = auth_service.decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌载荷",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = user_storage.get_user(user_id=user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """获取当前用户（可选）"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")
    if not auth_service or not user_storage:
        return None
    
    payload = auth_service.decode_access_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = user_storage.get_user(user_id=user_id)
    if not user or not user.is_active:
        return None
    
    return user


# API端点
@router.post("/register", response_model=Dict[str, Any])
async def register(request: RegisterRequest):
    """用户注册"""
    print(f"[AUTH] 注册请求 - 用户名: {request.username}, 邮箱: {request.email}")
    
    if not user_storage or not auth_service:
        print("[AUTH] 错误: 认证服务未初始化")
        raise HTTPException(status_code=500, detail="认证服务未初始化")
    
    # 检查用户名是否已存在
    existing_user = user_storage.get_user(username=request.username)
    if existing_user:
        print(f"[AUTH] 错误: 用户名已存在 - {request.username}")
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    if request.email:
        existing_user = user_storage.get_user(email=request.email)
        if existing_user:
            print(f"[AUTH] 错误: 邮箱已存在 - {request.email}")
            raise HTTPException(status_code=400, detail="邮箱已存在")
    
    # 创建用户
    print(f"[AUTH] 开始创建用户 - 用户名: {request.username}")
    try:
        password_bytes = request.password.encode('utf-8')
        print(f"[AUTH] 密码长度: {len(password_bytes)} 字节")
        
        password_hash = auth_service.hash_password(request.password)
        print(f"[AUTH] 密码哈希成功")
        
        user = User(
            id=str(uuid.uuid4()),
            username=request.username,
            email=request.email,
            password_hash=password_hash,
            roles=["viewer"],  # 默认角色
            is_active=True,
            auth_provider="builtin"
        )
        
        if not user_storage.create_user(user):
            print("[AUTH] 错误: 创建用户失败")
            raise HTTPException(status_code=500, detail="创建用户失败")
        
        print(f"[AUTH] 用户创建成功 - ID: {user.id}")
        
        # 生成访问令牌
        access_token = auth_service.create_access_token(
            data={"sub": user.id, "username": user.username}
        )
        print(f"[AUTH] 访问令牌生成成功")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": user.roles
            }
        }
    except Exception as e:
        print(f"[AUTH] 异常: {type(e).__name__} - {str(e)}")
        import traceback
        print(f"[AUTH] Traceback:\n{traceback.format_exc()}")
        raise


@router.post("/login", response_model=Dict[str, Any])
async def login(request: LoginRequest):
    """用户登录"""
    if not user_storage or not auth_service:
        raise HTTPException(status_code=500, detail="认证服务未初始化")
    
    # 查找用户
    user = user_storage.get_user(username=request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="用户已被禁用")
    
    # 验证密码
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="该用户未设置密码")
    
    if not auth_service.verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 更新最后登录时间
    user.last_login = datetime.now()
    user_storage.update_user(user)
    
    # 生成访问令牌
    access_token = auth_service.create_access_token(
        data={"sub": user.id, "username": user.username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
            "teams": user.teams,
            "spaces": user.spaces
        }
    }


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "teams": current_user.teams,
        "spaces": current_user.spaces,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_user)
):
    """创建用户（需要管理员权限）"""
    if not user_storage or not auth_service or not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "user", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查用户名是否已存在
    existing_user = user_storage.get_user(username=request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 创建用户
    password_hash = None
    if request.password:
        password_hash = auth_service.hash_password(request.password)
    
    user = User(
        id=str(uuid.uuid4()),
        username=request.username,
        email=request.email,
        password_hash=password_hash,
        roles=request.roles,
        is_active=request.is_active,
        is_superuser=request.is_superuser,
        auth_provider=request.auth_provider,
        auth_provider_id=request.auth_provider_id
    )
    
    if not user_storage.create_user(user):
        raise HTTPException(status_code=500, detail="创建用户失败")
    
    return {"success": True, "user_id": user.id}


@router.get("/users", response_model=Dict[str, Any])
async def list_users(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """列出用户"""
    if not user_storage or not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "user", "read"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    users = user_storage.list_users(limit=limit, offset=offset)
    return {
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "roles": u.roles,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ],
        "count": len(users)
    }


@router.post("/teams", response_model=Dict[str, Any])
async def create_team(
    request: CreateTeamRequest,
    current_user: User = Depends(get_current_user)
):
    """创建团队"""
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    team = Team(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        members=request.members + [current_user.id]  # 创建者自动加入
    )
    
    if not user_storage.create_team(team):
        raise HTTPException(status_code=500, detail="创建团队失败")
    
    # 更新用户的团队列表
    current_user.teams.append(team.id)
    user_storage.update_user(current_user)
    
    return {"success": True, "team_id": team.id}


@router.get("/teams", response_model=Dict[str, Any])
async def list_teams(current_user: User = Depends(get_current_user)):
    """列出团队"""
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    teams = user_storage.list_teams()
    return {
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "members": t.members,
                "created_at": t.created_at.isoformat()
            }
            for t in teams
        ],
        "count": len(teams)
    }


@router.post("/spaces", response_model=Dict[str, Any])
async def create_space(
    request: CreateSpaceRequest,
    current_user: User = Depends(get_current_user)
):
    """创建工作空间"""
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    space = Space(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        team_id=request.team_id,
        owner_id=current_user.id,
        members=request.members + [current_user.id],  # 创建者自动加入
        is_public=request.is_public
    )
    
    if not user_storage.create_space(space):
        raise HTTPException(status_code=500, detail="创建工作空间失败")
    
    # 更新用户的空间列表
    current_user.spaces.append(space.id)
    user_storage.update_user(current_user)
    
    return {"success": True, "space_id": space.id}


@router.post("/tokens", response_model=Dict[str, Any])
async def create_api_token(
    request: CreateAPITokenRequest,
    current_user: User = Depends(get_current_user)
):
    """创建API Token"""
    if not user_storage or not auth_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 生成Token
    token_value = auth_service.generate_api_token()
    token_hash = auth_service.hash_token(token_value)
    
    # 计算过期时间
    expires_at = None
    if request.expires_days:
        expires_at = datetime.now() + timedelta(days=request.expires_days)
    
    # 创建Token对象
    permissions = [Permission(**p) for p in request.permissions]
    api_token = APIToken(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        token_hash=token_hash,
        name=request.name,
        permissions=permissions,
        expires_at=expires_at
    )
    
    if not user_storage.create_api_token(api_token):
        raise HTTPException(status_code=500, detail="创建Token失败")
    
    # 返回Token值（仅此一次）
    return {
        "success": True,
        "token": token_value,
        "token_id": api_token.id,
        "expires_at": expires_at.isoformat() if expires_at else None
    }


@router.get("/roles", response_model=Dict[str, Any])
async def list_roles(current_user: User = Depends(get_current_user)):
    """列出所有角色"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    roles = permission_engine.list_roles()
    return {
        "roles": [
            {
                "name": r.name,
                "description": r.description,
                "permissions": [
                    {
                        "resource": p.resource,
                        "action": p.action,
                        "scope": p.scope
                    }
                    for p in r.permissions
                ]
            }
            for r in roles
        ],
        "count": len(roles)
    }


class CreateRoleRequest(BaseModel):
    """创建角色请求"""
    name: str
    description: Optional[str] = None
    permissions: List[Dict[str, Any]] = []


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""
    description: Optional[str] = None
    permissions: List[Dict[str, Any]] = []


@router.post("/roles", response_model=Dict[str, Any])
async def create_role(
    request: CreateRoleRequest,
    current_user: User = Depends(get_current_user)
):
    """创建角色（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "role", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查角色是否已存在
    existing_role = permission_engine.get_role(request.name)
    if existing_role:
        raise HTTPException(status_code=400, detail="角色已存在")
    
    # 创建角色
    permissions = [Permission(**p) for p in request.permissions]
    role = Role(
        name=request.name,
        description=request.description,
        permissions=permissions
    )
    
    permission_engine.add_role(role)
    
    return {"success": True, "role_name": role.name}


@router.put("/roles/{role_name}", response_model=Dict[str, Any])
async def update_role(
    role_name: str,
    request: UpdateRoleRequest,
    current_user: User = Depends(get_current_user)
):
    """更新角色（需要管理员权限）"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "role", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查角色是否存在
    existing_role = permission_engine.get_role(role_name)
    if not existing_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 更新角色
    permissions = [Permission(**p) for p in request.permissions] if request.permissions else existing_role.permissions
    updated_role = Role(
        name=role_name,
        description=request.description if request.description is not None else existing_role.description,
        permissions=permissions
    )
    
    permission_engine.add_role(updated_role)
    
    return {"success": True, "role_name": role_name}


@router.delete("/roles/{role_name}", response_model=Dict[str, Any])
async def delete_role(
    role_name: str,
    current_user: User = Depends(get_current_user)
):
    """删除角色（需要管理员权限）"""
    if not permission_engine or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "role", "delete"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查角色是否存在
    existing_role = permission_engine.get_role(role_name)
    if not existing_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    # 检查是否有用户使用该角色
    users = user_storage.list_users(limit=1000, offset=0)
    users_with_role = [u for u in users if role_name in u.roles]
    if users_with_role:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除角色：仍有 {len(users_with_role)} 个用户使用此角色"
        )
    
    # 删除角色（从权限引擎中移除）
    if hasattr(permission_engine, 'roles'):
        permission_engine.roles.pop(role_name, None)
    
    return {"success": True, "message": f"角色 {role_name} 已删除"}


@router.get("/roles/{role_name}", response_model=Dict[str, Any])
async def get_role(
    role_name: str,
    current_user: User = Depends(get_current_user)
):
    """获取角色详情"""
    if not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    role = permission_engine.get_role(role_name)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    return {
        "name": role.name,
        "description": role.description,
        "permissions": [
            {
                "resource": p.resource,
                "action": p.action,
                "scope": p.scope
            }
            for p in role.permissions
        ]
    }


@router.put("/users/{user_id}", response_model=Dict[str, Any])
async def update_user(
    user_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """更新用户（需要管理员权限）"""
    if not user_storage or not auth_service or not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "user", "write"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 获取用户
    user = user_storage.get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新用户信息
    if "username" in request:
        # 检查新用户名是否已存在
        existing_user = user_storage.get_user(username=request["username"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = request["username"]
    
    if "email" in request:
        # 检查新邮箱是否已存在
        existing_user = user_storage.get_user(email=request["email"])
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = request["email"]
    
    if "password" in request and request["password"]:
        user.password_hash = auth_service.hash_password(request["password"])
    
    if "roles" in request:
        user.roles = request["roles"]
    
    if "is_active" in request:
        user.is_active = request["is_active"]
    
    if "is_superuser" in request:
        user.is_superuser = request["is_superuser"]
    
    user.updated_at = datetime.now()
    
    if not user_storage.update_user(user):
        raise HTTPException(status_code=500, detail="更新用户失败")
    
    return {"success": True, "user_id": user.id}


@router.delete("/users/{user_id}", response_model=Dict[str, Any])
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除用户（需要管理员权限）"""
    if not user_storage or not permission_engine:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 检查权限
    if not permission_engine.check_permission(current_user, "user", "delete"):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 不能删除自己
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    # 获取用户
    user = user_storage.get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 删除用户（标记为禁用）
    user.is_active = False
    user.updated_at = datetime.now()
    user_storage.update_user(user)
    
    return {"success": True, "message": f"用户 {user.username} 已禁用"}


@router.get("/tokens", response_model=Dict[str, Any])
async def list_api_tokens(
    current_user: User = Depends(get_current_user)
):
    """列出当前用户的API Token"""
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 获取用户的所有Token
    all_tokens = user_storage.list_api_tokens(user_id=current_user.id)
    
    return {
        "tokens": [
            {
                "id": t.id,
                "name": t.name,
                "permissions": [
                    {
                        "resource": p.resource,
                        "action": p.action,
                        "scope": p.scope
                    }
                    for p in t.permissions
                ],
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                "created_at": t.created_at.isoformat(),
                "is_active": t.is_active
            }
            for t in all_tokens
        ],
        "count": len(all_tokens)
    }


@router.delete("/tokens/{token_id}", response_model=Dict[str, Any])
async def delete_api_token(
    token_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除API Token"""
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 获取Token
    token = user_storage.get_api_token(token_id=token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Token不存在")
    
    # 检查权限（只能删除自己的Token）
    if token.user_id != current_user.id:
        if not permission_engine or not permission_engine.check_permission(current_user, "token", "delete"):
            raise HTTPException(status_code=403, detail="权限不足")
    
    # 删除Token（标记为禁用）
    token.is_active = False
    user_storage.update_api_token(token)
    
    return {"success": True, "message": "Token已删除"}

