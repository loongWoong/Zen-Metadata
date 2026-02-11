"""
关系型数据库元数据采集器
支持 PostgreSQL, MySQL, SQLite 等
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.engine import Engine
# #region agent log
import json as json_log
import time
log_path = r"g:\data\Zen metadata\.cursor\debug.log"
# #endregion

from .base import BaseCollector
from ..core.models import (
    CollectionResult, 
    MetadataType, 
    RelationshipType
)


class RelationalDatabaseCollector(BaseCollector):
    """关系型数据库采集器"""
    
    def __init__(self, connection_string: str, source: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化关系型数据库采集器
        
        Args:
            connection_string: 数据库连接字符串
            source: 数据源标识
            config: 配置信息
        """
        super().__init__("relational_database", source, config)
        self.connection_string = connection_string
        self.engine: Optional[Engine] = None
    
    def _get_engine(self) -> Engine:
        """获取数据库引擎"""
        if self.engine is None:
            # #region agent log
            try:
                # 解析连接字符串以验证格式
                conn_parts = self.connection_string.split("@")
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"C","location":"relational.py:_get_engine","message":"Creating engine","data":{"conn_str_preview":conn_parts[0] + "@***" if len(conn_parts) > 1 else self.connection_string[:50],"parts_count":len(conn_parts)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            self.engine = create_engine(self.connection_string)
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"C","location":"relational.py:_get_engine","message":"Engine created","data":{"engine_type":str(type(self.engine))},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
        return self.engine
    
    def collect(self, schema: Optional[str] = None) -> CollectionResult:
        """
        采集关系型数据库元数据
        
        Args:
            schema: 数据库模式（可选）
            
        Returns:
            采集结果
        """
        result = CollectionResult()
        
        try:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"D","location":"relational.py:collect","message":"Starting collection","data":{"schema":schema},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            engine = self._get_engine()
            inspector = inspect(engine)
            metadata = MetaData()
            
            # 获取所有表
            tables = inspector.get_table_names(schema=schema)
            
            # 创建数据库实体
            db_entity = self.create_entity(
                MetadataType.DATABASE,
                name=self.source,
                description=f"数据库: {self.source}",
                properties={
                    "connection_string": self.connection_string.split("@")[-1] if "@" in self.connection_string else "***",
                    "schema": schema or "default"
                }
            )
            result.entities.append(db_entity)
            
            # 采集每个表的元数据
            for table_name in tables:
                table_result = self._collect_table(inspector, table_name, schema, db_entity.id)
                result.entities.extend(table_result.entities)
                result.relationships.extend(table_result.relationships)
            
            # 采集外键关系
            fk_result = self._collect_foreign_keys(inspector, schema)
            result.relationships.extend(fk_result.relationships)
            
        except Exception as e:
            # #region agent log
            try:
                import traceback
                error_details = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()[:1000],
                }
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"D","location":"relational.py:collect","message":"Collection failed","data":error_details,"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            result.errors.append(f"采集失败: {str(e)}")
        
        return result
    
    def _collect_table(self, inspector, table_name: str, schema: Optional[str], 
                      database_id: str) -> CollectionResult:
        """采集表的元数据"""
        result = CollectionResult()
        
        try:
            # 创建表实体
            table_entity = self.create_entity(
                MetadataType.TABLE,
                name=table_name,
                description=f"表: {table_name}",
                properties={
                    "schema": schema,
                    "table_name": table_name
                }
            )
            result.entities.append(table_entity)
            
            # 创建数据库包含表的关系
            contains_rel = self.create_relationship(
                database_id,
                table_entity.id,
                RelationshipType.CONTAINS
            )
            result.relationships.append(contains_rel)
            
            # 获取列信息
            columns = inspector.get_columns(table_name, schema=schema)
            for column in columns:
                column_entity = self.create_entity(
                    MetadataType.COLUMN,
                    name=column['name'],
                    description=f"列: {column['name']}",
                    properties={
                        "type": str(column['type']),
                        "nullable": column.get('nullable', True),
                        "default": str(column.get('default', '')),
                        "primary_key": column.get('primary_key', False)
                    }
                )
                result.entities.append(column_entity)
                
                # 创建表包含列的关系
                contains_rel = self.create_relationship(
                    table_entity.id,
                    column_entity.id,
                    RelationshipType.CONTAINS
                )
                result.relationships.append(contains_rel)
            
            # 获取索引信息
            indexes = inspector.get_indexes(table_name, schema=schema)
            for index in indexes:
                index_entity = self.create_entity(
                    MetadataType.INDEX,
                    name=index['name'],
                    description=f"索引: {index['name']}",
                    properties={
                        "unique": index.get('unique', False),
                        "columns": index.get('column_names', [])
                    }
                )
                result.entities.append(index_entity)
                
                # 创建表包含索引的关系
                contains_rel = self.create_relationship(
                    table_entity.id,
                    index_entity.id,
                    RelationshipType.CONTAINS
                )
                result.relationships.append(contains_rel)
            
        except Exception as e:
            result.errors.append(f"采集表 {table_name} 失败: {str(e)}")
        
        return result
    
    def _collect_foreign_keys(self, inspector, schema: Optional[str]) -> CollectionResult:
        """采集外键关系"""
        result = CollectionResult()
        
        try:
            tables = inspector.get_table_names(schema=schema)
            
            for table_name in tables:
                foreign_keys = inspector.get_foreign_keys(table_name, schema=schema)
                
                for fk in foreign_keys:
                    # 查找源表和目标表实体ID
                    source_table_id = self.generate_id(MetadataType.TABLE, table_name)
                    target_table_id = self.generate_id(
                        MetadataType.TABLE, 
                        fk['referred_table']
                    )
                    
                    # 创建外键关系
                    fk_rel = self.create_relationship(
                        source_table_id,
                        target_table_id,
                        RelationshipType.REFERENCES,
                        properties={
                            "columns": fk.get('constrained_columns', []),
                            "referred_columns": fk.get('referred_columns', []),
                            "name": fk.get('name', '')
                        }
                    )
                    result.relationships.append(fk_rel)
        
        except Exception as e:
            result.errors.append(f"采集外键失败: {str(e)}")
        
        return result
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()



