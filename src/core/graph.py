"""
FalkorDB 图数据库连接和操作
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from falkordb import FalkorDB

from .models import MetadataEntity, MetadataRelationship, QueryResult
from .logging_config import get_logger
from .query_builder import CypherQueryBuilder
from .exceptions import GraphStoreException

logger = get_logger("graph")


def _convert_property_value(value: Any) -> Any:
    """
    将属性值转换为FalkorDB支持的类型
    FalkorDB支持: str, int, float, bool, None
    不支持: list, dict, datetime等复杂类型
    
    Args:
        value: 原始值
        
    Returns:
        转换后的值
    """
    if value is None:
        return None
    elif isinstance(value, bool):
        # 布尔值直接返回
        return value
    elif isinstance(value, (int, float)):
        # 数字直接返回
        return value
    elif isinstance(value, str):
        # 字符串直接返回
        return value
    elif isinstance(value, (list, dict)):
        # 将列表和字典转换为JSON字符串
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, datetime):
        # datetime转换为ISO格式字符串
        return value.isoformat()
    elif hasattr(value, '__str__'):
        # Enum或其他有__str__方法的对象，先尝试获取值
        if hasattr(value, 'value'):
            # Enum类型，获取value
            return _convert_property_value(value.value)
        else:
            # 其他类型转换为字符串
            return str(value)
    else:
        # 最后兜底：转换为字符串
        return str(value)


class GraphStore:
    """FalkorDB 图存储管理器"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 password: Optional[str] = None, graph_name: str = "zen_metadata"):
        """
        初始化图存储
        
        Args:
            host: FalkorDB 主机地址
            port: 端口
            password: 密码
            graph_name: 图名称
        """
        logger.info(f"初始化 FalkorDB 连接: {host}:{port}, graph={graph_name}")
        # 使用 FalkorDB API
        db_kwargs = {"host": host, "port": port}
        if password:
            db_kwargs["password"] = password
        try:
            self.db = FalkorDB(**db_kwargs)
            self.graph_name = graph_name
            self.graph = self.db.select_graph(graph_name)
            logger.info(f"FalkorDB 连接成功，图: {graph_name}")
        except Exception as e:
            logger.error(f"FalkorDB 连接失败: {e}", exc_info=True)
            raise GraphStoreException(f"无法连接到 FalkorDB: {e}")
    
    def add_entity(self, entity: MetadataEntity) -> bool:
        """
        添加实体到图数据库
        
        Args:
            entity: 元数据实体
            
        Returns:
            是否成功
        """
        try:
            logger.debug(f"添加实体: id={entity.id}, type={entity.type}, name={entity.name}")
            
            # 构建节点属性 - 所有基本属性也需要转换
            properties = {}
            
            # 转换基本属性
            properties["id"] = _convert_property_value(entity.id)
            properties["type"] = _convert_property_value(entity.type)
            properties["name"] = _convert_property_value(entity.name)
            properties["source"] = _convert_property_value(entity.source)
            properties["created_at"] = _convert_property_value(entity.created_at)
            properties["updated_at"] = _convert_property_value(entity.updated_at)
            
            if entity.description:
                properties["description"] = _convert_property_value(entity.description)
            
            # 添加扩展属性，并转换不支持的类型
            # 注意：避免与基本属性键冲突（如"type"）
            for key, value in entity.properties.items():
                # 避免键冲突：如果扩展属性中有与基本属性同名的键，添加前缀
                if key in properties:
                    new_key = f"prop_{key}"
                    logger.debug(f"属性键冲突，重命名: {key} -> {new_key}")
                    key = new_key
                
                properties[key] = _convert_property_value(value)
            
            # 使用查询构建器创建安全的查询
            query = CypherQueryBuilder.create_node(
                node_type=entity.type,
                properties=properties
            )
            
            logger.debug(f"执行 CREATE 查询: {query[:200]}...")
            result = self.graph.query(query)
            logger.debug(f"实体添加成功: id={entity.id}")
            return True
        except Exception as e:
            logger.error(f"添加实体失败: id={entity.id}, error={e}", exc_info=True)
            return False
    
    def add_relationship(self, relationship: MetadataRelationship) -> bool:
        """
        添加关系到图数据库
        
        Args:
            relationship: 元数据关系
            
        Returns:
            是否成功
        """
        try:
            logger.debug(
                f"添加关系: source_id={relationship.source_id}, "
                f"target_id={relationship.target_id}, type={relationship.type}"
            )
            
            # 构建关系属性
            properties = {}
            properties["created_at"] = _convert_property_value(relationship.created_at)
            
            # 转换扩展属性中不支持的类型
            for key, value in relationship.properties.items():
                # 避免键冲突
                if key in properties:
                    new_key = f"prop_{key}"
                    logger.debug(f"关系属性键冲突，重命名: {key} -> {new_key}")
                    key = new_key
                properties[key] = _convert_property_value(value)
            
            # 使用查询构建器创建安全的查询
            query = CypherQueryBuilder.create_relationship(
                source_id=relationship.source_id,
                target_id=relationship.target_id,
                rel_type=relationship.type,
                properties=properties
            )
            
            logger.debug(f"执行 CREATE 关系查询: {query[:200]}...")
            result = self.graph.query(query)
            success = len(result.result_set) > 0 if hasattr(result, 'result_set') else True
            if success:
                logger.debug(f"关系添加成功: {relationship.source_id} -> {relationship.target_id}")
            return success
        except Exception as e:
            logger.error(
                f"添加关系失败: source_id={relationship.source_id}, "
                f"target_id={relationship.target_id}, error={e}",
                exc_info=True
            )
            return False
    
    def batch_add_entities(self, entities: List[MetadataEntity]) -> int:
        """
        批量添加实体
        
        Args:
            entities: 实体列表
            
        Returns:
            成功添加的数量
        """
        success_count = 0
        for entity in entities:
            if self.add_entity(entity):
                success_count += 1
        return success_count
    
    def batch_add_relationships(self, relationships: List[MetadataRelationship]) -> int:
        """
        批量添加关系
        
        Args:
            relationships: 关系列表
            
        Returns:
            成功添加的数量
        """
        success_count = 0
        for relationship in relationships:
            if self.add_relationship(relationship):
                success_count += 1
        return success_count
    
    def merge_entity(self, entity: MetadataEntity) -> bool:
        """
        合并实体到图数据库（增量更新模式）
        如果实体已存在则更新，不存在则创建
        
        Args:
            entity: 元数据实体
            
        Returns:
            是否成功
        """
        try:
            logger.debug(f"合并实体: id={entity.id}, type={entity.type}")
            
            # 构建节点属性
            properties = {}
            properties["id"] = _convert_property_value(entity.id)
            properties["type"] = _convert_property_value(entity.type)
            properties["name"] = _convert_property_value(entity.name)
            properties["source"] = _convert_property_value(entity.source)
            properties["created_at"] = _convert_property_value(entity.created_at)
            properties["updated_at"] = _convert_property_value(entity.updated_at)
            
            if entity.description:
                properties["description"] = _convert_property_value(entity.description)
            
            # 添加扩展属性
            for key, value in entity.properties.items():
                if key in properties:
                    new_key = f"prop_{key}"
                    key = new_key
                properties[key] = _convert_property_value(value)
            
            # 使用查询构建器创建安全的 MERGE 查询
            query = CypherQueryBuilder.merge_node(
                node_type=entity.type,
                node_id=entity.id,
                properties=properties
            )
            
            logger.debug(f"执行 MERGE 查询: {query[:200]}...")
            result = self.graph.query(query)
            logger.debug(f"实体合并成功: id={entity.id}")
            return True
        except Exception as e:
            logger.error(f"合并实体失败: id={entity.id}, error={e}", exc_info=True)
            return False
    
    def merge_relationship(self, relationship: MetadataRelationship) -> bool:
        """
        合并关系到图数据库（增量更新模式）
        如果关系已存在则更新，不存在则创建
        
        Args:
            relationship: 元数据关系
            
        Returns:
            是否成功
        """
        try:
            logger.debug(
                f"合并关系: source_id={relationship.source_id}, "
                f"target_id={relationship.target_id}, type={relationship.type}"
            )
            
            # 构建关系属性
            properties = {}
            properties["created_at"] = _convert_property_value(relationship.created_at)
            
            for key, value in relationship.properties.items():
                if key in properties:
                    new_key = f"prop_{key}"
                    key = new_key
                properties[key] = _convert_property_value(value)
            
            # 使用查询构建器创建安全的 MERGE 查询
            escaped_source_id = CypherQueryBuilder.escape_string(relationship.source_id)
            escaped_target_id = CypherQueryBuilder.escape_string(relationship.target_id)
            escaped_rel_type = CypherQueryBuilder.escape_label(relationship.type)
            
            # 构建属性字符串
            props_parts = []
            for k, v in properties.items():
                escaped_key = CypherQueryBuilder.escape_label(k)
                if v is None:
                    props_parts.append(f"{escaped_key}: null")
                elif isinstance(v, bool):
                    props_parts.append(f"{escaped_key}: {str(v).lower()}")
                elif isinstance(v, (int, float)):
                    props_parts.append(f"{escaped_key}: {v}")
                else:
                    escaped_value = CypherQueryBuilder.escape_string(str(v))
                    props_parts.append(f"{escaped_key}: '{escaped_value}'")
            props_str = ", ".join(props_parts)
            
            query = f"""
            MATCH (a), (b)
            WHERE a.id = '{escaped_source_id}' AND b.id = '{escaped_target_id}'
            MERGE (a)-[r:{escaped_rel_type}]->(b)
            SET r = {{{props_str}}}
            RETURN r
            """
            
            logger.debug(f"执行 MERGE 关系查询: {query[:200]}...")
            result = self.graph.query(query)
            success = len(result.result_set) > 0 if hasattr(result, 'result_set') else True
            if success:
                logger.debug(f"关系合并成功: {relationship.source_id} -> {relationship.target_id}")
            return success
        except Exception as e:
            logger.error(
                f"合并关系失败: source_id={relationship.source_id}, "
                f"target_id={relationship.target_id}, error={e}",
                exc_info=True
            )
            return False
    
    def batch_merge_entities(self, entities: List[MetadataEntity]) -> int:
        """
        批量合并实体（增量更新模式）
        
        Args:
            entities: 实体列表
            
        Returns:
            成功合并的数量
        """
        success_count = 0
        for entity in entities:
            if self.merge_entity(entity):
                success_count += 1
        return success_count
    
    def batch_merge_relationships(self, relationships: List[MetadataRelationship]) -> int:
        """
        批量合并关系（增量更新模式）
        
        Args:
            relationships: 关系列表
            
        Returns:
            成功合并的数量
        """
        success_count = 0
        for relationship in relationships:
            if self.merge_relationship(relationship):
                success_count += 1
        return success_count
    
    def _process_edge_with_nodes(self, rel_item: Any, source_id: Any, target_id: Any, edges: List[Dict], record_nodes: List, rel_type_override: Optional[str] = None) -> None:
        """处理边对象，使用记录中的节点来推断 source/target
        
        Args:
            rel_item: 关系对象
            source_id: 源节点ID
            target_id: 目标节点ID
            edges: 边列表
            record_nodes: 记录中的节点列表
            rel_type_override: 关系类型覆盖值（如果查询中显式返回了关系类型）
        """
        if not rel_item:
            return
        
        edge_dict = {}
        # 获取属性
        if hasattr(rel_item, 'properties'):
            edge_dict = dict(rel_item.properties) if rel_item.properties else {}
        elif hasattr(rel_item, '__dict__'):
            edge_dict = {k: v for k, v in rel_item.__dict__.items() if not k.startswith('_')}
        
        # 获取关系类型 - 优先使用覆盖值
        rel_type = rel_type_override
        
        if not rel_type:
            # 方法1: 直接访问 type 属性（FalkorDB 关系对象可能使用这个）
            if hasattr(rel_item, 'type'):
                type_val = rel_item.type
                if isinstance(type_val, str) and type_val:
                    rel_type = type_val
                elif isinstance(type_val, (list, tuple)) and type_val:
                    # 如果是列表，取第一个（FalkorDB 可能返回列表）
                    rel_type = str(type_val[0]) if type_val else None
                elif type_val is not None:
                    # 尝试转换为字符串
                    rel_type = str(type_val)
            
            # 方法2: 访问 relation_type 属性
            if not rel_type and hasattr(rel_item, 'relation_type'):
                rel_type = rel_item.relation_type
            
            # 方法3: 从 __dict__ 中查找（包括私有属性）
            if not rel_type and hasattr(rel_item, '__dict__'):
                rel_dict = rel_item.__dict__
                # 检查所有可能的键
                for key in ['type', 'relation_type', '_type', '_relation_type', 'relationship_type']:
                    if key in rel_dict:
                        type_val = rel_dict[key]
                        if isinstance(type_val, str) and type_val:
                            rel_type = type_val
                            break
                        elif isinstance(type_val, (list, tuple)) and type_val:
                            rel_type = str(type_val[0]) if type_val else None
                            if rel_type:
                                break
            
            # 方法4: 从 properties 中查找（某些情况下类型可能存储在properties中）
            if not rel_type and edge_dict:
                for key in ['type', 'relation_type', 'relationship_type']:
                    if key in edge_dict:
                        type_val = edge_dict[key]
                        if isinstance(type_val, str) and type_val:
                            rel_type = type_val
                            break
            
            # 方法5: 尝试从对象的所有属性中查找
            if not rel_type:
                # 获取对象的所有属性
                try:
                    attrs = dir(rel_item)
                    for attr_name in ['type', 'relation_type', 'relationship_type', 'label', 'name', 'rel_type']:
                        if attr_name in attrs:
                            try:
                                attr_val = getattr(rel_item, attr_name)
                                if isinstance(attr_val, str) and attr_val:
                                    rel_type = attr_val
                                    break
                                elif isinstance(attr_val, (list, tuple)) and attr_val:
                                    rel_type = str(attr_val[0]) if attr_val else None
                                    if rel_type:
                                        break
                            except (AttributeError, TypeError):
                                continue
                except Exception:
                    pass
            
            # 方法6: 尝试从字符串表示中提取（最后的手段）
            if not rel_type:
                try:
                    rel_str = str(rel_item)
                    # 尝试从字符串中提取关系类型（如果格式类似 "Edge(type='CONTAINS')"）
                    import re
                    match = re.search(r"type[=:]['\"]?(\w+)['\"]?", rel_str, re.IGNORECASE)
                    if match:
                        rel_type = match.group(1)
                except Exception:
                    pass
        
        # 如果仍然没有找到，使用默认值
        if not rel_type:
            rel_type = 'related_to'
            logger.warning(f"无法提取关系类型，使用默认值 'related_to'")
        
        edge_dict['type'] = rel_type
        
        # 优先使用记录中的节点ID
        if source_id:
            edge_dict['source'] = str(source_id)
        if target_id:
            edge_dict['target'] = str(target_id)
        
        # 如果记录中没有节点ID，尝试从边的 start_node/end_node 获取
        if 'source' not in edge_dict or 'target' not in edge_dict:
            if hasattr(rel_item, 'start_node') and hasattr(rel_item, 'end_node'):
                start_node = rel_item.start_node
                end_node = rel_item.end_node
                
                if 'source' not in edge_dict:
                    source_id_from_edge = None
                    if hasattr(start_node, 'properties') and start_node.properties and 'id' in start_node.properties:
                        source_id_from_edge = start_node.properties['id']
                    elif hasattr(start_node, 'id'):
                        source_id_from_edge = start_node.id
                    if source_id_from_edge:
                        edge_dict['source'] = str(source_id_from_edge)
                
                if 'target' not in edge_dict:
                    target_id_from_edge = None
                    if hasattr(end_node, 'properties') and end_node.properties and 'id' in end_node.properties:
                        target_id_from_edge = end_node.properties['id']
                    elif hasattr(end_node, 'id'):
                        target_id_from_edge = end_node.id
                    if target_id_from_edge:
                        edge_dict['target'] = str(target_id_from_edge)
        
        if 'source' in edge_dict and 'target' in edge_dict:
            edges.append(edge_dict)
            logger.debug(f"添加边: {edge_dict.get('source')} -> {edge_dict.get('target')} ({edge_dict.get('type')})")
        else:
            logger.warning(f"无法提取边的 source/target: rel_item_type={type(rel_item)}")
    
    def query(self, cypher_query: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        执行 Cypher 查询
        
        Args:
            cypher_query: Cypher 查询语句
            params: 查询参数（FalkorDB可能不支持参数化查询，建议使用内联值）
            
        Returns:
            查询结果
        """
        logger.debug(f"执行查询: {cypher_query[:200]}...")
        try:
            # FalkorDB可能不支持参数化查询，如果提供了params，尝试替换查询中的参数
            if params:
                # 将参数内联到查询中
                query = cypher_query
                for key, value in params.items():
                    # 转义字符串值
                    if isinstance(value, str):
                        escaped_value = CypherQueryBuilder.escape_string(value)
                        query = query.replace(f"${key}", f"'{escaped_value}'")
                    elif value is None:
                        query = query.replace(f"${key}", "null")
                    elif isinstance(value, bool):
                        query = query.replace(f"${key}", str(value).lower())
                    else:
                        query = query.replace(f"${key}", str(value))
                cypher_query = query
                logger.debug("已替换查询参数")
            
            # FalkorDB的query方法可能不支持参数，直接传入查询字符串
            result = self.graph.query(cypher_query)
            logger.debug(f"查询执行完成，结果集大小: {len(result.result_set) if hasattr(result, 'result_set') and result.result_set else 0}")
            
            nodes = []
            edges = []
            count_values = []
            
            # 解析查询结果
            if result.result_set:
                logger.debug(f"解析结果集，记录数: {len(result.result_set)}")
                for record in result.result_set:
                    
                    # 检查是否是新的查询格式：[Node, Relationship, Node, rel_type] 或 [Node, Relationship, Node, TYPE(r)]
                    # 如果记录长度>=4，检查最后一个元素是否是关系类型
                    rel_type_from_record = None
                    if len(record) >= 4:
                        last_item = record[-1]
                        # 关系类型通常是字符串，且不是节点或边对象
                        if isinstance(last_item, str) and last_item and not hasattr(last_item, 'labels') and not hasattr(last_item, 'start_node'):
                            # 可能是关系类型（从 TYPE(r) 返回）
                            rel_type_from_record = last_item
                        # 也检查倒数第二个元素（如果记录格式是 [Node, Relationship, Node, rel_type, ...]）
                        elif len(record) >= 3:
                            second_last_item = record[-2] if len(record) > 1 else None
                            if isinstance(second_last_item, str) and second_last_item and not hasattr(second_last_item, 'labels') and not hasattr(second_last_item, 'start_node'):
                                rel_type_from_record = second_last_item
                    
                    # 如果记录格式是 [Node, Relationship, Node, rel_type]，需要检查每个位置
                    # 遍历记录，查找字符串类型的关系类型（排除节点和边对象）
                    if not rel_type_from_record:
                        for item in record:
                            if isinstance(item, str) and item and len(item) > 0:
                                # 检查是否可能是关系类型（不是节点ID或属性值）
                                # 关系类型通常是简单的标识符，不包含特殊字符（除了下划线）
                                if item.replace('_', '').replace('-', '').isalnum() and not item.isdigit():
                                    # 进一步验证：检查是否不是节点ID格式（节点ID可能包含特殊字符）
                                    # 如果这个字符串不在已识别的节点中，可能是关系类型
                                    is_node_id = False
                                    for node_idx, node_item in record_nodes:
                                        if hasattr(node_item, 'properties') and node_item.properties:
                                            node_id = node_item.properties.get('id', '')
                                            if str(node_id) == item:
                                                is_node_id = True
                                                break
                                    if not is_node_id:
                                        rel_type_from_record = item
                                        break
                    
                    # 尝试识别记录格式：通常是 [Node, Edge/Path, Node] 或 [Node, Edge/Path, Node, rel_type]
                    # 先提取记录中的节点，用于推断边的 source/target
                    record_nodes = []
                    record_edges = []
                    
                    # 跳过最后一个元素（可能是关系类型字符串）
                    items_to_check = record[:-1] if rel_type_from_record else record
                    
                    for idx, item in enumerate(items_to_check):
                        if item is None:
                            continue
                        # 识别节点（FalkorDB 节点有 labels 属性）
                        if hasattr(item, 'labels'):
                            record_nodes.append((idx, item))
                        # 识别 Path 对象（路径查询返回的是 Path 对象，包含多个边）
                        elif hasattr(item, '__class__') and 'Path' in str(type(item)):
                            # FalkorDB Path 对象，需要从中提取边
                            record_edges.append((idx, item))
                        # 识别边（可能是单个边或路径列表）
                        elif isinstance(item, (list, tuple)) and item:
                            # 检查是否是边列表
                            if any(hasattr(x, 'type') or hasattr(x, 'relation_type') or 
                                   (hasattr(x, 'start_node') and hasattr(x, 'end_node')) 
                                   for x in item if x is not None):
                                record_edges.append((idx, item))
                        # 识别单个边对象
                        # FalkorDB Edge 对象通常有 type 属性（字符串类型的关系类型）
                        # 或者有 start_node/end_node 属性，或者有 relation_type 属性
                        elif hasattr(item, '__class__') and 'Edge' in str(type(item)):
                            # 通过类型名称识别 Edge 对象
                            record_edges.append((idx, item))
                        elif (hasattr(item, 'start_node') and hasattr(item, 'end_node')) or \
                             hasattr(item, 'relation_type') or \
                             (hasattr(item, 'type') and isinstance(item.type, str) and 
                              not hasattr(item, 'labels')):
                            record_edges.append((idx, item))
                    
                    # 如果记录格式是 [Node, Edge/Path, Node]，使用节点来推断边的 source/target
                    if len(record_nodes) >= 2 and record_edges:
                        source_node = record_nodes[0][1]
                        target_node = record_nodes[-1][1]
                        
                        # 先处理节点（确保节点被添加到 nodes 列表）
                        for node_idx, node_item in record_nodes:
                            node_dict = {}
                            if hasattr(node_item, 'properties'):
                                node_dict = dict(node_item.properties) if node_item.properties else {}
                            elif hasattr(node_item, '__dict__'):
                                node_dict = {k: v for k, v in node_item.__dict__.items() if not k.startswith('_')}
                            
                            # 获取标签（节点类型）
                            if hasattr(node_item, 'labels') and node_item.labels:
                                labels = node_item.labels
                                if isinstance(labels, list) and labels:
                                    node_dict['type'] = labels[0]
                                elif labels:
                                    node_dict['type'] = str(labels)
                            
                            # 确保有id字段
                            if 'id' not in node_dict and hasattr(node_item, 'properties') and node_item.properties:
                                if 'id' in node_item.properties:
                                    node_dict['id'] = node_item.properties['id']
                            
                            if 'id' not in node_dict:
                                if 'name' in node_dict:
                                    node_dict['id'] = str(node_dict['name'])
                                else:
                                    node_dict['id'] = f"node_{len(nodes)}"
                            
                            # 检查是否已存在（避免重复）
                            node_id = str(node_dict.get('id'))
                            if not any(str(n.get('id')) == node_id for n in nodes):
                                nodes.append(node_dict)
                        
                        # 提取源节点ID和目标节点ID
                        source_id = None
                        if hasattr(source_node, 'properties') and source_node.properties and 'id' in source_node.properties:
                            source_id = source_node.properties['id']
                        elif hasattr(source_node, 'id'):
                            source_id = source_node.id
                        
                        target_id = None
                        if hasattr(target_node, 'properties') and target_node.properties and 'id' in target_node.properties:
                            target_id = target_node.properties['id']
                        elif hasattr(target_node, 'id'):
                            target_id = target_node.id
                        
                        # 处理记录中的边
                        for edge_idx, edge_item in record_edges:
                            # 处理 Path 对象
                            if hasattr(edge_item, '__class__') and 'Path' in str(type(edge_item)):
                                # 从 Path 对象中提取边
                                # Path 对象通常有 edges 或 relationships 属性，或者可以迭代
                                path_edges = []
                                
                                # 尝试多种方式访问 Path 中的边
                                if hasattr(edge_item, 'edges'):
                                    path_edges = edge_item.edges if isinstance(edge_item.edges, (list, tuple)) else [edge_item.edges]
                                elif hasattr(edge_item, 'relationships'):
                                    path_edges = edge_item.relationships if isinstance(edge_item.relationships, (list, tuple)) else [edge_item.relationships]
                                elif hasattr(edge_item, 'relationship'):
                                    path_edges = edge_item.relationship if isinstance(edge_item.relationship, (list, tuple)) else [edge_item.relationship]
                                elif hasattr(edge_item, '__iter__'):
                                    # Path 对象可能可以直接迭代，但需要检查迭代的是边还是节点
                                    try:
                                        iter_items = list(edge_item)
                                        # 过滤出边对象
                                        path_edges = [item for item in iter_items 
                                                     if item is not None and 
                                                     (hasattr(item, '__class__') and 'Edge' in str(type(item)) or
                                                      hasattr(item, 'type') or hasattr(item, 'start_node'))]
                                    except Exception as e:
                                        logger.warning(f"无法迭代路径对象: {e}, path_type={type(edge_item)}")
                                        path_edges = []
                                
                                # 处理路径中的每条边
                                for rel_item in path_edges:
                                    if rel_item is None:
                                        continue
                                    self._process_edge_with_nodes(rel_item, source_id, target_id, edges, record_nodes, rel_type_from_record)
                                
                                # 如果路径中没有边，但路径连接了源节点和目标节点，创建一条虚拟边
                                # 这对于路径查询很重要，因为路径可能只包含节点信息
                                if not path_edges and source_id and target_id:
                                    edge_dict = {
                                        'source': str(source_id),
                                        'target': str(target_id),
                                        'type': 'path'  # 标记为路径边
                                    }
                                    edges.append(edge_dict)
                                    logger.debug(f"从路径添加虚拟边: {edge_dict.get('source')} -> {edge_dict.get('target')}")
                            elif isinstance(edge_item, (list, tuple)):
                                # 路径：包含多个边
                                for rel_item in edge_item:
                                    if rel_item is None:
                                        continue
                                    self._process_edge_with_nodes(rel_item, source_id, target_id, edges, record_nodes, rel_type_from_record)
                            else:
                                # 单个边
                                self._process_edge_with_nodes(edge_item, source_id, target_id, edges, record_nodes, rel_type_from_record)
                        
                        # 跳过后续的逐个处理，因为我们已经处理了这条记录
                        continue
                    
                    # 处理记录中的每个字段（原有逻辑，用于处理其他格式）
                    for idx, item in enumerate(record):
                        # 跳过None值
                        if item is None:
                            continue
                        
                        # 处理路径（路径查询返回的是关系列表，如 [r*1..2]）
                        if isinstance(item, (list, tuple)):
                            # 这是一个路径，包含多个关系
                            for path_item in item:
                                if path_item is None:
                                    continue
                                # 将路径中的每个关系对象当作普通关系处理
                                # 使用 _process_edge_with_nodes 函数处理
                                for path_item in item:
                                    if path_item is None:
                                        continue
                                    # 对于路径中的关系，我们需要从关系对象中提取 source/target
                                    # 这里暂时使用 None，让函数自己从关系对象中提取
                                    self._process_edge_with_nodes(path_item, None, None, edges, [], rel_type_from_record)
                                    
                                    # 获取源和目标节点
                                    if hasattr(rel_item, 'start_node') and hasattr(rel_item, 'end_node'):
                                        start_node = rel_item.start_node
                                        end_node = rel_item.end_node
                                        
                                        # 从起始节点提取id
                                        source_id = None
                                        if hasattr(start_node, 'properties') and start_node.properties and 'id' in start_node.properties:
                                            source_id = start_node.properties['id']
                                        elif hasattr(start_node, 'id'):
                                            source_id = start_node.id
                                        
                                        # 从结束节点提取id
                                        target_id = None
                                        if hasattr(end_node, 'properties') and end_node.properties and 'id' in end_node.properties:
                                            target_id = end_node.properties['id']
                                        elif hasattr(end_node, 'id'):
                                            target_id = end_node.id
                                        
                                        if source_id:
                                            edge_dict['source'] = str(source_id)
                                        if target_id:
                                            edge_dict['target'] = str(target_id)
                                    
                                    if 'source' in edge_dict and 'target' in edge_dict:
                                        edges.append(edge_dict)
                                        logger.debug(f"从路径添加边: {edge_dict.get('source')} -> {edge_dict.get('target')} ({edge_dict.get('type')})")
                                
                                process_relationship(path_item)
                            continue
                        
                        # 尝试判断是否为节点对象（FalkorDB节点通常有labels属性）
                        if hasattr(item, 'labels'):
                            # 这是一个节点对象
                            node_dict = {}
                            # 获取属性
                            if hasattr(item, 'properties'):
                                node_dict = dict(item.properties) if item.properties else {}
                            elif hasattr(item, '__dict__'):
                                node_dict = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                            
                            # 获取标签（节点类型）
                            if hasattr(item, 'labels') and item.labels:
                                labels = item.labels
                                if isinstance(labels, list) and labels:
                                    node_dict['type'] = labels[0]
                                elif labels:
                                    node_dict['type'] = str(labels)
                            
                            # 确保有id字段（从properties中获取）
                            if 'id' not in node_dict and hasattr(item, 'properties') and item.properties:
                                if 'id' in item.properties:
                                    node_dict['id'] = item.properties['id']
                            
                            # 如果没有id，尝试使用其他唯一标识或生成一个
                            if 'id' not in node_dict:
                                # 尝试从name或其他字段生成id
                                if 'name' in node_dict:
                                    node_dict['id'] = str(node_dict['name'])
                                else:
                                    # 使用类型和索引生成临时id
                                    node_dict['id'] = f"node_{len(nodes)}"
                            
                            nodes.append(node_dict)
                            logger.debug(f"添加节点: id={node_dict.get('id')}, type={node_dict.get('type')}")
                            continue
                        
                        # 尝试判断是否为关系对象
                        # FalkorDB关系对象最可靠的标识是有start_node和end_node属性
                        # 或者有relation_type属性（某些版本可能使用这个）
                        is_relationship = (
                            (hasattr(item, 'start_node') and hasattr(item, 'end_node')) or
                            hasattr(item, 'relation_type') or
                            (hasattr(item, 'type') and isinstance(item.type, str) and 
                             hasattr(item, 'start_node') and hasattr(item, 'end_node'))
                        )
                        
                        if is_relationship:
                            # 这是一个关系对象
                            edge_dict = {}
                            # 获取属性
                            if hasattr(item, 'properties'):
                                edge_dict = dict(item.properties) if item.properties else {}
                            elif hasattr(item, '__dict__'):
                                edge_dict = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                            
                            # 获取关系类型 - 优先使用从查询结果中提取的类型（从 TYPE(r) 返回）
                            # 同时检查 edge_dict 中是否已经有 rel_type 字段（从查询返回）
                            if rel_type_from_record:
                                edge_dict['type'] = rel_type_from_record
                                edge_dict['rel_type'] = rel_type_from_record  # 也保存到 rel_type 字段
                            elif 'rel_type' in edge_dict:
                                # 如果 edge_dict 中已经有 rel_type（从查询返回），使用它
                                edge_dict['type'] = edge_dict['rel_type']
                            else:
                                # 尝试从关系对象中提取类型
                                # 使用与 _process_edge_with_nodes 相同的逻辑
                                extracted_type = None
                                
                                # 方法1: 直接访问 type 属性
                                if hasattr(item, 'type'):
                                    type_val = item.type
                                    if isinstance(type_val, str) and type_val:
                                        extracted_type = type_val
                                    elif isinstance(type_val, (list, tuple)) and type_val:
                                        extracted_type = str(type_val[0]) if type_val else None
                                    elif type_val is not None:
                                        extracted_type = str(type_val)
                                
                                # 方法2: 访问 relation_type 属性
                                if not extracted_type and hasattr(item, 'relation_type'):
                                    extracted_type = item.relation_type
                                
                                # 方法3: 从 __dict__ 中查找
                                if not extracted_type and hasattr(item, '__dict__'):
                                    item_dict = item.__dict__
                                    for key in ['type', 'relation_type', '_type', '_relation_type']:
                                        if key in item_dict:
                                            type_val = item_dict[key]
                                            if isinstance(type_val, str) and type_val:
                                                extracted_type = type_val
                                                break
                                            elif isinstance(type_val, (list, tuple)) and type_val:
                                                extracted_type = str(type_val[0]) if type_val else None
                                                if extracted_type:
                                                    break
                                
                                # 方法4: 从 properties 中查找
                                if not extracted_type and edge_dict:
                                    for key in ['type', 'relation_type', 'relationship_type']:
                                        if key in edge_dict:
                                            type_val = edge_dict[key]
                                            if isinstance(type_val, str) and type_val:
                                                extracted_type = type_val
                                                break
                                
                                # 如果仍然没有找到，使用默认值
                                edge_dict['type'] = extracted_type if extracted_type else 'related_to'
                                
                                # 记录调试信息（如果使用默认值）
                                if not extracted_type:
                                    logger.warning(f"无法从对象提取关系类型，使用默认值: item_type={type(item)}")
                            
                            # 获取源和目标节点
                            if hasattr(item, 'start_node') and hasattr(item, 'end_node'):
                                start_node = item.start_node
                                end_node = item.end_node
                                
                                # 从起始节点提取id
                                source_id = None
                                if hasattr(start_node, 'properties') and start_node.properties and 'id' in start_node.properties:
                                    source_id = start_node.properties['id']
                                elif hasattr(start_node, 'id'):
                                    source_id = start_node.id
                                elif hasattr(start_node, 'labels') and hasattr(start_node, 'properties'):
                                    # 尝试从properties中获取id
                                    if start_node.properties and 'id' in start_node.properties:
                                        source_id = start_node.properties['id']
                                
                                # 从结束节点提取id
                                target_id = None
                                if hasattr(end_node, 'properties') and end_node.properties and 'id' in end_node.properties:
                                    target_id = end_node.properties['id']
                                elif hasattr(end_node, 'id'):
                                    target_id = end_node.id
                                elif hasattr(end_node, 'labels') and hasattr(end_node, 'properties'):
                                    # 尝试从properties中获取id
                                    if end_node.properties and 'id' in end_node.properties:
                                        target_id = end_node.properties['id']
                                
                                if source_id:
                                    edge_dict['source'] = str(source_id)
                                if target_id:
                                    edge_dict['target'] = str(target_id)
                            
                            if 'source' in edge_dict and 'target' in edge_dict:
                                edges.append(edge_dict)
                                logger.debug(f"添加边: {edge_dict.get('source')} -> {edge_dict.get('target')} ({edge_dict.get('type')})")
                            else:
                                logger.warning(f"无法提取边的 source/target: item_type={type(item)}")
                            continue
                        
                        # 字典格式（可能是已经解析的节点或关系）
                        if isinstance(item, dict):
                            if 'id' in item and ('type' in item or 'labels' in item):
                                nodes.append(item)
                            elif 'source' in item and 'target' in item:
                                edges.append(item)
                            continue
                        
                        # 数值（COUNT查询结果或其他数值）
                        if isinstance(item, (int, float)):
                            count_values.append(item)
                            logger.debug(f"找到数值（COUNT结果）: {item}")
                            continue
                        
                        # 字符串或其他类型（可能是属性值，不是节点或关系）
                        # 这些值通常来自RETURN语句中的属性访问，如 RETURN n.name
                        # 在这种情况下，我们不需要处理它们，因为它们不是节点或关系
            
            logger.debug(f"查询完成: nodes={len(nodes)}, edges={len(edges)}, count_values={len(count_values)}")
            
            # 构建统计信息
            stats = {"result_count": len(result.result_set) if result.result_set else 0}
            if count_values:
                stats["count_value"] = count_values[0] if len(count_values) == 1 else count_values
            
            return QueryResult(
                nodes=nodes,
                edges=edges,
                statistics=stats
            )
        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            return QueryResult()
    
    def find_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        查找实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体信息或None
        """
        query = CypherQueryBuilder.match_node(node_id=entity_id) + " RETURN n"
        result = self.query(query)
        return result.nodes[0] if result.nodes else None
    
    def get_entity_relationships(self, entity_id: str, 
                                relationship_type: Optional[str] = None) -> QueryResult:
        """
        获取实体的关系
        
        Args:
            entity_id: 实体ID
            relationship_type: 关系类型（可选）
            
        Returns:
            查询结果
        """
        match_clause = CypherQueryBuilder.match_node(node_id=entity_id, alias="n")
        if relationship_type:
            escaped_type = CypherQueryBuilder.escape_label(relationship_type)
            query = f"{match_clause}-[r:{escaped_type}]->(m) RETURN n, r, m, TYPE(r) as rel_type"
        else:
            query = f"{match_clause}-[r]->(m) RETURN n, r, m, TYPE(r) as rel_type"
        
        return self.query(query)
    
    def delete_entity(self, entity_id: str) -> bool:
        """
        删除实体及其所有关系
        
        Args:
            entity_id: 实体ID
            
        Returns:
            是否成功
        """
        try:
            match_clause = CypherQueryBuilder.match_node(node_id=entity_id, alias="n")
            query = f"{match_clause} DETACH DELETE n"
            self.graph.query(query)
            logger.debug(f"删除实体成功: id={entity_id}")
            return True
        except Exception as e:
            logger.error(f"删除实体失败: id={entity_id}, error={e}", exc_info=True)
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图统计信息
        
        Returns:
            统计信息
        """
        logger.debug("获取图统计信息")
        node_count_query = """
        MATCH (n)
        RETURN count(n) as node_count
        """
        
        edge_count_query = """
        MATCH ()-[r]->()
        RETURN count(r) as edge_count
        """
        
        node_result = self.query(node_count_query)
        edge_result = self.query(edge_count_query)
        
        # 使用count_value而不是result_count
        node_count = node_result.statistics.get("count_value", 0)
        edge_count = edge_result.statistics.get("count_value", 0)
        
        logger.debug(f"统计信息: nodes={node_count}, edges={edge_count}")
        return {
            "node_count": node_count,
            "edge_count": edge_count,
        }
    
    def close(self):
        """关闭连接"""
        logger.info("关闭 FalkorDB 连接")
        # FalkorDB connection is managed internally, no explicit close needed
        pass


