"""
用户认证与授权核心模块
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import hashlib
import secrets
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
import bcrypt

# 直接使用 bcrypt，避免 passlib 的初始化问题


class Permission(BaseModel):
    """权限定义"""
    resource: str = Field(..., description="资源类型: entity, relationship, collector, job, version")
    action: str = Field(..., description="操作类型: read, write, delete, execute, approve")
    scope: str = Field(..., description="范围: all, team, own")


class Role(BaseModel):
    """角色"""
    name: str = Field(..., description="角色名称")
    permissions: List[Permission] = Field(default_factory=list, description="权限列表")
    description: Optional[str] = Field(None, description="角色描述")


class User(BaseModel):
    """用户模型"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    password_hash: Optional[str] = Field(None, description="密码哈希（仅用于内建认证）")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    teams: List[str] = Field(default_factory=list, description="团队列表")
    spaces: List[str] = Field(default_factory=list, description="工作空间列表")
    is_active: bool = Field(True, description="是否激活")
    is_superuser: bool = Field(False, description="是否超级用户")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    auth_provider: str = Field("builtin", description="认证提供者: builtin, oauth2, ldap")
    auth_provider_id: Optional[str] = Field(None, description="认证提供者ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class Team(BaseModel):
    """团队模型"""
    id: str = Field(..., description="团队ID")
    name: str = Field(..., description="团队名称")
    description: Optional[str] = Field(None, description="团队描述")
    members: List[str] = Field(default_factory=list, description="成员用户ID列表")
    spaces: List[str] = Field(default_factory=list, description="工作空间列表")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Space(BaseModel):
    """工作空间模型"""
    id: str = Field(..., description="空间ID")
    name: str = Field(..., description="空间名称")
    description: Optional[str] = Field(None, description="空间描述")
    team_id: Optional[str] = Field(None, description="所属团队ID")
    owner_id: str = Field(..., description="所有者用户ID")
    members: List[str] = Field(default_factory=list, description="成员用户ID列表")
    is_public: bool = Field(False, description="是否公开")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class APIToken(BaseModel):
    """API Token模型"""
    id: str = Field(..., description="Token ID")
    user_id: str = Field(..., description="用户ID")
    token_hash: str = Field(..., description="Token哈希值")
    name: str = Field(..., description="Token名称")
    permissions: List[Permission] = Field(default_factory=list, description="绑定权限")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True, description="是否激活")


class AuthService:
    """认证服务"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", access_token_expire_minutes: int = 30):
        """
        初始化认证服务
        
        Args:
            secret_key: JWT密钥
            algorithm: JWT算法
            access_token_expire_minutes: Access Token过期时间（分钟）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        # bcrypt 限制密码长度不能超过72字节
        # 如果密码超过72字节，先进行SHA256哈希再bcrypt
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # 先进行SHA256哈希，得到固定长度的字符串（64个字符）
            password = hashlib.sha256(password_bytes).hexdigest()
            password_bytes = password.encode('utf-8')
        
        # 确保不超过72字节
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # 使用 bcrypt 直接哈希
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        # 如果原始密码超过72字节，需要先进行SHA256哈希
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            # 先进行SHA256哈希，得到固定长度的字符串（64个字符）
            plain_password = hashlib.sha256(password_bytes).hexdigest()
            password_bytes = plain_password.encode('utf-8')
        
        # 确保不超过72字节
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # 使用 bcrypt 验证
        try:
            return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
        except Exception as e:
            print(f"[AUTH] 密码验证异常: {type(e).__name__} - {str(e)}")
            return False
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码访问令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            return None
        except JWTError:
            return None
    
    def generate_api_token(self) -> str:
        """生成API Token"""
        return secrets.token_urlsafe(32)
    
    def hash_token(self, token: str) -> str:
        """哈希Token"""
        return hashlib.sha256(token.encode()).hexdigest()


