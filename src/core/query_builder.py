"""
安全的 Cypher 查询构建器
"""
from typing import Optional, List, Dict, Any
from .exceptions import GraphStoreException


class CypherQueryBuilder:
    """安全的 Cypher 查询构建器，防止 SQL 注入"""
    
    @staticmethod
    def escape_string(value: str) -> str:
        """
        转义字符串值，防止注入攻击
        
        Args:
            value: 要转义的字符串
            
        Returns:
            转义后的字符串
        """
        if not isinstance(value, str):
            value = str(value)
        # 转义反斜杠和单引号
        return value.replace("\\", "\\\\").replace("'", "\\'")
    
    @staticmethod
    def escape_label(label: str) -> str:
        """
        转义标签（节点类型或关系类型）
        
        Args:
            label: 标签名称
            
        Returns:
            转义后的标签
        """
        if not isinstance(label, str):
            label = str(label)
        # 标签通常只包含字母、数字和下划线，但为了安全还是转义特殊字符
        return label.replace(":", "\\:").replace(" ", "_")
    
    @staticmethod
    def match_node(node_id: Optional[str] = None, 
                   node_type: Optional[str] = None,
                   alias: str = "n",
                   properties: Optional[Dict[str, Any]] = None) -> str:
        """
        构建节点匹配查询
        
        Args:
            node_id: 节点ID
            node_type: 节点类型（标签）
            alias: 节点别名
            properties: 节点属性
            
        Returns:
            MATCH 查询字符串
        """
        if node_type:
            escaped_type = CypherQueryBuilder.escape_label(node_type)
            match_clause = f"MATCH ({alias}:{escaped_type}"
        else:
            match_clause = f"MATCH ({alias}"
        
        # 构建属性条件
        conditions = []
        if node_id:
            escaped_id = CypherQueryBuilder.escape_string(node_id)
            conditions.append(f"id: '{escaped_id}'")
        
        if properties:
            for key, value in properties.items():
                escaped_key = CypherQueryBuilder.escape_label(key)
                if isinstance(value, str):
                    escaped_value = CypherQueryBuilder.escape_string(value)
                    conditions.append(f"{escaped_key}: '{escaped_value}'")
                elif value is None:
                    conditions.append(f"{escaped_key}: null")
                elif isinstance(value, bool):
                    conditions.append(f"{escaped_key}: {str(value).lower()}")
                else:
                    conditions.append(f"{escaped_key}: {value}")
        
        if conditions:
            match_clause += " {" + ", ".join(conditions) + "}"
        
        match_clause += ")"
        return match_clause
    
    @staticmethod
    def create_node(node_type: str,
                   properties: Dict[str, Any],
                   alias: str = "n") -> str:
        """
        构建节点创建查询
        
        Args:
            node_type: 节点类型
            properties: 节点属性
            alias: 节点别名
            
        Returns:
            CREATE 查询字符串
        """
        escaped_type = CypherQueryBuilder.escape_label(node_type)
        
        # 构建属性字符串
        props_parts = []
        for key, value in properties.items():
            escaped_key = CypherQueryBuilder.escape_label(key)
            if value is None:
                props_parts.append(f"{escaped_key}: null")
            elif isinstance(value, bool):
                props_parts.append(f"{escaped_key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                props_parts.append(f"{escaped_key}: {value}")
            else:
                escaped_value = CypherQueryBuilder.escape_string(str(value))
                props_parts.append(f"{escaped_key}: '{escaped_value}'")
        
        props_str = ", ".join(props_parts)
        return f"CREATE ({alias}:{escaped_type} {{{props_str}}})"
    
    @staticmethod
    def create_relationship(source_id: str,
                           target_id: str,
                           rel_type: str,
                           properties: Optional[Dict[str, Any]] = None) -> str:
        """
        构建关系创建查询
        
        Args:
            source_id: 源节点ID
            target_id: 目标节点ID
            rel_type: 关系类型
            properties: 关系属性
            
        Returns:
            CREATE 查询字符串
        """
        escaped_source_id = CypherQueryBuilder.escape_string(source_id)
        escaped_target_id = CypherQueryBuilder.escape_string(target_id)
        escaped_rel_type = CypherQueryBuilder.escape_label(rel_type)
        
        # 构建关系属性
        rel_props = ""
        if properties:
            props_parts = []
            for key, value in properties.items():
                escaped_key = CypherQueryBuilder.escape_label(key)
                if value is None:
                    props_parts.append(f"{escaped_key}: null")
                elif isinstance(value, bool):
                    props_parts.append(f"{escaped_key}: {str(value).lower()}")
                elif isinstance(value, (int, float)):
                    props_parts.append(f"{escaped_key}: {value}")
                else:
                    escaped_value = CypherQueryBuilder.escape_string(str(value))
                    props_parts.append(f"{escaped_key}: '{escaped_value}'")
            rel_props = " {" + ", ".join(props_parts) + "}"
        
        return f"""
        MATCH (a), (b)
        WHERE a.id = '{escaped_source_id}' AND b.id = '{escaped_target_id}'
        CREATE (a)-[r:{escaped_rel_type}{rel_props}]->(b)
        RETURN r
        """
    
    @staticmethod
    def merge_node(node_type: str,
                  node_id: str,
                  properties: Dict[str, Any],
                  alias: str = "n") -> str:
        """
        构建节点合并查询（MERGE）
        
        Args:
            node_type: 节点类型
            node_id: 节点ID
            properties: 节点属性
            alias: 节点别名
            
        Returns:
            MERGE 查询字符串
        """
        escaped_type = CypherQueryBuilder.escape_label(node_type)
        escaped_id = CypherQueryBuilder.escape_string(node_id)
        
        # 构建属性字符串
        props_parts = []
        for key, value in properties.items():
            escaped_key = CypherQueryBuilder.escape_label(key)
            if value is None:
                props_parts.append(f"{escaped_key}: null")
            elif isinstance(value, bool):
                props_parts.append(f"{escaped_key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                props_parts.append(f"{escaped_key}: {value}")
            else:
                escaped_value = CypherQueryBuilder.escape_string(str(value))
                props_parts.append(f"{escaped_key}: '{escaped_value}'")
        
        props_str = ", ".join(props_parts)
        return f"MERGE ({alias}:{escaped_type} {{id: '{escaped_id}'}}) SET {alias} = {{{props_str}}}"


