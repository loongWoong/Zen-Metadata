"""
血缘追踪器 - 基于图数据库的关系追踪和影响分析
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .graph import GraphStore
from .models import QueryResult, MetadataEntity, MetadataRelationship


class LineageGranularity(str, Enum):
    """血缘粒度"""
    COLUMN = "column"
    TABLE = "table"
    JOB = "job"
    SYSTEM = "system"


@dataclass
class LineagePath:
    """血缘路径"""
    path: List[str]  # 实体ID路径
    relationships: List[str]  # 关系类型路径
    depth: int  # 路径深度
    path_length: int  # 路径长度（边的数量）
    quality_score: float = 1.0  # 路径质量评分
    risk_score: float = 0.0  # 风险评分


@dataclass
class ImpactAnalysis:
    """影响分析结果"""
    entity_id: str
    direction: str  # "upstream" or "downstream"
    affected_entities: List[Dict[str, Any]] = field(default_factory=list)
    paths: List[LineagePath] = field(default_factory=list)
    risk_summary: Dict[str, Any] = field(default_factory=dict)
    total_affected: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0


class LineageTracker:
    """血缘追踪器"""
    
    # 定义构成血缘的关系类型
    LINEAGE_RELATIONSHIP_TYPES = {
        "depends_on",
        "references",
        "contains",
        "calls",
        "imports",
        "uses",
        "belongs_to"
    }
    
    def __init__(self, graph_store: GraphStore):
        """
        初始化血缘追踪器
        
        Args:
            graph_store: 图数据库存储
        """
        self.graph_store = graph_store
    
    def discover_lineage(self, entity_id: str, 
                        granularity: Optional[LineageGranularity] = None,
                        max_depth: int = 5) -> Dict[str, Any]:
        """
        发现实体的血缘关系
        
        Args:
            entity_id: 实体ID
            granularity: 血缘粒度（可选）
            max_depth: 最大深度
            
        Returns:
            血缘图数据
        """
        # 获取上游和下游
        upstream_paths = self.trace_upstream(entity_id, max_depth)
        downstream_paths = self.trace_downstream(entity_id, max_depth)
        
        # 构建血缘图
        all_entity_ids = set([entity_id])
        for path in upstream_paths + downstream_paths:
            all_entity_ids.update(path.path)
        
        # 查询所有相关实体和关系
        lineage_graph = self._build_lineage_graph(list(all_entity_ids), upstream_paths, downstream_paths, entity_id)
        
        return {
            "entity_id": entity_id,
            "granularity": granularity.value if granularity else None,
            "upstream_paths": [self._path_to_dict(p) for p in upstream_paths],
            "downstream_paths": [self._path_to_dict(p) for p in downstream_paths],
            "graph": lineage_graph,
            "statistics": {
                "upstream_count": len(upstream_paths),
                "downstream_count": len(downstream_paths),
                "total_entities": len(all_entity_ids),
                "max_depth": max_depth
            }
        }
    
    def trace_upstream(self, entity_id: str, depth: int = -1) -> List[LineagePath]:
        """
        追踪上游血缘
        
        Args:
            entity_id: 实体ID
            depth: 追踪深度（-1表示无限制）
            
        Returns:
            上游路径列表
        """
        return self._trace_lineage(entity_id, direction="upstream", depth=depth)
    
    def trace_downstream(self, entity_id: str, depth: int = -1) -> List[LineagePath]:
        """
        追踪下游血缘
        
        Args:
            entity_id: 实体ID
            depth: 追踪深度（-1表示无限制）
            
        Returns:
            下游路径列表
        """
        return self._trace_lineage(entity_id, direction="downstream", depth=depth)
    
    def _trace_lineage(self, entity_id: str, direction: str, depth: int = -1) -> List[LineagePath]:
        """
        追踪血缘路径 - 使用BFS遍历实现多层深度查询
        
        Args:
            entity_id: 实体ID
            direction: 方向（"upstream" 或 "downstream"）
            depth: 追踪深度（-1表示无限制，1表示只查询一层）
            
        Returns:
            路径列表
        """
        if depth == 0:
            return []
        
        # 使用BFS遍历实现多层深度查询，确保能正确提取关系类型
        # 这种方法比路径查询更可靠，能正确处理关系类型
        return self._trace_lineage_bfs(entity_id, direction, depth)
    
    def _build_paths_from_nodes(self, nodes: List[Dict], edges: List[Dict], 
                                start_id: str, direction: str, max_depth: int) -> List[LineagePath]:
        """从节点和边构建路径"""
        # 构建邻接表
        adjacency = {}
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            rel_type = edge.get('type')
            
            if not source or not target:
                continue
            
            if direction == "upstream":
                # 上游：反向边
                if target not in adjacency:
                    adjacency[target] = []
                adjacency[target].append((source, rel_type))
            else:
                # 下游：正向边
                if source not in adjacency:
                    adjacency[source] = []
                adjacency[source].append((target, rel_type))
        
        # BFS遍历构建路径
        paths = []
        queue = [(start_id, [start_id], [])]
        visited = set()
        
        while queue and len(paths) < 100:
            current_id, path_ids, rel_types = queue.pop(0)
            
            if len(path_ids) > max_depth + 1 and max_depth > 0:
                continue
            
            if current_id not in adjacency:
                continue
            
            for neighbor_id, rel_type in adjacency[current_id]:
                if neighbor_id in path_ids:  # 避免循环
                    continue
                
                new_path = path_ids + [neighbor_id]
                new_rel_types = rel_types + [rel_type] if rel_type else rel_types
                
                path_key = tuple(new_path)
                if path_key not in visited:
                    visited.add(path_key)
                    paths.append(LineagePath(
                        path=new_path,
                        relationships=new_rel_types,
                        depth=len(new_path) - 1,
                        path_length=len(new_path) - 1
                    ))
                    
                    if len(new_path) <= max_depth + 1 or max_depth < 0:
                        queue.append((neighbor_id, new_path, new_rel_types))
        
        return paths
    
    def _build_paths_from_query_result(self, result: Any, entity_id: str, 
                                       direction: str, max_depth: int) -> List[LineagePath]:
        """
        从路径查询结果构建路径
        
        Args:
            result: 查询结果对象
            entity_id: 起始实体ID
            direction: 方向
            max_depth: 最大深度
            
        Returns:
            路径列表
        """
        paths = []
        visited_paths = set()
        
        # 构建节点ID到节点的映射
        node_map = {}
        for node in result.nodes:
            node_id = node.get('id') or node.get('entity_id')
            if node_id:
                node_map[str(node_id)] = node
        
        # 构建邻接表
        adjacency = {}
        for edge in result.edges:
            source = edge.get('source')
            target = edge.get('target')
            rel_type = edge.get('type') or edge.get('rel_type')
            
            if not source or not target:
                continue
            
            source = str(source)
            target = str(target)
            
            if direction == "upstream":
                # 上游：反向边（从target到source）
                if target not in adjacency:
                    adjacency[target] = []
                adjacency[target].append((source, rel_type))
            else:
                # 下游：正向边（从source到target）
                if source not in adjacency:
                    adjacency[source] = []
                adjacency[source].append((target, rel_type))
        
        # BFS遍历构建路径
        queue = [(entity_id, [entity_id], [])]
        
        while queue and len(paths) < 100:
            current_id, path_ids, rel_types = queue.pop(0)
            
            # 检查深度限制
            if max_depth > 0 and len(path_ids) > max_depth + 1:
                continue
            
            if str(current_id) not in adjacency:
                continue
            
            for neighbor_id, rel_type in adjacency[str(current_id)]:
                # 避免循环
                if neighbor_id in path_ids:
                    continue
                
                new_path = path_ids + [neighbor_id]
                new_rel_types = rel_types + [rel_type] if rel_type else rel_types
                
                path_key = tuple(new_path)
                if path_key not in visited_paths:
                    visited_paths.add(path_key)
                    paths.append(LineagePath(
                        path=new_path,
                        relationships=new_rel_types,
                        depth=len(new_path) - 1,
                        path_length=len(new_path) - 1
                    ))
                    
                    # 继续遍历
                    if max_depth < 0 or len(new_path) <= max_depth + 1:
                        queue.append((neighbor_id, new_path, new_rel_types))
        
        return paths
    
    def _build_paths_from_edges(self, result: Any, entity_id: str, 
                                direction: str) -> List[LineagePath]:
        """
        从边查询结果构建路径（单层）
        
        Args:
            result: 查询结果对象
            entity_id: 起始实体ID
            direction: 方向
            
        Returns:
            路径列表
        """
        paths = []
        visited_paths = set()
        
        for edge in result.edges:
            source = edge.get('source')
            target = edge.get('target')
            rel_type = edge.get('rel_type') or edge.get('type')
            
            if not source or not target:
                continue
            
            # 构建路径
            if direction == "upstream":
                # 上游：target是当前实体，source是上游实体
                if str(target) == str(entity_id):
                    path_ids = [str(source), str(target)]
                else:
                    continue
            else:
                # 下游：source是当前实体，target是下游实体
                if str(source) == str(entity_id):
                    path_ids = [str(source), str(target)]
                else:
                    continue
            
            # 创建路径对象
            path_key = tuple(path_ids)
            if path_key not in visited_paths:
                visited_paths.add(path_key)
                paths.append(LineagePath(
                    path=path_ids,
                    relationships=[rel_type] if rel_type else [],
                    depth=1,
                    path_length=1
                ))
        
        return paths
    
    def _trace_lineage_bfs(self, entity_id: str, direction: str, depth: int) -> List[LineagePath]:
        """
        使用BFS遍历实现多层深度查询
        
        Args:
            entity_id: 实体ID
            direction: 方向
            depth: 深度
            
        Returns:
            路径列表
        """
        if depth == 0:
            return []
        
        paths = []
        visited_paths = set()
        queue = [(entity_id, [entity_id], [])]  # (当前节点ID, 路径节点列表, 关系类型列表)
        
        # 确定最大深度
        max_depth = depth if depth > 0 else 10
        
        escaped_id = str(entity_id).replace("'", "\\'")
        
        while queue and len(paths) < 100:
            current_id, path_ids, rel_types = queue.pop(0)
            
            # 检查深度限制
            current_depth = len(path_ids) - 1
            if max_depth > 0 and current_depth >= max_depth:
                continue
            
            # 查询当前节点的邻居
            current_escaped_id = str(current_id).replace("'", "\\'")
            
            if direction == "upstream":
                # 查询上游：找到指向当前节点的关系
                query = f"""
                MATCH (target {{id: '{current_escaped_id}'}})<-[r]-(source)
                RETURN source, r, target, TYPE(r) as rel_type
                LIMIT 100
                """
            else:
                # 查询下游：找到从当前节点出发的关系
                query = f"""
                MATCH (source {{id: '{current_escaped_id}'}})-[r]->(target)
                RETURN source, r, target, TYPE(r) as rel_type
                LIMIT 100
                """
            
            try:
                result = self.graph_store.query(query)
                
                # 处理查询结果中的边
                for edge in result.edges:
                    source = edge.get('source')
                    target = edge.get('target')
                    # 优先使用 rel_type（从 TYPE(r) as rel_type 返回），然后是 type
                    rel_type = edge.get('rel_type') or edge.get('type')
                    
                    # 如果仍然没有关系类型，尝试从关系对象中提取
                    if not rel_type or rel_type == 'related_to':
                        # 检查边字典中是否有其他字段包含关系类型信息
                        for key in ['relationship_type', 'relation_type', 'label']:
                            if key in edge and edge[key]:
                                rel_type = edge[key]
                                break
                    
                    # 如果还是没有，使用默认值
                    if not rel_type:
                        rel_type = 'related_to'
                    
                    if not source or not target:
                        continue
                    
                    source = str(source)
                    target = str(target)
                    
                    # 确定邻居节点
                    if direction == "upstream":
                        # 上游：target是当前节点，source是上游节点
                        if str(target) == str(current_id):
                            neighbor_id = source
                        else:
                            continue
                    else:
                        # 下游：source是当前节点，target是下游节点
                        if str(source) == str(current_id):
                            neighbor_id = target
                        else:
                            continue
                    
                    # 避免循环：检查邻居是否已在路径中
                    if neighbor_id in path_ids:
                        continue
                    
                    # 构建新路径
                    new_path = path_ids + [neighbor_id]
                    new_rel_types = rel_types + [rel_type]
                    
                    # 检查是否已访问过此路径
                    path_key = tuple(new_path)
                    if path_key not in visited_paths:
                        visited_paths.add(path_key)
                        
                        # 创建路径对象
                        paths.append(LineagePath(
                            path=new_path,
                            relationships=new_rel_types,
                            depth=len(new_path) - 1,
                            path_length=len(new_path) - 1
                        ))
                        
                        # 继续遍历：如果未达到最大深度，将邻居加入队列
                        if max_depth < 0 or len(new_path) <= max_depth + 1:
                            queue.append((neighbor_id, new_path, new_rel_types))
                            
            except Exception as e:
                print(f"查询邻居节点失败 (current_id={current_id}): {e}")
                continue
        
        return paths
    
    def _trace_lineage_fallback(self, entity_id: str, direction: str, depth: int) -> List[LineagePath]:
        """
        回退查询方法：使用BFS遍历实现多层深度查询
        
        Args:
            entity_id: 实体ID
            direction: 方向
            depth: 深度
            
        Returns:
            路径列表
        """
        if depth == 0:
            return []
        
        # 使用BFS遍历实现多层查询
        paths = []
        visited_paths = set()
        queue = [(entity_id, [entity_id], [])]
        
        # 确定最大深度
        max_depth = depth if depth > 0 else 10
        
        while queue and len(paths) < 100:
            current_id, path_ids, rel_types = queue.pop(0)
            
            # 检查深度限制
            if max_depth > 0 and len(path_ids) > max_depth + 1:
                continue
            
            # 查询当前节点的邻居
            escaped_id = str(current_id).replace("'", "\\'")
            
            if direction == "upstream":
                query = f"""
                MATCH (target {{id: '{escaped_id}'}})<-[r]-(source)
                RETURN source, r, target, TYPE(r) as rel_type
                LIMIT 100
                """
            else:
                query = f"""
                MATCH (source {{id: '{escaped_id}'}})-[r]->(target)
                RETURN source, r, target, TYPE(r) as rel_type
                LIMIT 100
                """
            
            try:
                result = self.graph_store.query(query)
                
                for edge in result.edges:
                    source = edge.get('source')
                    target = edge.get('target')
                    rel_type = edge.get('rel_type') or edge.get('type')
                    
                    if not source or not target:
                        continue
                    
                    # 确定邻居节点
                    if direction == "upstream":
                        neighbor_id = str(source) if str(target) == str(current_id) else None
                    else:
                        neighbor_id = str(target) if str(source) == str(current_id) else None
                    
                    if not neighbor_id:
                        continue
                    
                    # 避免循环
                    if neighbor_id in path_ids:
                        continue
                    
                    new_path = path_ids + [neighbor_id]
                    new_rel_types = rel_types + [rel_type] if rel_type else rel_types
                    
                    path_key = tuple(new_path)
                    if path_key not in visited_paths:
                        visited_paths.add(path_key)
                        paths.append(LineagePath(
                            path=new_path,
                            relationships=new_rel_types,
                            depth=len(new_path) - 1,
                            path_length=len(new_path) - 1
                        ))
                        
                        # 继续遍历
                        if max_depth < 0 or len(new_path) <= max_depth + 1:
                            queue.append((neighbor_id, new_path, new_rel_types))
            except Exception as e:
                print(f"查询邻居节点失败: {e}")
                continue
        
        return paths
    
    def analyze_impact(self, entity_id: str, 
                       direction: str = "downstream",
                       include_quality: bool = True) -> ImpactAnalysis:
        """
        分析影响范围
        
        Args:
            entity_id: 实体ID
            direction: 分析方向（"upstream" 或 "downstream"）
            include_quality: 是否包含质量评分
            
        Returns:
            影响分析结果
        """
        # 追踪路径
        if direction == "upstream":
            paths = self.trace_upstream(entity_id, depth=5)
        else:
            paths = self.trace_downstream(entity_id, depth=5)
        
        # 收集受影响的实体
        affected_entity_ids = set()
        for path in paths:
            if direction == "upstream":
                # 上游：排除起始实体
                affected_entity_ids.update(path.path[1:])
            else:
                # 下游：排除起始实体
                affected_entity_ids.update(path.path[1:])
        
        # 计算风险评分
        risk_scores = {}
        for path in paths:
            risk = self._calculate_path_risk(path, include_quality)
            path.risk_score = risk
            
            for entity_id_in_path in path.path[1:]:  # 排除起始实体
                if entity_id_in_path not in risk_scores:
                    risk_scores[entity_id_in_path] = []
                risk_scores[entity_id_in_path].append(risk)
        
        # 获取受影响实体的详细信息
        affected_entities = []
        for eid in affected_entity_ids:
            entity = self.graph_store.find_entity(eid)
            if entity:
                avg_risk = sum(risk_scores.get(eid, [0])) / len(risk_scores.get(eid, [1]))
                entity['risk_score'] = avg_risk
                affected_entities.append(entity)
        
        # 按风险评分排序
        affected_entities.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        
        # 统计风险等级
        high_risk = sum(1 for e in affected_entities if e.get('risk_score', 0) > 0.7)
        medium_risk = sum(1 for e in affected_entities if 0.3 < e.get('risk_score', 0) <= 0.7)
        low_risk = sum(1 for e in affected_entities if e.get('risk_score', 0) <= 0.3)
        
        return ImpactAnalysis(
            entity_id=entity_id,
            direction=direction,
            affected_entities=affected_entities,
            paths=paths,
            risk_summary={
                "high_risk_count": high_risk,
                "medium_risk_count": medium_risk,
                "low_risk_count": low_risk,
                "average_risk": sum(e.get('risk_score', 0) for e in affected_entities) / len(affected_entities) if affected_entities else 0
            },
            total_affected=len(affected_entities),
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=low_risk
        )
    
    def _calculate_path_risk(self, path: LineagePath, include_quality: bool = True) -> float:
        """
        计算路径风险评分
        
        Args:
            path: 血缘路径
            include_quality: 是否包含质量评分
            
        Returns:
            风险评分（0-1）
        """
        # 基础风险：路径长度
        path_length_risk = min(path.path_length / 10.0, 1.0)
        
        # 质量风险（如果有质量评分）
        quality_risk = 0.0
        if include_quality and path.quality_score < 1.0:
            quality_risk = 1.0 - path.quality_score
        
        # 综合风险
        risk = path_length_risk * 0.5 + quality_risk * 0.5
        
        return min(risk, 1.0)
    
    def _format_relationship_types(self) -> str:
        """格式化关系类型列表为Cypher格式"""
        types_str = ", ".join([f"'{t}'" for t in self.LINEAGE_RELATIONSHIP_TYPES])
        return f"[{types_str}]"
    
    def _is_lineage_relationship(self, rel_type: str) -> bool:
        """判断关系类型是否属于血缘关系"""
        return rel_type.lower() in self.LINEAGE_RELATIONSHIP_TYPES
    
    def _path_to_dict(self, path: LineagePath) -> Dict[str, Any]:
        """将路径对象转换为字典"""
        return {
            "path": path.path,
            "relationships": path.relationships,
            "depth": path.depth,
            "path_length": path.path_length,
            "quality_score": path.quality_score,
            "risk_score": path.risk_score
        }
    
    def _build_lineage_graph(self, entity_ids: List[str], 
                            upstream_paths: List[LineagePath],
                            downstream_paths: List[LineagePath],
                            current_entity_id: str) -> Dict[str, Any]:
        """构建血缘图数据"""
        # 查询所有相关实体
        nodes = []
        edges = []
        
        for eid in entity_ids:
            entity = self.graph_store.find_entity(eid)
            if entity:
                nodes.append(entity)
        
        # 从路径中提取边，保留方向信息
        edge_set = set()
        
        # 处理上游路径（从上游实体指向当前实体）
        # 上游路径应该表示：数据从上游实体流向当前实体
        # 所以箭头应该从上游实体指向当前实体
        for path in upstream_paths:
            path_list = path.path
            # 检查路径方向：如果路径的第一个节点是当前实体，需要反转
            # 如果路径的最后一个节点是当前实体，则方向正确
            if current_entity_id and len(path_list) > 1:
                # 如果路径从当前实体开始，需要反转
                if path_list[0] == current_entity_id:
                    path_list = list(reversed(path_list))
                    rel_list = list(reversed(path.relationships)) if path.relationships else []
                else:
                    rel_list = path.relationships if path.relationships else []
            else:
                rel_list = path.relationships if path.relationships else []
            
            for i in range(len(path_list) - 1):
                source = path_list[i]  # 上游实体
                target = path_list[i + 1]  # 当前实体（或路径中的下一个节点）
                rel_type = rel_list[i] if i < len(rel_list) else "related_to"
                
                edge_key = (source, target, rel_type)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "direction": "upstream"  # 标记为上游关系，箭头从上游指向当前
                    })
        
        # 处理下游路径（从当前实体指向下游实体）
        for path in downstream_paths:
            for i in range(len(path.path) - 1):
                source = path.path[i]
                target = path.path[i + 1]
                rel_type = path.relationships[i] if i < len(path.relationships) else "related_to"
                
                edge_key = (source, target, rel_type)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "direction": "downstream"  # 标记为下游关系
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }

