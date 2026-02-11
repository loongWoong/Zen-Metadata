"""
SQLite 关系型数据处理
"""
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

from ..core.models import MetadataEntity, MetadataRelationship


class SQLiteProcessor:
    """SQLite 数据处理器"""
    
    def __init__(self, database_path: str):
        """
        初始化 SQLite 处理器
        
        Args:
            database_path: 数据库文件路径
        """
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.database_path))
        self._init_schema()
    
    def _init_schema(self):
        """初始化数据库模式"""
        cursor = self.conn.cursor()
        
        # 创建实体表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                properties TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 创建关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
        """)
        
        # 创建质量评分表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                completeness_score REAL NOT NULL,
                accuracy_score REAL NOT NULL,
                consistency_score REAL NOT NULL,
                freshness_score REAL NOT NULL,
                overall_score REAL NOT NULL,
                quality_level TEXT NOT NULL,
                completeness_details TEXT,
                accuracy_details TEXT,
                consistency_details TEXT,
                freshness_details TEXT,
                assessed_at TEXT NOT NULL,
                assessed_by TEXT,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        """)
        
        # 创建标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                color TEXT DEFAULT '#808080',
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT
            )
        """)
        
        # 创建实体标签关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_tags (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                user_id TEXT,
                confidence REAL DEFAULT 1.0,
                is_auto INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id)
            )
        """)
        
        # 创建数据标准表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_standards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                entity_type TEXT,
                rule TEXT NOT NULL,
                description TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by TEXT
            )
        """)
        
        # 创建标准违规表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS standard_violations (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                standard_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                fix_suggestion TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL,
                fixed_at TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                FOREIGN KEY (standard_id) REFERENCES data_standards(id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_scores_entity_id ON quality_scores(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_scores_entity_type ON quality_scores(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_scores_assessed_at ON quality_scores(assessed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_tags_entity_id ON entity_tags(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_tags_tag_id ON entity_tags(tag_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_standards_type ON data_standards(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_standards_entity_type ON data_standards(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_standard_violations_entity_id ON standard_violations(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_standard_violations_standard_id ON standard_violations(standard_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_standard_violations_status ON standard_violations(status)")
        
        self.conn.commit()
    
    def store_entity(self, entity: MetadataEntity) -> bool:
        """
        存储实体
        
        Args:
            entity: 元数据实体
            
        Returns:
            是否成功
        """
        try:
            import json
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO entities 
                (id, type, name, description, source, properties, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.type,
                entity.name,
                entity.description,
                entity.source,
                json.dumps(entity.properties),
                entity.created_at.isoformat(),
                entity.updated_at.isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"存储实体失败: {e}")
            return False
    
    def store_relationship(self, relationship: MetadataRelationship, incremental: bool = False) -> bool:
        """
        存储关系
        
        Args:
            relationship: 元数据关系
            incremental: 是否为增量模式（True=更新已存在的关系，False=直接插入）
            
        Returns:
            是否成功
        """
        try:
            import json
            cursor = self.conn.cursor()
            
            if incremental:
                # 增量模式：先检查是否存在相同的关系，如果存在则更新，不存在则插入
                # 由于relationships表没有唯一约束，我们查找最新的相同关系并更新
                cursor.execute("""
                    SELECT id FROM relationships 
                    WHERE source_id = ? AND target_id = ? AND type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (
                    relationship.source_id,
                    relationship.target_id,
                    relationship.type
                ))
                existing = cursor.fetchone()
                
                if existing:
                    # 更新已存在的关系
                    cursor.execute("""
                        UPDATE relationships 
                        SET properties = ?, created_at = ?
                        WHERE id = ?
                    """, (
                        json.dumps(relationship.properties),
                        relationship.created_at.isoformat(),
                        existing[0]
                    ))
                else:
                    # 插入新关系
                    cursor.execute("""
                        INSERT INTO relationships 
                        (source_id, target_id, type, properties, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        relationship.source_id,
                        relationship.target_id,
                        relationship.type,
                        json.dumps(relationship.properties),
                        relationship.created_at.isoformat()
                    ))
            else:
                # 非增量模式：直接插入
                cursor.execute("""
                    INSERT INTO relationships 
                    (source_id, target_id, type, properties, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    relationship.source_id,
                    relationship.target_id,
                    relationship.type,
                    json.dumps(relationship.properties),
                    relationship.created_at.isoformat()
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"存储关系失败: {e}")
            return False
    
    def query_entities(self, 
                      entity_type: Optional[str] = None,
                      source: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询实体
        
        Args:
            entity_type: 实体类型过滤
            source: 数据源过滤
            limit: 限制数量
            
        Returns:
            实体列表
        """
        import json
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM entities WHERE 1=1"
        params = []
        
        if entity_type:
            query += " AND type = ?"
            params.append(entity_type)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            if result.get('properties'):
                result['properties'] = json.loads(result['properties'])
            results.append(result)
        
        return results
    
    def query_relationships(self,
                           source_id: Optional[str] = None,
                           target_id: Optional[str] = None,
                           relationship_type: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询关系
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relationship_type: 关系类型
            limit: 限制数量
            
        Returns:
            关系列表
        """
        import json
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM relationships WHERE 1=1"
        params = []
        
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        
        if relationship_type:
            query += " AND type = ?"
            params.append(relationship_type)
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            if result.get('properties'):
                result['properties'] = json.loads(result['properties'])
            results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM relationships")
        relationship_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT type) FROM entities")
        entity_type_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT source) FROM entities")
        source_count = cursor.fetchone()[0]
        
        return {
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "entity_type_count": entity_type_count,
            "source_count": source_count
        }
    
    def to_dataframe(self, query: str) -> pd.DataFrame:
        """
        执行查询并返回 DataFrame
        
        Args:
            query: SQL 查询语句
            
        Returns:
            DataFrame
        """
        return pd.read_sql_query(query, self.conn)
    
    def store_quality_score(self, score: Dict[str, Any]) -> bool:
        """
        存储质量评分
        
        Args:
            score: 质量评分字典（来自 MetadataQualityScore.to_dict()）
            
        Returns:
            是否成功
        """
        try:
            import json
            from datetime import datetime
            
            cursor = self.conn.cursor()
            
            # 将详情字典转换为JSON字符串
            completeness_details = json.dumps(score.get('completeness_details', {}))
            accuracy_details = json.dumps(score.get('accuracy_details', {}))
            consistency_details = json.dumps(score.get('consistency_details', {}))
            freshness_details = json.dumps(score.get('freshness_details', {}))
            
            cursor.execute("""
                INSERT INTO quality_scores 
                (entity_id, entity_type, completeness_score, accuracy_score, 
                 consistency_score, freshness_score, overall_score, quality_level,
                 completeness_details, accuracy_details, consistency_details, freshness_details,
                 assessed_at, assessed_by, version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.get('entity_id'),
                score.get('entity_type'),
                score.get('completeness_score', 0.0),
                score.get('accuracy_score', 0.0),
                score.get('consistency_score', 0.0),
                score.get('freshness_score', 0.0),
                score.get('overall_score', 0.0),
                score.get('quality_level', 'unknown'),
                completeness_details,
                accuracy_details,
                consistency_details,
                freshness_details,
                score.get('assessed_at'),
                score.get('assessed_by', 'quality_assessor'),
                score.get('version', 1),
                datetime.now().isoformat()
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"存储质量评分失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def query_quality_scores(self,
                           entity_id: Optional[str] = None,
                           entity_type: Optional[str] = None,
                           limit: int = 100,
                           offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """
        查询质量评分
        
        Args:
            entity_id: 实体ID过滤
            entity_type: 实体类型过滤
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            (质量评分列表, 总数)
        """
        import json
        cursor = self.conn.cursor()
        
        query = """
            SELECT entity_id, entity_type, completeness_score, accuracy_score,
                   consistency_score, freshness_score, overall_score, quality_level,
                   completeness_details, accuracy_details, consistency_details, freshness_details,
                   assessed_at, assessed_by, version
            FROM quality_scores
            WHERE 1=1
        """
        params = []
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        # 按评估时间倒序排列，获取最新的评分
        query += " ORDER BY assessed_at DESC"
        
        # 先获取总数
        count_query = query.replace(
            "SELECT entity_id, entity_type, completeness_score, accuracy_score," +
            " consistency_score, freshness_score, overall_score, quality_level," +
            " completeness_details, accuracy_details, consistency_details, freshness_details," +
            " assessed_at, assessed_by, version",
            "SELECT COUNT(*)"
        )
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            # 解析详情JSON字符串
            if result.get('completeness_details'):
                result['completeness_details'] = json.loads(result['completeness_details'])
            if result.get('accuracy_details'):
                result['accuracy_details'] = json.loads(result['accuracy_details'])
            if result.get('consistency_details'):
                result['consistency_details'] = json.loads(result['consistency_details'])
            if result.get('freshness_details'):
                result['freshness_details'] = json.loads(result['freshness_details'])
            results.append(result)
        
        return results, total
    
    def get_latest_quality_scores(self,
                                 entity_ids: Optional[List[str]] = None,
                                 entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取最新的质量评分（每个实体只返回最新的评分）
        
        Args:
            entity_ids: 实体ID列表（可选）
            entity_type: 实体类型过滤（可选）
            
        Returns:
            质量评分列表
        """
        import json
        cursor = self.conn.cursor()
        
        if entity_ids:
            # 为每个实体ID获取最新的评分
            placeholders = ','.join(['?'] * len(entity_ids))
            query = f"""
                SELECT entity_id, entity_type, completeness_score, accuracy_score,
                       consistency_score, freshness_score, overall_score, quality_level,
                       completeness_details, accuracy_details, consistency_details, freshness_details,
                       assessed_at, assessed_by, version
                FROM quality_scores qs1
                WHERE qs1.entity_id IN ({placeholders})
                  AND qs1.assessed_at = (
                      SELECT MAX(qs2.assessed_at)
                      FROM quality_scores qs2
                      WHERE qs2.entity_id = qs1.entity_id
                  )
            """
            params = entity_ids
        else:
            # 获取所有实体的最新评分
            query = """
                SELECT qs1.entity_id, qs1.entity_type, qs1.completeness_score, qs1.accuracy_score,
                       qs1.consistency_score, qs1.freshness_score, qs1.overall_score, qs1.quality_level,
                       qs1.completeness_details, qs1.accuracy_details, qs1.consistency_details, qs1.freshness_details,
                       qs1.assessed_at, qs1.assessed_by, qs1.version
                FROM quality_scores qs1
                WHERE qs1.assessed_at = (
                    SELECT MAX(qs2.assessed_at)
                    FROM quality_scores qs2
                    WHERE qs2.entity_id = qs1.entity_id
                )
            """
            params = []
        
        if entity_type:
            query += " AND qs1.entity_type = ?"
            params.append(entity_type)
        
        query += " ORDER BY qs1.assessed_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            # 解析详情JSON字符串
            if result.get('completeness_details'):
                result['completeness_details'] = json.loads(result['completeness_details'])
            if result.get('accuracy_details'):
                result['accuracy_details'] = json.loads(result['accuracy_details'])
            if result.get('consistency_details'):
                result['consistency_details'] = json.loads(result['consistency_details'])
            if result.get('freshness_details'):
                result['freshness_details'] = json.loads(result['freshness_details'])
            results.append(result)
        
        return results
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()