class PermissionEngine:
    """权限引擎（RBAC + ABAC）"""
    
    def __init__(self):
        """初始化权限引擎"""
        self.roles: Dict[str, Role] = {}
        self._init_default_roles()
    
    def _init_default_roles(self):
        """初始化默认角色"""
        # 管理员角色
        admin_role = Role(
            name="admin",
            description="系统管理员",
            permissions=[
                Permission(resource="*", action="*", scope="all")
            ]
        )
        self.roles["admin"] = admin_role
        
        # 数据管理员角色
        data_admin_role = Role(
            name="data_admin",
            description="数据管理员",
            permissions=[
                Permission(resource="entity", action="*", scope="all"),
                Permission(resource="relationship", action="*", scope="all"),
                Permission(resource="collector", action="*", scope="all"),
                Permission(resource="job", action="*", scope="all"),
            ]
        )
        self.roles["data_admin"] = data_admin_role
        
        # 数据工程师角色
        data_engineer_role = Role(
            name="data_engineer",
            description="数据工程师",
            permissions=[
                Permission(resource="entity", action="read", scope="all"),
                Permission(resource="entity", action="write", scope="team"),
                Permission(resource="relationship", action="read", scope="all"),
                Permission(resource="relationship", action="write", scope="team"),
                Permission(resource="collector", action="read", scope="all"),
                Permission(resource="collector", action="execute", scope="team"),
                Permission(resource="job", action="read", scope="team"),
                Permission(resource="job", action="execute", scope="team"),
            ]
        )
        self.roles["data_engineer"] = data_engineer_role
        
        # 业务分析师角色
        analyst_role = Role(
            name="analyst",
            description="业务分析师",
            permissions=[
                Permission(resource="entity", action="read", scope="all"),
                Permission(resource="relationship", action="read", scope="all"),
            ]
        )
        self.roles["analyst"] = analyst_role
        
        # 只读用户角色
        viewer_role = Role(
            name="viewer",
            description="只读用户",
            permissions=[
                Permission(resource="entity", action="read", scope="all"),
                Permission(resource="relationship", action="read", scope="all"),
            ]
        )
        self.roles["viewer"] = viewer_role
    
    def check_permission(
        self,
        user: User,
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        resource_owner_id: Optional[str] = None,
        resource_team_id: Optional[str] = None,
        resource_space_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        检查权限（RBAC + ABAC混合）
        
        Args:
            user: 用户对象
            resource: 资源类型
            action: 操作类型
            resource_id: 资源ID（用于ABAC）
            resource_owner_id: 资源所有者ID（用于own scope）
            resource_team_id: 资源所属团队ID（用于team scope）
            resource_space_id: 资源所属空间ID（用于team scope）
            attributes: 资源属性（用于ABAC规则判断）
        
        Returns:
            是否有权限
        """
        # 超级用户拥有所有权限
        if user.is_superuser:
            return True
        
        # 检查用户的所有角色权限
        for role_name in user.roles:
            role = self.roles.get(role_name)
            if not role:
                continue
            
            for permission in role.permissions:
                # 检查资源匹配
                if permission.resource != "*" and permission.resource != resource:
                    continue
                
                # 检查操作匹配
                if permission.action != "*" and permission.action != action:
                    continue
                
                # 检查范围
                if permission.scope == "all":
                    return True
                elif permission.scope == "own":
                    if resource_owner_id and resource_owner_id == user.id:
                        return True
                elif permission.scope == "team":
                    # 检查用户是否在资源的团队中
                    if resource_team_id and resource_team_id in user.teams:
                        return True
                    if resource_space_id:
                        # 需要检查空间权限（这里简化处理）
                        if resource_space_id in user.spaces:
                            return True
                
                # ABAC规则判断（基于属性）
                if attributes and self._check_abac_rules(permission, attributes):
                    return True
        
        return False
    
    def _check_abac_rules(self, permission: Permission, attributes: Dict[str, Any]) -> bool:
        """
        检查ABAC规则
        
        例如：
        - 质量评分低于60的生产表，只允许只读访问
        - 包含PII标签的实体，需要特殊权限
        """
        # 这里可以实现更复杂的ABAC规则
        # 例如：检查质量评分、标签、系统来源等
        return False
    
    def add_role(self, role: Role):
        """添加角色"""
        self.roles[role.name] = role
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """获取角色"""
        return self.roles.get(role_name)
    
    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self.roles.values())


