"""
基本使用示例
"""
from src.collectors.filesystem import FileSystemCollector
from src.collectors.code import CodeMetadataCollector
from src.core.graph import GraphStore
from src.processing.sqlite import SQLiteProcessor
from src.visualization.graphiti import GraphitiVisualizer


def example_filesystem_collection():
    """文件系统采集示例"""
    print("=== 文件系统元数据采集示例 ===")
    
    collector = FileSystemCollector(
        scan_paths=["."],
        source="example_filesystem",
        config={
            "exclude_patterns": [".git", "__pycache__", "node_modules"],
            "max_depth": 3
        }
    )
    
    result = collector.collect()
    print(f"采集到 {len(result.entities)} 个实体")
    print(f"采集到 {len(result.relationships)} 个关系")
    
    if result.errors:
        print(f"错误: {result.errors}")
    
    return result


def example_code_collection():
    """代码元数据采集示例"""
    print("\n=== 代码元数据采集示例 ===")
    
    collector = CodeMetadataCollector(
        source_path="src",
        source="example_code",
        languages=["python"],
        config={
            "exclude_patterns": ["__pycache__", ".git"]
        }
    )
    
    result = collector.collect()
    print(f"采集到 {len(result.entities)} 个实体")
    print(f"采集到 {len(result.relationships)} 个关系")
    
    # 显示一些实体
    for entity in result.entities[:5]:
        print(f"  - {entity.type}: {entity.name}")
    
    return result


def example_graph_storage():
    """图数据库存储示例"""
    print("\n=== 图数据库存储示例 ===")
    
    # 初始化图存储
    graph_store = GraphStore(
        host="localhost",
        port=6379,
        graph_name="zen_metadata_example"
    )
    
    # 采集文件系统元数据
    fs_result = example_filesystem_collection()
    
    # 存储到图数据库
    entity_count = graph_store.batch_add_entities(fs_result.entities)
    rel_count = graph_store.batch_add_relationships(fs_result.relationships)
    
    print(f"存储了 {entity_count} 个实体")
    print(f"存储了 {rel_count} 个关系")
    
    # 查询统计
    stats = graph_store.get_statistics()
    print(f"图统计: {stats}")
    
    # 查询示例
    query_result = graph_store.query("""
        MATCH (n)-[r]->(m)
        RETURN n.name, type(r), m.name
        LIMIT 10
    """)
    print(f"查询结果: {len(query_result.nodes)} 个节点")
    
    graph_store.close()


def example_sqlite_storage():
    """SQLite 存储示例"""
    print("\n=== SQLite 存储示例 ===")
    
    processor = SQLiteProcessor("data/example.db")
    
    # 采集代码元数据
    code_result = example_code_collection()
    
    # 存储
    for entity in code_result.entities:
        processor.store_entity(entity)
    
    for relationship in code_result.relationships:
        processor.store_relationship(relationship)
    
    # 查询
    entities = processor.query_entities(entity_type="function", limit=10)
    print(f"查询到 {len(entities)} 个函数实体")
    
    # 统计
    stats = processor.get_statistics()
    print(f"统计信息: {stats}")
    
    processor.close()


def example_visualization():
    """可视化示例"""
    print("\n=== 可视化示例 ===")
    
    graph_store = GraphStore(
        host="localhost",
        port=6379,
        graph_name="zen_metadata_example"
    )
    
    # 查询数据
    query_result = graph_store.query("""
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 50
    """)
    
    # 创建可视化器
    visualizer = GraphitiVisualizer()
    visualizer.load_from_query_result(query_result)
    
    # 转换为 Graphiti 格式
    graph_data = visualizer.to_graphiti_format()
    print(f"可视化数据: {len(graph_data['nodes'])} 个节点, {len(graph_data['edges'])} 条边")
    
    # 获取布局
    layout = visualizer.get_layout(layout_type="spring")
    print(f"布局计算完成: {len(layout)} 个节点位置")
    
    # 获取统计
    stats = visualizer.get_statistics()
    print(f"图统计: {stats}")
    
    graph_store.close()


if __name__ == "__main__":
    # 运行示例
    example_filesystem_collection()
    example_code_collection()
    # example_graph_storage()  # 需要 FalkorDB 运行
    example_sqlite_storage()
    # example_visualization()  # 需要 FalkorDB 运行







