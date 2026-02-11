"""
用户、权限、团队、空间的存储层
"""
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json

from .auth import User, Team, Space, APIToken, Role, Permission
from .collaboration import Comment, Annotation, Approval, ApprovalStatus, ApprovalLevel


class UserStorage:
    """用户存储"""
    
    def __init__(self, database_path: str):
        """
        初始化用户存储
        
        Args:
            database_path: 数据库文件路径
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.database_path), check_same_thread=False)
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库模式"""
        cursor = self.conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                roles TEXT NOT NULL DEFAULT '[]',
                teams TEXT NOT NULL DEFAULT '[]',
                spaces TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                is_superuser INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login TEXT,
                auth_provider TEXT NOT NULL DEFAULT 'builtin',
                auth_provider_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # 团队表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                members TEXT NOT NULL DEFAULT '[]',
                spaces TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # 工作空间表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                team_id TEXT,
                owner_id TEXT NOT NULL,
                members TEXT NOT NULL DEFAULT '[]',
                is_public INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # API Token表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                permissions TEXT NOT NULL DEFAULT '[]',
                expires_at TEXT,
                last_used_at TEXT,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 评论表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_id TEXT,
                version INTEGER,
                mentions TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 标注表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                note TEXT NOT NULL,
                category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # 审批表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                change_type TEXT NOT NULL,
                change_data TEXT NOT NULL,
                requester_id TEXT NOT NULL,
                approver_id TEXT,
                level TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                comment TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                approved_at TEXT,
                FOREIGN KEY (requester_id) REFERENCES users(id),
                FOREIGN KEY (approver_id) REFERENCES users(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON api_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_tokens_token_hash ON api_tokens(token_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_entity_id ON comments(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_entity_id ON annotations(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_user_id ON annotations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_entity_id ON approvals(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status)")
        
        self.conn.commit()
    
    # 用户操作
    def create_user(self, user: User) -> bool:
        """创建用户"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, roles, teams, spaces,
                                 is_active, is_superuser, created_at, updated_at, last_login,
                                 auth_provider, auth_provider_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id, user.username, user.email, user.password_hash,
                json.dumps(user.roles), json.dumps(user.teams), json.dumps(user.spaces),
                1 if user.is_active else 0, 1 if user.is_superuser else 0,
                user.created_at.isoformat(), user.updated_at.isoformat(),
                user.last_login.isoformat() if user.last_login else None,
                user.auth_provider, user.auth_provider_id,
                json.dumps(user.metadata)
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user(self, user_id: Optional[str] = None, username: Optional[str] = None, 
                 email: Optional[str] = None) -> Optional[User]:
        """获取用户"""
        cursor = self.conn.cursor()
        
        if user_id:
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        elif username:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        elif email:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        else:
            return None
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return self._row_to_user(row)
    
    def update_user(self, user: User) -> bool:
        """更新用户"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET
                    username = ?, email = ?, password_hash = ?, roles = ?, teams = ?,
                    spaces = ?, is_active = ?, is_superuser = ?, updated_at = ?,
                    last_login = ?, auth_provider = ?, auth_provider_id = ?, metadata = ?
                WHERE id = ?
            """, (
                user.username, user.email, user.password_hash,
                json.dumps(user.roles), json.dumps(user.teams), json.dumps(user.spaces),
                1 if user.is_active else 0, 1 if user.is_superuser else 0,
                user.updated_at.isoformat(),
                user.last_login.isoformat() if user.last_login else None,
                user.auth_provider, user.auth_provider_id,
                json.dumps(user.metadata),
                user.id
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False
    
    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """列出用户"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, offset))
        rows = cursor.fetchall()
        return [self._row_to_user(row) for row in rows]
    
    def _row_to_user(self, row) -> User:
        """将数据库行转换为User对象"""
        return User(
            id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            roles=json.loads(row[4]),
            teams=json.loads(row[5]),
            spaces=json.loads(row[6]),
            is_active=bool(row[7]),
            is_superuser=bool(row[8]),
            created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
            last_login=datetime.fromisoformat(row[11]) if row[11] else None,
            auth_provider=row[12],
            auth_provider_id=row[13],
            metadata=json.loads(row[14])
        )
    
    # 团队操作
    def create_team(self, team: Team) -> bool:
        """创建团队"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO teams (id, name, description, members, spaces, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team.id, team.name, team.description,
                json.dumps(team.members), json.dumps(team.spaces),
                team.created_at.isoformat(), team.updated_at.isoformat(),
                json.dumps(team.metadata)
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """获取团队"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Team(
            id=row[0],
            name=row[1],
            description=row[2],
            members=json.loads(row[3]),
            spaces=json.loads(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            metadata=json.loads(row[7])
        )
    
    def list_teams(self, limit: int = 100) -> List[Team]:
        """列出团队"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM teams LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [Team(
            id=row[0], name=row[1], description=row[2],
            members=json.loads(row[3]), spaces=json.loads(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            metadata=json.loads(row[7])
        ) for row in rows]
    
    # 工作空间操作
    def create_space(self, space: Space) -> bool:
        """创建工作空间"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO spaces (id, name, description, team_id, owner_id, members,
                                  is_public, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                space.id, space.name, space.description, space.team_id, space.owner_id,
                json.dumps(space.members), 1 if space.is_public else 0,
                space.created_at.isoformat(), space.updated_at.isoformat(),
                json.dumps(space.metadata)
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_space(self, space_id: str) -> Optional[Space]:
        """获取工作空间"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM spaces WHERE id = ?", (space_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Space(
            id=row[0], name=row[1], description=row[2], team_id=row[3],
            owner_id=row[4], members=json.loads(row[5]),
            is_public=bool(row[6]), created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]), metadata=json.loads(row[9])
        )
    
    # API Token操作
    def create_api_token(self, token: APIToken) -> bool:
        """创建API Token"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO api_tokens (id, user_id, token_hash, name, permissions,
                                      expires_at, last_used_at, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token.id, token.user_id, token.token_hash, token.name,
                json.dumps([p.dict() for p in token.permissions]),
                token.expires_at.isoformat() if token.expires_at else None,
                token.last_used_at.isoformat() if token.last_used_at else None,
                token.created_at.isoformat(), 1 if token.is_active else 0
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_api_token_by_hash(self, token_hash: str) -> Optional[APIToken]:
        """通过哈希获取API Token"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE token_hash = ? AND is_active = 1", (token_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        
        expires_at = datetime.fromisoformat(row[5]) if row[5] else None
        if expires_at and expires_at < datetime.now():
            return None  # Token已过期
        
        return APIToken(
            id=row[0], user_id=row[1], token_hash=row[2], name=row[3],
            permissions=[Permission(**p) for p in json.loads(row[4])],
            expires_at=expires_at,
            last_used_at=datetime.fromisoformat(row[6]) if row[6] else None,
            created_at=datetime.fromisoformat(row[7]),
            is_active=bool(row[8])
        )
    
    # 评论操作
    def create_comment(self, comment: Comment) -> bool:
        """创建评论"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO comments (id, entity_id, user_id, content, parent_id, version,
                                    mentions, created_at, updated_at, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment.id, comment.entity_id, comment.user_id, comment.content,
                comment.parent_id, comment.version, json.dumps(comment.mentions),
                comment.created_at.isoformat(), comment.updated_at.isoformat(),
                1 if comment.is_deleted else 0
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_comments(self, entity_id: str, version: Optional[int] = None) -> List[Comment]:
        """获取评论列表"""
        cursor = self.conn.cursor()
        if version is not None:
            cursor.execute("""
                SELECT * FROM comments WHERE entity_id = ? AND version = ? AND is_deleted = 0
                ORDER BY created_at ASC
            """, (entity_id, version))
        else:
            cursor.execute("""
                SELECT * FROM comments WHERE entity_id = ? AND is_deleted = 0
                ORDER BY created_at ASC
            """, (entity_id,))
        
        rows = cursor.fetchall()
        return [Comment(
            id=row[0], entity_id=row[1], user_id=row[2], content=row[3],
            parent_id=row[4], version=row[5], mentions=json.loads(row[6]),
            created_at=datetime.fromisoformat(row[7]), updated_at=datetime.fromisoformat(row[8]),
            is_deleted=bool(row[9])
        ) for row in rows]
    
    # 标注操作
    def create_annotation(self, annotation: Annotation) -> bool:
        """创建标注"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO annotations (id, entity_id, user_id, tag, note, category,
                                        created_at, updated_at, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                annotation.id, annotation.entity_id, annotation.user_id,
                annotation.tag, annotation.note, annotation.category,
                annotation.created_at.isoformat(), annotation.updated_at.isoformat(),
                1 if annotation.is_deleted else 0
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_annotations(self, entity_id: str) -> List[Annotation]:
        """获取标注列表"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM annotations WHERE entity_id = ? AND is_deleted = 0
            ORDER BY created_at ASC
        """, (entity_id,))
        rows = cursor.fetchall()
        return [Annotation(
            id=row[0], entity_id=row[1], user_id=row[2], tag=row[3], note=row[4],
            category=row[5], created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]), is_deleted=bool(row[8])
        ) for row in rows]
    
    # 审批操作
    def create_approval(self, approval: Approval) -> bool:
        """创建审批"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO approvals (id, entity_id, change_type, change_data, requester_id,
                                     approver_id, level, status, comment, created_at, updated_at, approved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                approval.id, approval.entity_id, approval.change_type,
                json.dumps(approval.change_data), approval.requester_id,
                approval.approver_id, approval.level.value, approval.status.value,
                approval.comment, approval.created_at.isoformat(),
                approval.updated_at.isoformat(),
                approval.approved_at.isoformat() if approval.approved_at else None
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_approvals(self, entity_id: Optional[str] = None, status: Optional[str] = None) -> List[Approval]:
        """获取审批列表"""
        cursor = self.conn.cursor()
        if entity_id and status:
            cursor.execute("""
                SELECT * FROM approvals WHERE entity_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (entity_id, status))
        elif entity_id:
            cursor.execute("SELECT * FROM approvals WHERE entity_id = ? ORDER BY created_at DESC", (entity_id,))
        elif status:
            cursor.execute("SELECT * FROM approvals WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM approvals ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        return [Approval(
            id=row[0], entity_id=row[1], change_type=row[2],
            change_data=json.loads(row[3]), requester_id=row[4],
            approver_id=row[5], level=ApprovalLevel(row[6]), status=ApprovalStatus(row[7]),
            comment=row[8], created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
            approved_at=datetime.fromisoformat(row[11]) if row[11] else None
        ) for row in rows]
    
    def update_approval(self, approval: Approval) -> bool:
        """更新审批"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE approvals SET
                    approver_id = ?, status = ?, comment = ?, updated_at = ?, approved_at = ?
                WHERE id = ?
            """, (
                approval.approver_id,
                approval.status.value,
                approval.comment,
                approval.updated_at.isoformat(),
                approval.approved_at.isoformat() if approval.approved_at else None,
                approval.id
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
    
    def list_api_tokens(self, user_id: Optional[str] = None) -> List[APIToken]:
        """列出API Token"""
        cursor = self.conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM api_tokens ORDER BY created_at DESC")
        
        rows = cursor.fetchall()
        tokens = []
        for row in rows:
            expires_at = datetime.fromisoformat(row[5]) if row[5] else None
            if expires_at and expires_at < datetime.now():
                continue  # 跳过已过期的Token
            
            tokens.append(APIToken(
                id=row[0], user_id=row[1], token_hash=row[2], name=row[3],
                permissions=[Permission(**p) for p in json.loads(row[4])],
                expires_at=expires_at,
                last_used_at=datetime.fromisoformat(row[6]) if row[6] else None,
                created_at=datetime.fromisoformat(row[7]),
                is_active=bool(row[8])
            ))
        return tokens
    
    def get_api_token(self, token_id: str) -> Optional[APIToken]:
        """获取API Token"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE id = ?", (token_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        expires_at = datetime.fromisoformat(row[5]) if row[5] else None
        return APIToken(
            id=row[0], user_id=row[1], token_hash=row[2], name=row[3],
            permissions=[Permission(**p) for p in json.loads(row[4])],
            expires_at=expires_at,
            last_used_at=datetime.fromisoformat(row[6]) if row[6] else None,
            created_at=datetime.fromisoformat(row[7]),
            is_active=bool(row[8])
        )
    
    def update_api_token(self, token: APIToken) -> bool:
        """更新API Token"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE api_tokens SET
                    name = ?, permissions = ?, expires_at = ?,
                    last_used_at = ?, is_active = ?
                WHERE id = ?
            """, (
                token.name,
                json.dumps([p.dict() for p in token.permissions]),
                token.expires_at.isoformat() if token.expires_at else None,
                token.last_used_at.isoformat() if token.last_used_at else None,
                1 if token.is_active else 0,
                token.id
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
    
    def close(self):
        """关闭连接"""
        self.conn.close()

