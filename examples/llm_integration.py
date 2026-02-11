"""
LLM 集成示例 - 为 LLM 提供元数据查询接口
"""
from typing import List, Dict, Any
from src.core.graph import GraphStore
from src.processing.sqlite import SQLiteProcessor
from src.visualization.graphiti import GraphitiVisualizer


class LLMMetadataInterface:
    """LLM 元数据接口"""
    
    def __init__(self, graph_store: GraphStore, sqlite_processor: SQLiteProcessor):
        """
        初始化 LLM 接口
        
        Args:
            graph_store: 图数据库存储
            sqlite_processor: SQLite 处理器
        """
        self.graph_store = graph_store
        self.sqlite_processor = sqlite_processor
    
    def get_entity_info(self, entity_name: str) -> Dict[str, Any]:
        """
        获取实体信息
        
        Args:
            entity_name: 实体名称
            
        Returns:
            实体信息
        """
        # 从 SQLite 查询
        entities = self.sqlite_processor.query_entities(limit=1000)
        matching = [e for e in entities if entity_name.lower() in e.get('name', '').lower()]
        
        if not matching:
            return {"error": f"未找到实体: {entity_name}"}
        
        entity = matching[0]
        entity_id = entity['id']
        
        # 获取关系
        relationships = self.graph_store.get_entity_relationships(entity_id)
        
        return {
            "entity": entity,
            "relationships": {
                "outgoing": [r for r in relationships.nodes if r.get('id') != entity_id],
                "incoming": []
            }
        }
    
    def search_entities(self, query: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """
        搜索实体
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            
        Returns:
            实体列表
        """
        entities = self.sqlite_processor.query_entities(
            entity_type=entity_type,
            limit=100
        )
        
        # 简单文本匹配
        results = [
            e for e in entities
            if query.lower() in e.get('name', '').lower() or
               query.lower() in (e.get('description') or '').lower()
        ]
        
        return results
    
    def get_relationship_path(self, source_name: str, target_name: str, 
                             max_depth: int = 3) -> Dict[str, Any]:
        """
        获取两个实体之间的路径
        
        Args:
            source_name: 源实体名称
            target_name: 目标实体名称
            max_depth: 最大深度
            
        Returns:
            路径信息
        """
        # 查找实体ID
        source_entities = self.search_entities(source_name)
        target_entities = self.search_entities(target_name)
        
        if not source_entities or not target_entities:
            return {"error": "未找到源或目标实体"}
        
        source_id = source_entities[0]['id']
        target_id = target_entities[0]['id']
        
        # 查询路径
        query = f"""
        MATCH path = shortestPath((a {{id: $source_id}})-[*1..{max_depth}]-(b {{id: $target_id}}))
        RETURN path
        """
        
        result = self.graph_store.query(query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        return {
            "source": source_entities[0],
            "target": target_entities[0],
            "path": result.nodes,
            "path_length": len(result.nodes) - 1 if result.nodes else 0
        }
    
    def get_context_for_entity(self, entity_name: str, depth: int = 2) -> Dict[str, Any]:
        """
        获取实体的上下文（邻居实体和关系）
        
        Args:
            entity_name: 实体名称
            depth: 深度
            
        Returns:
            上下文信息
        """
        entities = self.search_entities(entity_name)
        if not entities:
            return {"error": f"未找到实体: {entity_name}"}
        
        entity_id = entities[0]['id']
        
        # 查询邻居
        query = f"""
        MATCH (n {{id: $id}})-[*1..{depth}]-(m)
        RETURN DISTINCT m
        LIMIT 50
        """
        
        result = self.graph_store.query(query, {"id": entity_id})
        
        return {
            "entity": entities[0],
            "neighbors": result.nodes,
            "neighbor_count": len(result.nodes)
        }
    
    def get_semantic_summary(self, entity_name: str) -> str:
        """
        生成实体的语义摘要（供 LLM 使用）
        
        Args:
            entity_name: 实体名称
            
        Returns:
            语义摘要文本
        """
        info = self.get_entity_info(entity_name)
        if "error" in info:
            return info["error"]
        
        entity = info["entity"]
        context = self.get_context_for_entity(entity_name, depth=1)
        
        summary = f"""
实体: {entity.get('name')}
类型: {entity.get('type')}
描述: {entity.get('description', '无描述')}
来源: {entity.get('source')}

关联实体数量: {context.get('neighbor_count', 0)}
"""
        
        return summary.strip()


def example_llm_interface():
    """LLM 接口使用示例"""
    print("=== LLM 元数据接口示例 ===")
    
    # 初始化
    graph_store = GraphStore(
        host="localhost",
        port=6379,
        graph_name="zen_metadata"
    )
    sqlite_processor = SQLiteProcessor("data/zen_metadata.db")
    
    # 创建接口
    llm_interface = LLMMetadataInterface(graph_store, sqlite_processor)
    
    # 搜索实体
    print("\n1. 搜索实体:")
    results = llm_interface.search_entities("file", entity_type="file")
    print(f"找到 {len(results)} 个文件实体")
    for r in results[:3]:
        print(f"  - {r.get('name')} ({r.get('type')})")
    
    # 获取实体信息
    print("\n2. 获取实体信息:")
    info = llm_interface.get_entity_info("example")
    if "error" not in info:
        print(f"实体: {info['entity'].get('name')}")
    
    # 获取语义摘要
    print("\n3. 获取语义摘要:")
    summary = llm_interface.get_semantic_summary("example")
    print(summary)
    
    # 清理
    graph_store.close()
    sqlite_processor.close()


if __name__ == "__main__":
    example_llm_interface()






