"""
搜索与语义检索服务
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re

from .graph import GraphStore
from .models import QueryResult


@dataclass
class SearchResult:
    """搜索结果"""
    entity: Dict[str, Any]
    score: float
    match_type: str  # "text", "semantic", "graph"
    highlights: List[str] = None


class SearchService:
    """搜索服务"""
    
    def __init__(self, graph_store: GraphStore, sqlite_processor=None):
        """
        初始化搜索服务
        
        Args:
            graph_store: 图数据库存储
            sqlite_processor: SQLite处理器（用于全文搜索）
        """
        self.graph_store = graph_store
        self.sqlite_processor = sqlite_processor
    
    def search(self, query: str,
              entity_type: Optional[str] = None,
              source: Optional[str] = None,
              limit: int = 50,
              use_semantic: bool = False,
              use_graph: bool = True) -> List[SearchResult]:
        """
        综合搜索
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            source: 数据源过滤
            limit: 结果数量限制
            use_semantic: 是否使用语义搜索
            use_graph: 是否使用图推荐
            
        Returns:
            搜索结果列表
        """
        # 1. 全文搜索
        text_results = self._text_search(query, entity_type, source, limit * 2)
        
        # 2. 语义搜索（如果启用）
        semantic_results = []
        if use_semantic:
            semantic_results = self._semantic_search(query, entity_type, source, limit * 2)
        
        # 3. 图推荐（如果启用）
        graph_results = []
        if use_graph and text_results:
            # 基于第一个文本搜索结果进行图推荐
            first_result = text_results[0]
            graph_results = self._graph_recommendation(first_result.entity.get('id'), limit)
        
        # 合并和排序结果
        all_results = self._merge_results(text_results, semantic_results, graph_results, limit)
        
        return all_results
    
    def _text_search(self, query: str,
                    entity_type: Optional[str] = None,
                    source: Optional[str] = None,
                    limit: int = 100) -> List[SearchResult]:
        """
        全文搜索
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            source: 数据源过滤
            limit: 结果数量限制
            
        Returns:
            搜索结果列表
        """
        if not self.sqlite_processor:
            # 如果没有SQLite处理器，使用图数据库查询
            return self._graph_text_search(query, entity_type, source, limit)
        
        # 从SQLite获取实体
        entities = self.sqlite_processor.query_entities(
            entity_type=entity_type,
            source=source,
            limit=10000
        )
        
        # 文本匹配
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for entity in entities:
            name = entity.get('name', '').lower()
            description = (entity.get('description') or '').lower()
            entity_type_str = entity.get('type', '').lower()
            
            # 计算匹配分数
            score = 0.0
            highlights = []
            match_type = "text"
            
            # 名称完全匹配
            if query_lower == name:
                score += 10.0
                highlights.append(f"名称完全匹配: {entity.get('name')}")
            # 名称包含
            elif query_lower in name:
                score += 5.0
                highlights.append(f"名称包含: {entity.get('name')}")
            # 描述包含
            elif query_lower in description:
                score += 2.0
                highlights.append(f"描述包含: {entity.get('description', '')[:100]}")
            
            # 词匹配
            name_words = set(name.split())
            desc_words = set(description.split())
            
            name_matches = len(query_words & name_words)
            desc_matches = len(query_words & desc_words)
            
            score += name_matches * 1.0
            score += desc_matches * 0.5
            
            if score > 0:
                results.append(SearchResult(
                    entity=entity,
                    score=score,
                    match_type=match_type,
                    highlights=highlights if highlights else None
                ))
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _graph_text_search(self, query: str,
                          entity_type: Optional[str] = None,
                          source: Optional[str] = None,
                          limit: int = 100) -> List[SearchResult]:
        """使用图数据库进行文本搜索"""
        query_lower = query.lower()
        escaped_query = query.replace("'", "\\'")
        
        # 构建Cypher查询
        cypher_query = f"""
        MATCH (n)
        WHERE toLower(n.name) CONTAINS '{escaped_query.lower()}'
        OR toLower(n.description) CONTAINS '{escaped_query.lower()}'
        """
        
        if entity_type:
            escaped_type = entity_type.replace("'", "\\'")
            cypher_query += f" AND n.type = '{escaped_type}'"
        
        if source:
            escaped_source = source.replace("'", "\\'")
            cypher_query += f" AND n.source = '{escaped_source}'"
        
        cypher_query += f" RETURN n LIMIT {limit}"
        
        try:
            result = self.graph_store.query(cypher_query)
            results = []
            
            for node in result.nodes:
                name = node.get('name', '').lower()
                description = (node.get('description') or '').lower()
                
                score = 0.0
                highlights = []
                
                if query_lower in name:
                    score += 5.0
                    highlights.append(f"名称包含: {node.get('name')}")
                if query_lower in description:
                    score += 2.0
                    highlights.append(f"描述包含: {node.get('description', '')[:100]}")
                
                if score > 0:
                    results.append(SearchResult(
                        entity=node,
                        score=score,
                        match_type="text",
                        highlights=highlights if highlights else None
                    ))
            
            results.sort(key=lambda x: x.score, reverse=True)
            return results
            
        except Exception as e:
            print(f"图数据库文本搜索失败: {e}")
            return []
    
    def _semantic_search(self, query: str,
                        entity_type: Optional[str] = None,
                        source: Optional[str] = None,
                        limit: int = 100) -> List[SearchResult]:
        """
        语义搜索（基于向量相似度）
        
        注意：这是一个简化版本，实际实现需要集成向量数据库或embedding模型
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            source: 数据源过滤
            limit: 结果数量限制
            
        Returns:
            搜索结果列表
        """
        # TODO: 集成embedding模型和向量数据库
        # 当前实现：基于文本相似度的简化版本
        
        if not self.sqlite_processor:
            return []
        
        entities = self.sqlite_processor.query_entities(
            entity_type=entity_type,
            source=source,
            limit=10000
        )
        
        query_words = set(query.lower().split())
        results = []
        
        for entity in entities:
            name = entity.get('name', '').lower()
            description = (entity.get('description') or '').lower()
            
            # 计算语义相似度（简化版：基于词重叠）
            name_words = set(name.split())
            desc_words = set(description.split())
            
            name_sim = len(query_words & name_words) / max(len(query_words | name_words), 1)
            desc_sim = len(query_words & desc_words) / max(len(query_words | desc_words), 1)
            
            semantic_score = name_sim * 0.6 + desc_sim * 0.4
            
            if semantic_score > 0.1:
                results.append(SearchResult(
                    entity=entity,
                    score=semantic_score,
                    match_type="semantic",
                    highlights=[f"语义相似度: {semantic_score:.2f}"]
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _graph_recommendation(self, entity_id: str, limit: int = 10) -> List[SearchResult]:
        """
        基于图结构的推荐
        
        Args:
            entity_id: 实体ID
            limit: 推荐数量
            
        Returns:
            推荐结果列表
        """
        try:
            # 获取实体的邻居节点
            result = self.graph_store.get_entity_relationships(entity_id)
            
            # 收集邻居实体
            neighbor_ids = set()
            for edge in result.edges:
                source = edge.get('source')
                target = edge.get('target')
                
                if source == entity_id:
                    neighbor_ids.add(target)
                elif target == entity_id:
                    neighbor_ids.add(source)
            
            # 获取邻居实体详情
            recommendations = []
            for nid in list(neighbor_ids)[:limit]:
                entity = self.graph_store.find_entity(nid)
                if entity:
                    recommendations.append(SearchResult(
                        entity=entity,
                        score=1.0,  # 图推荐的基础分数
                        match_type="graph",
                        highlights=[f"与 {entity_id} 相关联"]
                    ))
            
            return recommendations
            
        except Exception as e:
            print(f"图推荐失败: {e}")
            return []
    
    def _merge_results(self, text_results: List[SearchResult],
                      semantic_results: List[SearchResult],
                      graph_results: List[SearchResult],
                      limit: int) -> List[SearchResult]:
        """
        合并和排序搜索结果
        
        Args:
            text_results: 文本搜索结果
            semantic_results: 语义搜索结果
            graph_results: 图推荐结果
            limit: 结果数量限制
            
        Returns:
            合并后的搜索结果
        """
        # 使用字典去重（基于实体ID）
        result_dict = {}
        
        # 添加文本搜索结果（权重最高）
        for result in text_results:
            entity_id = result.entity.get('id')
            if entity_id not in result_dict:
                result_dict[entity_id] = result
            else:
                # 合并分数
                existing = result_dict[entity_id]
                existing.score = max(existing.score, result.score) + 0.5  # 文本匹配加分
        
        # 添加语义搜索结果
        for result in semantic_results:
            entity_id = result.entity.get('id')
            if entity_id not in result_dict:
                result_dict[entity_id] = result
            else:
                # 合并分数
                existing = result_dict[entity_id]
                existing.score += result.score * 0.3  # 语义匹配加权
        
        # 添加图推荐结果
        for result in graph_results:
            entity_id = result.entity.get('id')
            if entity_id not in result_dict:
                result_dict[entity_id] = result
            else:
                # 合并分数
                existing = result_dict[entity_id]
                existing.score += result.score * 0.2  # 图推荐加权
        
        # 转换为列表并排序
        merged_results = list(result_dict.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results[:limit]
    
    def search_with_quality(self, query: str,
                           entity_type: Optional[str] = None,
                           source: Optional[str] = None,
                           limit: int = 50,
                           min_quality: float = 0.0) -> List[SearchResult]:
        """
        带质量过滤的搜索
        
        Args:
            query: 搜索查询
            entity_type: 实体类型过滤
            source: 数据源过滤
            limit: 结果数量限制
            min_quality: 最小质量评分
            
        Returns:
            搜索结果列表
        """
        # 先进行普通搜索
        results = self.search(query, entity_type, source, limit * 2, use_semantic=True, use_graph=True)
        
        # 如果有质量评分，进行过滤和加权
        # TODO: 集成质量评分系统
        # 当前实现：直接返回结果
        
        return results[:limit]



