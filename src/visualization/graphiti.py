"""
Graphiti 图形可视化集成
"""
from typing import List, Dict, Any, Optional
import networkx as nx
import json
import math

from ..core.models import QueryResult


class GraphitiVisualizer:
    """Graphiti 可视化器"""
    
    def __init__(self):
        """初始化可视化器"""
        self.graph = nx.DiGraph()
    
    def load_from_query_result(self, query_result: QueryResult):
        """
        从查询结果加载图数据
        
        Args:
            query_result: 查询结果
        """
        # 添加节点
        for node in query_result.nodes:
            node_id = node.get('id', str(node))
            self.graph.add_node(
                node_id,
                **{k: v for k, v in node.items() if k != 'id'}
            )
        
        # 添加边
        for edge in query_result.edges:
            source = edge.get('source', edge.get('source_id'))
            target = edge.get('target', edge.get('target_id'))
            if source and target:
                self.graph.add_edge(
                    source,
                    target,
                    **{k: v for k, v in edge.items() if k not in ['source', 'target', 'source_id', 'target_id']}
                )
    
    def to_graphiti_format(self) -> Dict[str, Any]:
        """
        转换为 Graphiti 格式
        
        Returns:
            Graphiti 格式的数据
        """
        nodes = []
        edges = []
        
        # 转换节点
        for node_id, data in self.graph.nodes(data=True):
            node_data = {
                "id": node_id,
                "label": data.get('name', node_id),
                "type": data.get('type', 'unknown'),
                **{k: v for k, v in data.items() if k not in ['name', 'type']}
            }
            nodes.append(node_data)
        
        # 转换边
        for source, target, data in self.graph.edges(data=True):
            edge_data = {
                "source": source,
                "target": target,
                "type": data.get('type', 'related_to'),
                **{k: v for k, v in data.items() if k != 'type'}
            }
            edges.append(edge_data)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def to_json(self) -> str:
        """
        转换为 JSON 字符串
        
        Returns:
            JSON 字符串
        """
        return json.dumps(self.to_graphiti_format(), indent=2, ensure_ascii=False)
    
    def get_layout(self, layout_type: str = "spring") -> Dict[str, Any]:
        """
        计算节点布局
        
        Args:
            layout_type: 布局类型 ('spring', 'circular', 'hierarchical')
            
        Returns:
            布局数据
        """
        if self.graph.number_of_nodes() == 0:
            return {}
        
        # 计算布局
        if layout_type == "spring":
            # 尝试使用 spring_layout，如果 scipy 不可用则使用 circular_layout
            try:
                # 使用更大的 k 值来增加节点间距，更多迭代次数以获得更好的布局
                k = max(2.0, min(3.0, 50.0 / max(1, self.graph.number_of_nodes())))
                pos = nx.spring_layout(self.graph, k=k, iterations=100, seed=42)
            except (ImportError, ModuleNotFoundError):
                # 如果 scipy 不可用，使用 circular_layout 作为 fallback
                pos = nx.circular_layout(self.graph)
        elif layout_type == "circular":
            pos = nx.circular_layout(self.graph)
        elif layout_type == "hierarchical":
            try:
                pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
            except:
                # 如果 graphviz 不可用，尝试使用 spring_layout，如果 scipy 也不可用则使用 circular_layout
                try:
                    pos = nx.spring_layout(self.graph, k=2.0, iterations=100, seed=42)
                except (ImportError, ModuleNotFoundError):
                    pos = nx.circular_layout(self.graph)
        else:
            # 默认布局：尝试 spring_layout，如果 scipy 不可用则使用 circular_layout
            try:
                pos = nx.spring_layout(self.graph, k=2.0, iterations=100, seed=42)
            except (ImportError, ModuleNotFoundError):
                pos = nx.circular_layout(self.graph)
        
        # 将坐标从 [-1, 1] 范围放大到合适的像素范围
        # 使用 1000x800 的画布大小，留出边距
        if pos:
            # 获取所有坐标的最小值和最大值
            x_coords = [p[0] for p in pos.values()]
            y_coords = [p[1] for p in pos.values()]
            
            if x_coords and y_coords:
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # 计算缩放比例，留出边距
                margin = 50
                width = 1000 - 2 * margin
                height = 800 - 2 * margin
                
                # 避免除零
                x_range = max_x - min_x if max_x != min_x else 1
                y_range = max_y - min_y if max_y != min_y else 1
                
                layout = {}
                for node_id, (x, y) in pos.items():
                    # 归一化到 [0, 1]，然后缩放到目标范围
                    normalized_x = (x - min_x) / x_range if x_range > 0 else 0.5
                    normalized_y = (y - min_y) / y_range if y_range > 0 else 0.5
                    
                    layout[node_id] = {
                        "x": float(margin + normalized_x * width),
                        "y": float(margin + normalized_y * height)
                    }
            else:
                # 如果没有有效坐标，使用默认布局
                layout = {}
                for i, node_id in enumerate(self.graph.nodes()):
                    angle = 2 * math.pi * i / max(1, self.graph.number_of_nodes())
                    layout[node_id] = {
                        "x": float(400 + 300 * math.cos(angle)),
                        "y": float(300 + 300 * math.sin(angle))
                    }
        else:
            layout = {}
        
        return layout
    
    def filter_by_type(self, node_types: List[str]) -> 'GraphitiVisualizer':
        """
        按类型过滤图
        
        Args:
            node_types: 节点类型列表
            
        Returns:
            新的可视化器实例
        """
        filtered = GraphitiVisualizer()
        
        for node_id, data in self.graph.nodes(data=True):
            if data.get('type') in node_types:
                filtered.graph.add_node(node_id, **data)
        
        for source, target, data in self.graph.edges(data=True):
            if source in filtered.graph and target in filtered.graph:
                filtered.graph.add_edge(source, target, **data)
        
        return filtered
    
    def get_subgraph(self, node_ids: List[str], depth: int = 1) -> 'GraphitiVisualizer':
        """
        获取子图
        
        Args:
            node_ids: 起始节点ID列表
            depth: 深度
            
        Returns:
            新的可视化器实例
        """
        subgraph = GraphitiVisualizer()
        
        # 获取指定节点及其邻居
        nodes_to_include = set(node_ids)
        current_nodes = set(node_ids)
        
        for _ in range(depth):
            next_nodes = set()
            for node in current_nodes:
                if node in self.graph:
                    neighbors = list(self.graph.successors(node)) + list(self.graph.predecessors(node))
                    next_nodes.update(neighbors)
            nodes_to_include.update(next_nodes)
            current_nodes = next_nodes
        
        # 构建子图
        for node_id in nodes_to_include:
            if node_id in self.graph:
                subgraph.graph.add_node(node_id, **self.graph.nodes[node_id])
        
        for source, target, data in self.graph.edges(data=True):
            if source in nodes_to_include and target in nodes_to_include:
                subgraph.graph.add_edge(source, target, **data)
        
        return subgraph
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取图统计信息"""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "node_types": dict(self.graph.nodes(data='type')),
            "density": nx.density(self.graph),
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else False
        }



