"""
可视化增强API
支持图谱分析、仪表盘数据、代理管理
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from ..core.graph import GraphStore
from ..processing.sqlite import SQLiteProcessor
import networkx as nx

router = APIRouter(prefix="/api/visualization", tags=["visualization"])

# 全局依赖
graph_store: Optional[GraphStore] = None
sqlite_processor: Optional[SQLiteProcessor] = None


def set_dependencies(gs: Optional[GraphStore] = None, sp: Optional[SQLiteProcessor] = None):
    """设置依赖"""
    global graph_store, sqlite_processor
    graph_store = gs
    sqlite_processor = sp


class GraphAnalysisRequest(BaseModel):
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    depth: int = 1
    analysis_type: str = "centrality"  # centrality, community, path


@router.get("/analysis/centrality")
async def get_centrality_analysis(
    entity_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    top_n: int = Query(10, ge=1, le=100),
):
    """获取中心性分析结果"""
    if not graph_store:
        raise HTTPException(status_code=500, detail="图数据库未初始化")
    
    try:
        
        # 构建查询
        if entity_id:
            query = f"MATCH (n)-[r*1..3]-(m) WHERE id(n) = {entity_id} RETURN n, r, m"
        elif entity_type:
            query = f"MATCH (n)-[r*1..3]-(m) WHERE n.type = '{entity_type}' RETURN n, r, m"
        else:
            query = "MATCH (n)-[r*1..3]-(m) RETURN n, r, m LIMIT 1000"
        
        results = graph_store.query(query)
        
        # 构建NetworkX图
        G = nx.Graph()
        nodes = []
        edges = []
        
        for result in results:
            if 'n' in result:
                node = result['n']
                node_id = str(node.get('id', node.get('_id', '')))
                G.add_node(node_id, **node)
                nodes.append(node)
            
            if 'r' in result and 'm' in result:
                source = str(result.get('n', {}).get('id', result.get('n', {}).get('_id', '')))
                target = str(result['m'].get('id', result['m'].get('_id', '')))
                G.add_edge(source, target)
                edges.append({
                    'source': source,
                    'target': target,
                    'type': result['r'].get('type', 'related_to'),
                })
        
        # 计算中心性
        degree_centrality = nx.degree_centrality(G)
        betweenness_centrality = nx.betweenness_centrality(G)
        closeness_centrality = nx.closeness_centrality(G)
        
        # 组合结果
        centrality_data = []
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            centrality_data.append({
                'id': node_id,
                'label': node_data.get('name', node_data.get('label', node_id)),
                'type': node_data.get('type', 'unknown'),
                'degree': degree_centrality.get(node_id, 0),
                'betweenness': betweenness_centrality.get(node_id, 0),
                'closeness': closeness_centrality.get(node_id, 0),
            })
        
        # 排序并返回top_n
        centrality_data.sort(key=lambda x: x['degree'], reverse=True)
        
        return {
            'data': centrality_data[:top_n],
            'total': len(centrality_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analysis/community")
async def get_community_detection(
    entity_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
):
    """获取社区检测结果"""
    if not graph_store:
        raise HTTPException(status_code=500, detail="图数据库未初始化")
    
    try:
        
        # 构建查询
        if entity_id:
            query = f"MATCH (n)-[r*1..3]-(m) WHERE id(n) = {entity_id} RETURN n, r, m"
        elif entity_type:
            query = f"MATCH (n)-[r*1..3]-(m) WHERE n.type = '{entity_type}' RETURN n, r, m"
        else:
            query = "MATCH (n)-[r*1..3]-(m) RETURN n, r, m LIMIT 1000"
        
        results = graph_store.query(query)
        
        # 构建NetworkX图
        G = nx.Graph()
        for result in results:
            if 'n' in result:
                node = result['n']
                node_id = str(node.get('id', node.get('_id', '')))
                G.add_node(node_id, **node)
            
            if 'r' in result and 'm' in result:
                source = str(result.get('n', {}).get('id', result.get('n', {}).get('_id', '')))
                target = str(result['m'].get('id', result['m'].get('_id', '')))
                G.add_edge(source, target)
        
        # 社区检测
        communities = list(nx.community.greedy_modularity_communities(G))
        
        community_data = []
        for i, community in enumerate(communities):
            nodes = [{'id': str(node_id), **G.nodes[node_id]} for node_id in community]
            community_data.append({
                'id': i,
                'nodes': nodes,
                'size': len(nodes),
            })
        
        return {
            'communities': community_data,
            'count': len(community_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"社区检测失败: {str(e)}")


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(role: Optional[str] = Query(None)):
    """获取仪表盘指标数据"""
    try:
        if not sqlite_processor:
            # 返回默认值
            stats = {
                'entity_count': 0,
                'relationship_count': 0,
                'source_count': 0,
                'entity_type_count': 0,
            }
        else:
            stats = sqlite_processor.get_statistics()
        
        # 根据角色返回不同的指标
        metrics = {
            'entity_count': stats.get('entity_count', 0),
            'relationship_count': stats.get('relationship_count', 0),
            'source_count': stats.get('source_count', 0),
            'entity_type_count': stats.get('entity_type_count', 0),
        }
        
        if role == 'data_governance':
            # 添加质量相关指标
            metrics['quality_score'] = 85.5  # 示例值
            metrics['high_risk_count'] = 12  # 示例值
        
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


@router.get("/agents")
async def list_agents():
    """列出所有采集代理"""
    # 这里应该从数据库或配置中读取代理信息
    # 目前返回模拟数据
    return {
        'agents': [
            {
                'id': 'agent_1',
                'name': '主节点采集代理',
                'type': 'lightweight',
                'status': 'running',
                'host': '192.168.1.100',
                'port': 8080,
                'last_heartbeat': '2024-01-01T12:00:00Z',
                'config': {
                    'collector_types': ['filesystem', 'code'],
                    'frequency': 3600,
                },
            },
        ],
        'count': 1,
    }


@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """启动采集代理"""
    # 这里应该实际启动代理
    return {'success': True, 'message': f'代理 {agent_id} 已启动'}


@router.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """停止采集代理"""
    # 这里应该实际停止代理
    return {'success': True, 'message': f'代理 {agent_id} 已停止'}


@router.put("/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, config: Dict[str, Any]):
    """更新代理配置"""
    # 这里应该实际更新代理配置
    return {'success': True, 'message': f'代理 {agent_id} 配置已更新'}

