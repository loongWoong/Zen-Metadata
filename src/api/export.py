"""
数据导出 API
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import json
import csv
import io
from pathlib import Path

from ..processing.sqlite import SQLiteProcessor
from ..core.graph import GraphStore


router = APIRouter(prefix="/api/export", tags=["export"])

sqlite_processor: Optional[SQLiteProcessor] = None
graph_store: Optional[GraphStore] = None


def set_dependencies(sp: SQLiteProcessor, gs: GraphStore):
    """设置依赖"""
    global sqlite_processor, graph_store
    sqlite_processor = sp
    graph_store = gs


@router.get("/json")
async def export_json():
    """导出为 JSON 格式"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    entities = sqlite_processor.query_entities(limit=100000)
    relationships = sqlite_processor.query_relationships(limit=100000)
    
    data = {
        "entities": entities,
        "relationships": relationships,
        "exported_at": str(Path().absolute()),
        "count": {
            "entities": len(entities),
            "relationships": len(relationships)
        }
    }
    
    json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    
    return StreamingResponse(
        io.BytesIO(json_str.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=zen_metadata_export.json"}
    )


@router.get("/csv/entities")
async def export_entities_csv():
    """导出实体为 CSV 格式"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    entities = sqlite_processor.query_entities(limit=100000)
    
    if not entities:
        raise HTTPException(status_code=404, detail="没有实体数据")
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'id', 'type', 'name', 'description', 'source', 'created_at', 'updated_at'
    ])
    writer.writeheader()
    
    for entity in entities:
        row = {
            'id': entity.get('id', ''),
            'type': entity.get('type', ''),
            'name': entity.get('name', ''),
            'description': entity.get('description', '') or '',
            'source': entity.get('source', ''),
            'created_at': entity.get('created_at', ''),
            'updated_at': entity.get('updated_at', '')
        }
        writer.writerow(row)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=entities.csv"}
    )


@router.get("/csv/relationships")
async def export_relationships_csv():
    """导出关系为 CSV 格式"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    relationships = sqlite_processor.query_relationships(limit=100000)
    
    if not relationships:
        raise HTTPException(status_code=404, detail="没有关系数据")
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'source_id', 'target_id', 'type', 'created_at'
    ])
    writer.writeheader()
    
    for rel in relationships:
        row = {
            'source_id': rel.get('source_id', ''),
            'target_id': rel.get('target_id', ''),
            'type': rel.get('type', ''),
            'created_at': rel.get('created_at', '')
        }
        writer.writerow(row)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relationships.csv"}
    )


@router.get("/graphml")
async def export_graphml():
    """导出为 GraphML 格式"""
    if not graph_store:
        raise HTTPException(status_code=500, detail="图数据库未初始化")
    
    # 查询所有节点和边
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 10000
    """
    result = graph_store.query(query)
    
    # 生成 GraphML
    graphml = ['<?xml version="1.0" encoding="UTF-8"?>']
    graphml.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
    graphml.append('  <graph id="zen_metadata" edgedefault="directed">')
    
    # 添加节点
    node_ids = set()
    for node in result.nodes:
        node_id = node.get('id', str(node))
        if node_id not in node_ids:
            node_ids.add(node_id)
            name = node.get('name', node_id)
            node_type = node.get('type', 'unknown')
            graphml.append(f'    <node id="{node_id}">')
            graphml.append(f'      <data key="name">{name}</data>')
            graphml.append(f'      <data key="type">{node_type}</data>')
            graphml.append('    </node>')
    
    # 添加边
    for edge in result.edges:
        source = edge.get('source', edge.get('source_id', ''))
        target = edge.get('target', edge.get('target_id', ''))
        edge_type = edge.get('type', 'related_to')
        if source and target:
            graphml.append(f'    <edge source="{source}" target="{target}">')
            graphml.append(f'      <data key="type">{edge_type}</data>')
            graphml.append('    </edge>')
    
    graphml.append('  </graph>')
    graphml.append('</graphml>')
    
    return StreamingResponse(
        io.BytesIO('\n'.join(graphml).encode('utf-8')),
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=zen_metadata.graphml"}
    )







