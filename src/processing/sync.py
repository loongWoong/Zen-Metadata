"""
SQLite 到 DuckDB 数据同步
"""
from typing import Optional
import json
from datetime import datetime

from .sqlite import SQLiteProcessor
from .duckdb import DuckDBProcessor


class DataSync:
    """数据同步器"""
    
    def __init__(self, sqlite_processor: SQLiteProcessor, duckdb_processor: DuckDBProcessor):
        """
        初始化数据同步器
        
        Args:
            sqlite_processor: SQLite 处理器
            duckdb_processor: DuckDB 处理器
        """
        self.sqlite = sqlite_processor
        self.duckdb = duckdb_processor
    
    def sync_all(self) -> dict:
        """
        同步所有数据
        
        Returns:
            同步结果统计
        """
        stats = {
            "entities_synced": 0,
            "relationships_synced": 0,
            "errors": []
        }
        
        try:
            # 同步实体
            entities = self.sqlite.query_entities(limit=100000)
            for entity in entities:
                try:
                    # 转换日期字符串为 datetime
                    if isinstance(entity.get('created_at'), str):
                        entity['created_at'] = datetime.fromisoformat(entity['created_at'])
                    if isinstance(entity.get('updated_at'), str):
                        entity['updated_at'] = datetime.fromisoformat(entity['updated_at'])
                    
                    # 插入到 DuckDB (使用 ON CONFLICT 处理重复)
                    properties_str = json.dumps(entity.get('properties', {})) if entity.get('properties') else None
                    self.duckdb.conn.execute("""
                        INSERT INTO entities 
                        (id, type, name, description, source, properties, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                            type = EXCLUDED.type,
                            name = EXCLUDED.name,
                            description = EXCLUDED.description,
                            source = EXCLUDED.source,
                            properties = EXCLUDED.properties,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        entity.get('id'),
                        entity.get('type'),
                        entity.get('name'),
                        entity.get('description'),
                        entity.get('source'),
                        properties_str,
                        entity.get('created_at'),
                        entity.get('updated_at')
                    ))
                    stats["entities_synced"] += 1
                except Exception as e:
                    stats["errors"].append(f"同步实体 {entity.get('id')} 失败: {str(e)}")
            
            # 同步关系
            relationships = self.sqlite.query_relationships(limit=100000)
            for rel in relationships:
                try:
                    if isinstance(rel.get('created_at'), str):
                        rel['created_at'] = datetime.fromisoformat(rel['created_at'])
                    
                    properties_str = json.dumps(rel.get('properties', {})) if rel.get('properties') else None
                    # 对于关系，使用 SQLite 中的 id 值
                    # 如果 id 已存在则更新，否则插入
                    rel_id = rel.get('id')
                    if rel_id:
                        self.duckdb.conn.execute("""
                            INSERT INTO relationships 
                            (id, source_id, target_id, type, properties, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT (id) DO UPDATE SET
                                source_id = EXCLUDED.source_id,
                                target_id = EXCLUDED.target_id,
                                type = EXCLUDED.type,
                                properties = EXCLUDED.properties,
                                created_at = EXCLUDED.created_at
                        """, (
                            rel_id,
                            rel.get('source_id'),
                            rel.get('target_id'),
                            rel.get('type'),
                            properties_str,
                            rel.get('created_at')
                        ))
                    else:
                        # 如果没有 id，使用 source_id, target_id, type 作为唯一标识
                        self.duckdb.conn.execute("""
                            INSERT INTO relationships 
                            (source_id, target_id, type, properties, created_at)
                            SELECT ?, ?, ?, ?, ?
                            WHERE NOT EXISTS (
                                SELECT 1 FROM relationships 
                                WHERE source_id = ? AND target_id = ? AND type = ?
                            )
                        """, (
                            rel.get('source_id'),
                            rel.get('target_id'),
                            rel.get('type'),
                            properties_str,
                            rel.get('created_at'),
                            rel.get('source_id'),
                            rel.get('target_id'),
                            rel.get('type')
                        ))
                    stats["relationships_synced"] += 1
                except Exception as e:
                    stats["errors"].append(f"同步关系失败: {str(e)}")
            
            # DuckDB 不需要显式 commit，它是自动提交的
        
        except Exception as e:
            stats["errors"].append(f"同步过程出错: {str(e)}")
        
        return stats
    
    def sync_incremental(self, since: Optional[datetime] = None) -> dict:
        """
        增量同步
        
        Args:
            since: 同步起始时间
            
        Returns:
            同步结果统计
        """
        stats = {
            "entities_synced": 0,
            "relationships_synced": 0,
            "errors": []
        }
        
        if not since:
            # 如果没有指定时间，同步最近1小时的数据
            from datetime import timedelta
            since = datetime.now() - timedelta(hours=1)
        
        try:
            # 获取需要同步的实体
            entities = self.sqlite.query_entities(limit=100000)
            for entity in entities:
                created_at = entity.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if created_at and created_at >= since:
                    try:
                        properties_str = json.dumps(entity.get('properties', {})) if entity.get('properties') else None
                        self.duckdb.conn.execute("""
                            INSERT INTO entities 
                            (id, type, name, description, source, properties, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT (id) DO UPDATE SET
                                type = EXCLUDED.type,
                                name = EXCLUDED.name,
                                description = EXCLUDED.description,
                                source = EXCLUDED.source,
                                properties = EXCLUDED.properties,
                                updated_at = EXCLUDED.updated_at
                        """, (
                            entity.get('id'),
                            entity.get('type'),
                            entity.get('name'),
                            entity.get('description'),
                            entity.get('source'),
                            properties_str,
                            created_at,
                            entity.get('updated_at')
                        ))
                        stats["entities_synced"] += 1
                    except Exception as e:
                        stats["errors"].append(f"同步实体失败: {str(e)}")
            
            # 获取需要同步的关系
            relationships = self.sqlite.query_relationships(limit=100000)
            for rel in relationships:
                created_at = rel.get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                
                if created_at and created_at >= since:
                    try:
                        properties_str = json.dumps(rel.get('properties', {})) if rel.get('properties') else None
                        # 对于关系，使用 SQLite 中的 id 值
                        rel_id = rel.get('id')
                        if rel_id:
                            self.duckdb.conn.execute("""
                                INSERT INTO relationships 
                                (id, source_id, target_id, type, properties, created_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT (id) DO UPDATE SET
                                    source_id = EXCLUDED.source_id,
                                    target_id = EXCLUDED.target_id,
                                    type = EXCLUDED.type,
                                    properties = EXCLUDED.properties,
                                    created_at = EXCLUDED.created_at
                            """, (
                                rel_id,
                                rel.get('source_id'),
                                rel.get('target_id'),
                                rel.get('type'),
                                properties_str,
                                created_at
                            ))
                        else:
                            # 如果没有 id，使用 source_id, target_id, type 作为唯一标识
                            self.duckdb.conn.execute("""
                                INSERT INTO relationships 
                                (source_id, target_id, type, properties, created_at)
                                SELECT ?, ?, ?, ?, ?
                                WHERE NOT EXISTS (
                                    SELECT 1 FROM relationships 
                                    WHERE source_id = ? AND target_id = ? AND type = ?
                                )
                            """, (
                                rel.get('source_id'),
                                rel.get('target_id'),
                                rel.get('type'),
                                properties_str,
                                created_at,
                                rel.get('source_id'),
                                rel.get('target_id'),
                                rel.get('type')
                            ))
                        stats["relationships_synced"] += 1
                    except Exception as e:
                        stats["errors"].append(f"同步关系失败: {str(e)}")
            
            # DuckDB 不需要显式 commit，它是自动提交的
        
        except Exception as e:
            stats["errors"].append(f"增量同步过程出错: {str(e)}")
        
        return stats



