"""
图数据库元数据采集器
支持 Neo4j, FalkorDB 等
"""
from typing import Dict, Any, Optional, List
from neo4j import GraphDatabase
from falkordb import FalkorDB

from .base import BaseCollector
from ..core.models import (
    CollectionResult,
    MetadataType,
    RelationshipType
)


class GraphDatabaseCollector(BaseCollector):
    """图数据库采集器"""
    
    def __init__(self, db_type: str, connection_config: Dict[str, Any], 
                 source: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化图数据库采集器
        
        Args:
            db_type: 数据库类型 ('neo4j' 或 'falkordb')
            connection_config: 连接配置
            source: 数据源标识
            config: 配置信息
        """
        super().__init__("graph_database", source, config)
        self.db_type = db_type.lower()
        self.connection_config = connection_config
        self.driver = None
        self.graph = None
    
    def collect(self) -> CollectionResult:
        """
        采集图数据库元数据
        
        Returns:
            采集结果
        """
        result = CollectionResult()
        
        try:
            if self.db_type == "neo4j":
                result = self._collect_neo4j()
            elif self.db_type == "falkordb":
                result = self._collect_falkordb()
            else:
                result.errors.append(f"不支持的图数据库类型: {self.db_type}")
        except Exception as e:
            result.errors.append(f"采集失败: {str(e)}")
        
        return result
    
    def _collect_neo4j(self) -> CollectionResult:
        """采集 Neo4j 元数据"""
        result = CollectionResult()
        
        try:
            uri = self.connection_config.get("uri", "bolt://localhost:7687")
            username = self.connection_config.get("username", "neo4j")
            password = self.connection_config.get("password", "")
            
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
            with self.driver.session() as session:
                # 创建数据库实体
                db_entity = self.create_entity(
                    MetadataType.DATABASE,
                    name=self.source,
                    description=f"Neo4j 图数据库: {self.source}",
                    properties={
                        "type": "neo4j",
                        "uri": uri
                    }
                )
                result.entities.append(db_entity)
                
                # 获取所有节点标签
                labels_query = "CALL db.labels()"
                labels_result = session.run(labels_query)
                labels = [record["label"] for record in labels_result]
                
                # 为每个标签创建实体
                for label in labels:
                    label_entity = self.create_entity(
                        MetadataType.SCHEMA,
                        name=label,
                        description=f"节点标签: {label}",
                        properties={"label": label, "type": "node_label"}
                    )
                    result.entities.append(label_entity)
                    
                    # 创建数据库包含标签的关系
                    contains_rel = self.create_relationship(
                        db_entity.id,
                        label_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
                
                # 获取所有关系类型
                rel_types_query = "CALL db.relationshipTypes()"
                rel_types_result = session.run(rel_types_query)
                rel_types = [record["relationshipType"] for record in rel_types_result]
                
                # 为每个关系类型创建实体
                for rel_type in rel_types:
                    rel_entity = self.create_entity(
                        MetadataType.RELATIONSHIP,
                        name=rel_type,
                        description=f"关系类型: {rel_type}",
                        properties={"relationship_type": rel_type}
                    )
                    result.entities.append(rel_entity)
                    
                    # 创建数据库包含关系类型的关系
                    contains_rel = self.create_relationship(
                        db_entity.id,
                        rel_entity.id,
                        RelationshipType.CONTAINS
                    )
                    result.relationships.append(contains_rel)
        
        except Exception as e:
            result.errors.append(f"采集 Neo4j 失败: {str(e)}")
        
        return result
    
    def _collect_falkordb(self) -> CollectionResult:
        """采集 FalkorDB 元数据"""
        result = CollectionResult()
        
        try:
            host = self.connection_config.get("host", "localhost")
            port = self.connection_config.get("port", 6379)
            password = self.connection_config.get("password", "")
            graph_name = self.connection_config.get("graph_name", "default")
            
            # 使用 FalkorDB API (参考 testGraphDB/test.py)
            db_kwargs = {"host": host, "port": port}
            if password:
                db_kwargs["password"] = password
            db = FalkorDB(**db_kwargs)
            self.graph = db.select_graph(graph_name)
            
            # 创建数据库实体
            db_entity = self.create_entity(
                MetadataType.DATABASE,
                name=self.source,
                description=f"FalkorDB 图数据库: {self.source}",
                properties={
                    "type": "falkordb",
                    "graph_name": graph_name
                }
            )
            result.entities.append(db_entity)
            
            # 查询所有节点标签
            labels_query = """
            CALL db.labels()
            """
            labels_result = self.graph.query(labels_query)
            
            # 查询所有关系类型
            rel_types_query = """
            CALL db.relationshipTypes()
            """
            rel_types_result = self.graph.query(rel_types_query)
            
            # 处理标签和关系类型（类似 Neo4j 的处理方式）
            # 注意：FalkorDB 的查询结果格式可能与 Neo4j 不同
            
        except Exception as e:
            result.errors.append(f"采集 FalkorDB 失败: {str(e)}")
        
        return result
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
        if self.graph:
            # FalkorDB 通过 Redis 客户端关闭
            pass



