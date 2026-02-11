"""
版本控制与审计系统
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
from pathlib import Path

from .models import MetadataEntity, MetadataRelationship


class OperationType(str, Enum):
    """操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class MetadataVersion:
    """元数据版本"""
    entity_id: str
    version: int
    metamodel_version: Optional[str] = None
    snapshot: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    change_reason: Optional[str] = None


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    entity_id: str
    operation_type: OperationType
    operator: Optional[str] = None
    changed_fields: List[str] = field(default_factory=list)
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetadataVersionControl:
    """元数据版本控制"""
    
    def __init__(self, database_path: str = "data/zen_metadata_versions.db"):
        """
        初始化版本控制系统
        
        Args:
            database_path: 版本数据库路径
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.database_path))
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库模式"""
        cursor = self.conn.cursor()
        
        # 版本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                metamodel_version TEXT,
                snapshot TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT,
                change_reason TEXT,
                UNIQUE(entity_id, version)
            )
        """)
        
        # 审计事件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                operator TEXT,
                changed_fields TEXT,
                old_value TEXT,
                new_value TEXT,
                change_reason TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_entity ON entity_versions(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_created ON entity_versions(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_operation ON audit_events(operation_type)")
        
        self.conn.commit()
    
    def create_version(self, entity: MetadataEntity,
                      created_by: Optional[str] = None,
                      change_reason: Optional[str] = None,
                      metamodel_version: Optional[str] = None) -> MetadataVersion:
        """
        创建实体版本
        
        Args:
            entity: 元数据实体
            created_by: 创建者
            change_reason: 变更原因
            metamodel_version: 元模型版本
            
        Returns:
            创建的版本对象
        """
        # 获取当前版本号
        current_version = self.get_current_version(entity.id)
        new_version = current_version + 1
        
        # 创建快照
        snapshot = {
            "id": entity.id,
            "type": entity.type,
            "name": entity.name,
            "description": entity.description,
            "properties": entity.properties,
            "source": entity.source,
            "created_at": entity.created_at.isoformat() if isinstance(entity.created_at, datetime) else str(entity.created_at),
            "updated_at": entity.updated_at.isoformat() if isinstance(entity.updated_at, datetime) else str(entity.updated_at)
        }
        
        # 保存版本
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO entity_versions 
            (entity_id, version, metamodel_version, snapshot, created_at, created_by, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.id,
            new_version,
            metamodel_version,
            json.dumps(snapshot, ensure_ascii=False),
            datetime.now().isoformat(),
            created_by,
            change_reason
        ))
        
        self.conn.commit()
        
        return MetadataVersion(
            entity_id=entity.id,
            version=new_version,
            metamodel_version=metamodel_version,
            snapshot=snapshot,
            created_at=datetime.now(),
            created_by=created_by,
            change_reason=change_reason
        )
    
    def get_version(self, entity_id: str, version: int) -> Optional[MetadataVersion]:
        """
        获取指定版本
        
        Args:
            entity_id: 实体ID
            version: 版本号
            
        Returns:
            版本对象或None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT entity_id, version, metamodel_version, snapshot, created_at, created_by, change_reason
            FROM entity_versions
            WHERE entity_id = ? AND version = ?
        """, (entity_id, version))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return MetadataVersion(
            entity_id=row[0],
            version=row[1],
            metamodel_version=row[2],
            snapshot=json.loads(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            created_by=row[5],
            change_reason=row[6]
        )
    
    def get_current_version(self, entity_id: str) -> int:
        """
        获取当前版本号
        
        Args:
            entity_id: 实体ID
            
        Returns:
            当前版本号（如果没有版本则返回0）
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT MAX(version) FROM entity_versions WHERE entity_id = ?
        """, (entity_id,))
        
        row = cursor.fetchone()
        return row[0] if row[0] else 0
    
    def list_versions(self, entity_id: str) -> List[MetadataVersion]:
        """
        列出实体的所有版本
        
        Args:
            entity_id: 实体ID
            
        Returns:
            版本列表
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT entity_id, version, metamodel_version, snapshot, created_at, created_by, change_reason
            FROM entity_versions
            WHERE entity_id = ?
            ORDER BY version DESC
        """, (entity_id,))
        
        versions = []
        for row in cursor.fetchall():
            versions.append(MetadataVersion(
                entity_id=row[0],
                version=row[1],
                metamodel_version=row[2],
                snapshot=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                created_by=row[5],
                change_reason=row[6]
            ))
        
        return versions
    
    def diff_versions(self, entity_id: str, version1: int, version2: int) -> Dict[str, Any]:
        """
        对比两个版本
        
        Args:
            entity_id: 实体ID
            version1: 版本1
            version2: 版本2
            
        Returns:
            差异信息
        """
        v1 = self.get_version(entity_id, version1)
        v2 = self.get_version(entity_id, version2)
        
        if not v1 or not v2:
            return {"error": "版本不存在"}
        
        diff = {
            "entity_id": entity_id,
            "version1": version1,
            "version2": version2,
            "changes": {}
        }
        
        # 对比快照
        snapshot1 = v1.snapshot
        snapshot2 = v2.snapshot
        
        all_keys = set(snapshot1.keys()) | set(snapshot2.keys())
        
        for key in all_keys:
            val1 = snapshot1.get(key)
            val2 = snapshot2.get(key)
            
            if val1 != val2:
                diff["changes"][key] = {
                    "old": val1,
                    "new": val2
                }
        
        return diff
    
    def rollback(self, entity_id: str, target_version: int) -> bool:
        """
        回滚到指定版本
        
        Args:
            entity_id: 实体ID
            target_version: 目标版本号
            
        Returns:
            是否成功
        """
        target = self.get_version(entity_id, target_version)
        if not target:
            return False
        
        # 创建新版本（回滚版本）
        cursor = self.conn.cursor()
        current_version = self.get_current_version(entity_id)
        new_version = current_version + 1
        
        cursor.execute("""
            INSERT INTO entity_versions 
            (entity_id, version, metamodel_version, snapshot, created_at, created_by, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_id,
            new_version,
            target.metamodel_version,
            json.dumps(target.snapshot, ensure_ascii=False),
            datetime.now().isoformat(),
            None,
            f"回滚到版本 {target_version}"
        ))
        
        self.conn.commit()
        return True
    
    def record_audit_event(self, event: AuditEvent) -> bool:
        """
        记录审计事件
        
        Args:
            event: 审计事件
            
        Returns:
            是否成功
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_events 
            (event_id, entity_id, operation_type, operator, changed_fields, 
             old_value, new_value, change_reason, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.entity_id,
            event.operation_type.value,
            event.operator,
            json.dumps(event.changed_fields, ensure_ascii=False),
            json.dumps(event.old_value, ensure_ascii=False) if event.old_value else None,
            json.dumps(event.new_value, ensure_ascii=False) if event.new_value else None,
            event.change_reason,
            event.timestamp.isoformat(),
            json.dumps(event.metadata, ensure_ascii=False)
        ))
        
        self.conn.commit()
        return True
    
    def get_audit_events(self,
                        entity_id: Optional[str] = None,
                        operation_type: Optional[OperationType] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        limit: int = 100) -> List[AuditEvent]:
        """
        查询审计事件
        
        Args:
            entity_id: 实体ID过滤
            operation_type: 操作类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 结果数量限制
            
        Returns:
            审计事件列表
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        if operation_type:
            query += " AND operation_type = ?"
            params.append(operation_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            events.append(AuditEvent(
                event_id=row[0],
                entity_id=row[1],
                operation_type=OperationType(row[2]),
                operator=row[3],
                changed_fields=json.loads(row[4]) if row[4] else [],
                old_value=json.loads(row[5]) if row[5] else None,
                new_value=json.loads(row[6]) if row[6] else None,
                change_reason=row[7],
                timestamp=datetime.fromisoformat(row[8]),
                metadata=json.loads(row[9]) if row[9] else {}
            ))
        
        return events
    
    def get_audit_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        获取审计统计信息
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息
        """
        cursor = self.conn.cursor()
        
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = start_time.replace(day=start_time.day - days)
        
        # 总事件数
        cursor.execute("""
            SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?
        """, (start_time.isoformat(),))
        total_events = cursor.fetchone()[0]
        
        # 操作类型分布
        cursor.execute("""
            SELECT operation_type, COUNT(*) as count
            FROM audit_events
            WHERE timestamp >= ?
            GROUP BY operation_type
        """, (start_time.isoformat(),))
        
        operation_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 操作者分布
        cursor.execute("""
            SELECT operator, COUNT(*) as count
            FROM audit_events
            WHERE timestamp >= ? AND operator IS NOT NULL
            GROUP BY operator
            ORDER BY count DESC
            LIMIT 10
        """, (start_time.isoformat(),))
        
        operator_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_events": total_events,
            "period_days": days,
            "operation_distribution": operation_distribution,
            "operator_distribution": operator_distribution,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()



