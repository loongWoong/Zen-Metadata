"""
数据治理核心服务模块
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import json
import re


class TagCategory(str, Enum):
    """标签分类"""
    BUSINESS = "业务域"  # 销售、财务、运营、风控等
    TECHNICAL = "技术栈"  # 表、视图、API、Topic、文档
    SENSITIVITY = "数据敏感度"  # 公开、内部、受限、机密
    LIFECYCLE = "生命周期"  # 开发、测试、生产、归档
    DATA_QUALITY = "数据质量"  # 质量相关标签
    COMPLIANCE = "合规"  # 合规相关标签


class Tag(BaseModel):
    """标签模型"""
    id: str = Field(..., description="唯一标识符")
    name: str = Field(..., description="标签名称")
    category: str = Field(..., description="标签分类")
    description: Optional[str] = Field(None, description="描述")
    color: str = Field(default="#808080", description="UI颜色")
    version: int = Field(default=1, description="版本号")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = Field(None, description="创建者")


class EntityTag(BaseModel):
    """实体标签关联"""
    id: str = Field(..., description="唯一标识符")
    entity_id: str = Field(..., description="实体ID")
    tag_id: str = Field(..., description="标签ID")
    user_id: Optional[str] = Field(None, description="创建者")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度（自动标签）")
    is_auto: bool = Field(default=False, description="是否自动标签")
    created_at: datetime = Field(default_factory=datetime.now)


class DataStandardType(str, Enum):
    """数据标准类型"""
    NAMING = "naming"  # 命名规范
    FORMAT = "format"  # 格式规范
    QUALITY = "quality"  # 质量规范
    RELATIONSHIP = "relationship"  # 关系规范


class DataStandard(BaseModel):
    """数据标准"""
    id: str = Field(..., description="唯一标识符")
    name: str = Field(..., description="标准名称")
    type: str = Field(..., description="标准类型")
    entity_type: Optional[str] = Field(None, description="适用的实体类型")
    rule: Dict[str, Any] = Field(..., description="规则定义")
    description: Optional[str] = Field(None, description="描述")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = Field(None, description="创建者")


class StandardViolation(BaseModel):
    """标准违规项"""
    id: str = Field(..., description="唯一标识符")
    entity_id: str = Field(..., description="实体ID")
    standard_id: str = Field(..., description="标准ID")
    violation_type: str = Field(..., description="违规类型")
    message: str = Field(..., description="违规信息")
    severity: str = Field(default="medium", description="严重程度")
    fix_suggestion: Optional[str] = Field(None, description="修复建议")
    status: str = Field(default="open", description="状态：open, fixed, ignored")
    created_at: datetime = Field(default_factory=datetime.now)
    fixed_at: Optional[datetime] = Field(None, description="修复时间")


class TagService:
    """标签服务"""
    
    def __init__(self, sqlite_processor, graph_store=None):
        self.sqlite = sqlite_processor
        self.graph = graph_store
    
    def create_tag(self, tag: Tag) -> Tag:
        """创建标签"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            INSERT INTO tags (id, name, category, description, color, version, created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tag.id, tag.name, tag.category, tag.description, tag.color,
            tag.version, tag.created_at.isoformat(), tag.updated_at.isoformat(), tag.created_by
        ))
        self.sqlite.conn.commit()
        return tag
    
    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """获取标签"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        # 确保datetime字段正确解析
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return Tag(**data)
    
    def list_tags(self, category: Optional[str] = None) -> List[Tag]:
        """列出标签"""
        cursor = self.sqlite.conn.cursor()
        if category:
            cursor.execute("SELECT * FROM tags WHERE category = ? ORDER BY name", (category,))
        else:
            cursor.execute("SELECT * FROM tags ORDER BY category, name")
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        tags = []
        for row in rows:
            data = dict(zip(columns, row))
            # 确保datetime字段正确解析
            if isinstance(data.get('created_at'), str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if isinstance(data.get('updated_at'), str):
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            tags.append(Tag(**data))
        return tags
    
    def update_tag(self, tag_id: str, updates: Dict[str, Any]) -> Optional[Tag]:
        """更新标签"""
        updates['updated_at'] = datetime.now().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [tag_id]
        
        cursor = self.sqlite.conn.cursor()
        cursor.execute(f"UPDATE tags SET {set_clause} WHERE id = ?", values)
        self.sqlite.conn.commit()
        
        if cursor.rowcount > 0:
            return self.get_tag(tag_id)
        return None
    
    def delete_tag(self, tag_id: str) -> bool:
        """删除标签"""
        cursor = self.sqlite.conn.cursor()
        # 先删除实体标签关联
        cursor.execute("DELETE FROM entity_tags WHERE tag_id = ?", (tag_id,))
        # 再删除标签
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self.sqlite.conn.commit()
        return cursor.rowcount > 0
    
    def add_entity_tag(self, entity_tag: EntityTag) -> EntityTag:
        """为实体添加标签"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            INSERT INTO entity_tags (id, entity_id, tag_id, user_id, confidence, is_auto, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_tag.id, entity_tag.entity_id, entity_tag.tag_id,
            entity_tag.user_id, entity_tag.confidence, entity_tag.is_auto,
            entity_tag.created_at.isoformat()
        ))
        self.sqlite.conn.commit()
        return entity_tag
    
    def remove_entity_tag(self, entity_id: str, tag_id: str) -> bool:
        """移除实体标签"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("DELETE FROM entity_tags WHERE entity_id = ? AND tag_id = ?", (entity_id, tag_id))
        self.sqlite.conn.commit()
        return cursor.rowcount > 0
    
    def get_entity_tags(self, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体的标签"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name, t.category, t.description, t.color, t.version,
                   et.confidence, et.is_auto, et.created_at as tagged_at, et.user_id
            FROM entity_tags et
            JOIN tags t ON et.tag_id = t.id
            WHERE et.entity_id = ?
            ORDER BY et.created_at DESC
        """, (entity_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def batch_get_entity_tags(self, entity_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """批量获取多个实体的标签"""
        if not entity_ids:
            return {}
        
        cursor = self.sqlite.conn.cursor()
        # 使用IN子句批量查询，避免N+1查询问题
        placeholders = ','.join(['?'] * len(entity_ids))
        cursor.execute(f"""
            SELECT et.entity_id, t.id, t.name, t.category, t.description, t.color, t.version,
                   et.confidence, et.is_auto, et.created_at as tagged_at, et.user_id
            FROM entity_tags et
            JOIN tags t ON et.tag_id = t.id
            WHERE et.entity_id IN ({placeholders})
            ORDER BY et.entity_id, et.created_at DESC
        """, entity_ids)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # 按entity_id分组
        result: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            row_dict = dict(zip(columns, row))
            entity_id = row_dict['entity_id']
            if entity_id not in result:
                result[entity_id] = []
            # 移除entity_id字段，因为它是分组的key
            tag_info = {k: v for k, v in row_dict.items() if k != 'entity_id'}
            result[entity_id].append(tag_info)
        
        # 确保所有请求的entity_id都在结果中（即使没有标签）
        for entity_id in entity_ids:
            if entity_id not in result:
                result[entity_id] = []
        
        return result
    
    def get_tagged_entities(self, tag_id: str, limit: int = 100) -> List[str]:
        """获取带标签的实体ID列表"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT entity_id FROM entity_tags WHERE tag_id = ? LIMIT ?
        """, (tag_id, limit))
        return [row[0] for row in cursor.fetchall()]
    
    def recommend_tags(self, entity_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """推荐标签（基于相似实体和属性）"""
        # 获取实体信息
        entities = self.sqlite.query_entities(limit=10000)
        entity = next((e for e in entities if e.get('id') == entity_id), None)
        if not entity:
            return []
        
        recommendations = []
        
        # 1. 基于实体属性推荐
        entity_type = entity.get('type', '')
        source = entity.get('source', '')
        name = entity.get('name', '').lower()
        
        # 查找相似实体的标签
        similar_entities = [
            e for e in entities
            if e.get('id') != entity_id
            and (e.get('type') == entity_type or e.get('source') == source)
        ]
        
        # 统计相似实体的标签
        tag_counts = {}
        for similar in similar_entities[:100]:  # 限制数量
            tags = self.get_entity_tags(similar.get('id'))
            for tag_info in tags:
                tag_id = tag_info.get('id')
                if tag_id:
                    tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1
        
        # 转换为推荐列表
        all_tags = self.list_tags()
        for tag in all_tags:
            count = tag_counts.get(tag.id, 0)
            if count > 0:
                confidence = min(0.9, 0.5 + count * 0.1)
                tag_dict = tag.dict() if hasattr(tag, 'dict') else {
                    'id': tag.id,
                    'name': tag.name,
                    'category': tag.category,
                    'description': tag.description,
                    'color': tag.color,
                    'version': tag.version
                }
                recommendations.append({
                    'tag': tag_dict,
                    'confidence': confidence,
                    'reason': f'相似实体中有{count}个使用了此标签'
                })
        
        # 按置信度排序
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        return recommendations[:limit]


class StandardService:
    """数据标准服务"""
    
    def __init__(self, sqlite_processor):
        self.sqlite = sqlite_processor
    
    def create_standard(self, standard: DataStandard) -> DataStandard:
        """创建数据标准"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            INSERT INTO data_standards (id, name, type, entity_type, rule, description, enabled, created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            standard.id, standard.name, standard.type, standard.entity_type,
            json.dumps(standard.rule), standard.description, standard.enabled,
            standard.created_at.isoformat(), standard.updated_at.isoformat(), standard.created_by
        ))
        self.sqlite.conn.commit()
        return standard
    
    def get_standard(self, standard_id: str) -> Optional[DataStandard]:
        """获取数据标准"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("SELECT * FROM data_standards WHERE id = ?", (standard_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))
        if isinstance(data.get('rule'), str):
            data['rule'] = json.loads(data['rule'])
        return DataStandard(**data)
    
    def list_standards(self, standard_type: Optional[str] = None, entity_type: Optional[str] = None) -> List[DataStandard]:
        """列出数据标准"""
        cursor = self.sqlite.conn.cursor()
        query = "SELECT * FROM data_standards WHERE 1=1"
        params = []
        
        if standard_type:
            query += " AND type = ?"
            params.append(standard_type)
        if entity_type:
            query += " AND (entity_type = ? OR entity_type IS NULL)"
            params.append(entity_type)
        
        query += " ORDER BY type, name"
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        standards = []
        for row in rows:
            data = dict(zip(columns, row))
            if isinstance(data.get('rule'), str):
                data['rule'] = json.loads(data['rule'])
            standards.append(DataStandard(**data))
        return standards
    
    def update_standard(self, standard_id: str, updates: Dict[str, Any]) -> Optional[DataStandard]:
        """更新数据标准"""
        if 'rule' in updates and isinstance(updates['rule'], dict):
            updates['rule'] = json.dumps(updates['rule'])
        updates['updated_at'] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [standard_id]
        
        cursor = self.sqlite.conn.cursor()
        cursor.execute(f"UPDATE data_standards SET {set_clause} WHERE id = ?", values)
        self.sqlite.conn.commit()
        
        if cursor.rowcount > 0:
            return self.get_standard(standard_id)
        return None
    
    def delete_standard(self, standard_id: str) -> bool:
        """删除数据标准"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("DELETE FROM standard_violations WHERE standard_id = ?", (standard_id,))
        cursor.execute("DELETE FROM data_standards WHERE id = ?", (standard_id,))
        self.sqlite.conn.commit()
        return cursor.rowcount > 0
    
    def validate_entity(self, entity_id: str, standard_id: Optional[str] = None) -> List[StandardViolation]:
        """验证实体是否符合标准"""
        # 获取实体
        entities = self.sqlite.query_entities(limit=10000)
        entity = next((e for e in entities if e.get('id') == entity_id), None)
        if not entity:
            return []
        
        # 获取适用的标准
        if standard_id:
            standards = [self.get_standard(standard_id)]
        else:
            standards = self.list_standards(entity_type=entity.get('type'))
        
        violations = []
        for standard in standards:
            if not standard or not standard.enabled:
                continue
            
            # 根据标准类型进行验证
            if standard.type == DataStandardType.NAMING:
                violations.extend(self._validate_naming(entity, standard))
            elif standard.type == DataStandardType.FORMAT:
                violations.extend(self._validate_format(entity, standard))
            elif standard.type == DataStandardType.QUALITY:
                violations.extend(self._validate_quality(entity, standard))
            elif standard.type == DataStandardType.RELATIONSHIP:
                violations.extend(self._validate_relationship(entity, standard))
        
        return violations
    
    def _validate_naming(self, entity: Dict[str, Any], standard: DataStandard) -> List[StandardViolation]:
        """验证命名规范"""
        violations = []
        rule = standard.rule
        
        name = entity.get('name', '')
        pattern = rule.get('pattern')
        if pattern:
            if not re.match(pattern, name):
                violations.append(StandardViolation(
                    id=f"{entity.get('id')}_{standard.id}_{datetime.now().timestamp()}",
                    entity_id=entity.get('id'),
                    standard_id=standard.id,
                    violation_type="naming",
                    message=f"名称'{name}'不符合命名规范: {pattern}",
                    severity=rule.get('severity', 'medium'),
                    fix_suggestion=rule.get('suggestion')
                ))
        
        return violations
    
    def _validate_format(self, entity: Dict[str, Any], standard: DataStandard) -> List[StandardViolation]:
        """验证格式规范"""
        violations = []
        # 格式验证逻辑
        return violations
    
    def _validate_quality(self, entity: Dict[str, Any], standard: DataStandard) -> List[StandardViolation]:
        """验证质量规范"""
        violations = []
        # 质量验证逻辑
        return violations
    
    def _validate_relationship(self, entity: Dict[str, Any], standard: DataStandard) -> List[StandardViolation]:
        """验证关系规范"""
        violations = []
        # 关系验证逻辑
        return violations
    
    def record_violation(self, violation: StandardViolation) -> StandardViolation:
        """记录违规项"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            INSERT INTO standard_violations 
            (id, entity_id, standard_id, violation_type, message, severity, fix_suggestion, status, created_at, fixed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            violation.id, violation.entity_id, violation.standard_id,
            violation.violation_type, violation.message, violation.severity,
            violation.fix_suggestion, violation.status,
            violation.created_at.isoformat(),
            violation.fixed_at.isoformat() if violation.fixed_at else None
        ))
        self.sqlite.conn.commit()
        return violation
    
    def get_violations(self, entity_id: Optional[str] = None, standard_id: Optional[str] = None, status: Optional[str] = None) -> List[StandardViolation]:
        """获取违规项"""
        cursor = self.sqlite.conn.cursor()
        query = "SELECT * FROM standard_violations WHERE 1=1"
        params = []
        
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if standard_id:
            query += " AND standard_id = ?"
            params.append(standard_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        violations = []
        for row in rows:
            data = dict(zip(columns, row))
            if data.get('fixed_at'):
                data['fixed_at'] = datetime.fromisoformat(data['fixed_at'])
            violations.append(StandardViolation(**data))
        return violations


class CatalogService:
    """数据目录服务"""
    
    def __init__(self, sqlite_processor, graph_store=None):
        self.sqlite = sqlite_processor
        self.graph = graph_store
    
    def browse_catalog(self, 
                      category: Optional[str] = None,
                      tag_id: Optional[str] = None,
                      entity_type: Optional[str] = None,
                      source: Optional[str] = None,
                      limit: int = 100,
                      offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """浏览数据目录"""
        entities = self.sqlite.query_entities(
            entity_type=entity_type,
            source=source,
            limit=10000
        )
        
        # 应用过滤
        filtered = []
        for entity in entities:
            if category:
                # 可以通过标签分类过滤
                pass
            if tag_id:
                # 检查实体是否有该标签
                tags = self._get_entity_tags(entity.get('id'))
                if not any(t.get('id') == tag_id for t in tags):
                    continue
            filtered.append(entity)
        
        total = len(filtered)
        paginated = filtered[offset:offset+limit]
        
        # 丰富实体信息（标签、质量评分等）
        enriched = []
        for entity in paginated:
            enriched_entity = entity.copy()
            enriched_entity['tags'] = self._get_entity_tags(entity.get('id'))
            # 可以添加质量评分等信息
            enriched.append(enriched_entity)
        
        return enriched, total
    
    def discover_entities(self, 
                         query: Optional[str] = None,
                         entity_type: Optional[str] = None,
                         limit: int = 10) -> List[Dict[str, Any]]:
        """智能发现实体"""
        entities = self.sqlite.query_entities(
            entity_type=entity_type,
            limit=10000
        )
        
        if query:
            # 简单文本匹配
            query_lower = query.lower()
            entities = [
                e for e in entities
                if query_lower in e.get('name', '').lower()
                or query_lower in (e.get('description') or '').lower()
            ]
        
        # 计算发现分数（简化版）
        scored = []
        for entity in entities[:limit*2]:  # 先取更多，再排序
            score = self._calculate_discovery_score(entity)
            scored.append((score, entity))
        
        # 按分数排序
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 返回前limit个
        results = []
        for score, entity in scored[:limit]:
            enriched = entity.copy()
            enriched['discovery_score'] = score
            enriched['tags'] = self._get_entity_tags(entity.get('id'))
            results.append(enriched)
        
        return results
    
    def _calculate_discovery_score(self, entity: Dict[str, Any]) -> float:
        """计算发现分数"""
        score = 0.0
        
        # 1. 使用频率（简化：基于关系数量）
        relationships = self.sqlite.query_relationships(
            source_id=entity.get('id'),
            limit=100
        )
        incoming = self.sqlite.query_relationships(
            target_id=entity.get('id'),
            limit=100
        )
        usage_score = min(1.0, (len(relationships) + len(incoming)) / 10.0)
        score += 0.3 * usage_score
        
        # 2. 质量评分
        quality_scores, _ = self.sqlite.query_quality_scores(
            entity_id=entity.get('id'),
            limit=1
        )
        if quality_scores:
            quality_score = quality_scores[0].get('overall_score', 0.0) / 100.0
            score += 0.3 * quality_score
        
        # 3. 标签数量（有标签的实体更易发现）
        tags = self._get_entity_tags(entity.get('id'))
        tag_score = min(1.0, len(tags) / 5.0)
        score += 0.2 * tag_score
        
        # 4. 描述完整性
        has_description = 1.0 if entity.get('description') else 0.0
        score += 0.2 * has_description
        
        return min(1.0, score)
    
    def _get_entity_tags(self, entity_id: str) -> List[Dict[str, Any]]:
        """获取实体标签（内部方法）"""
        cursor = self.sqlite.conn.cursor()
        cursor.execute("""
            SELECT t.* FROM entity_tags et
            JOIN tags t ON et.tag_id = t.id
            WHERE et.entity_id = ?
        """, (entity_id,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_usage_analytics(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """获取使用分析"""
        # 简化版使用分析
        entities = self.sqlite.query_entities(limit=10000)
        
        # 统计访问频率（基于关系数量）
        usage_stats = []
        for entity in entities[:100]:  # 限制数量
            relationships = self.sqlite.query_relationships(
                source_id=entity.get('id'),
                limit=100
            )
            incoming = self.sqlite.query_relationships(
                target_id=entity.get('id'),
                limit=100
            )
            usage_stats.append({
                'entity_id': entity.get('id'),
                'entity_name': entity.get('name'),
                'entity_type': entity.get('type'),
                'usage_count': len(relationships) + len(incoming)
            })
        
        usage_stats.sort(key=lambda x: x['usage_count'], reverse=True)
        
        return {
            'high_usage': usage_stats[:10],
            'low_usage': usage_stats[-10:] if len(usage_stats) > 10 else [],
            'total_entities': len(entities)
        }

