"""
协作与知识沉淀模块
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class Comment(BaseModel):
    """评论模型"""
    id: str = Field(..., description="评论ID")
    entity_id: str = Field(..., description="实体ID")
    user_id: str = Field(..., description="用户ID")
    content: str = Field(..., description="评论内容")
    parent_id: Optional[str] = Field(None, description="父评论ID（用于回复）")
    version: Optional[int] = Field(None, description="关联的版本号")
    mentions: List[str] = Field(default_factory=list, description="提及的用户ID列表")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = Field(False, description="是否已删除")


class Annotation(BaseModel):
    """标注模型"""
    id: str = Field(..., description="标注ID")
    entity_id: str = Field(..., description="实体ID")
    user_id: str = Field(..., description="用户ID")
    tag: str = Field(..., description="标签")
    note: str = Field(..., description="备注")
    category: Optional[str] = Field(None, description="分类：business_semantic, usage_note, risk_warning, experience")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = Field(False, description="是否已删除")


class ApprovalStatus(str, Enum):
    """审批状态"""
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    CANCELLED = "cancelled"  # 已取消


class ApprovalLevel(str, Enum):
    """审批级别"""
    TECHNICAL = "technical"  # 技术审批
    DATA_GOVERNANCE = "data_governance"  # 数据治理审批
    BUSINESS = "business"  # 业务审批


class Approval(BaseModel):
    """审批模型"""
    id: str = Field(..., description="审批ID")
    entity_id: str = Field(..., description="实体ID")
    change_type: str = Field(..., description="变更类型：create, update, delete")
    change_data: Dict[str, Any] = Field(..., description="变更数据")
    requester_id: str = Field(..., description="申请人ID")
    approver_id: Optional[str] = Field(None, description="审批人ID")
    level: ApprovalLevel = Field(..., description="审批级别")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="审批状态")
    comment: Optional[str] = Field(None, description="审批意见")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = Field(None, description="审批时间")


class CollaborationService:
    """协作服务"""
    
    def __init__(self):
        """初始化协作服务"""
        self.comments: Dict[str, Comment] = {}
        self.annotations: Dict[str, Annotation] = {}
        self.approvals: Dict[str, Approval] = {}
    
    def add_comment(self, comment: Comment) -> Comment:
        """添加评论"""
        self.comments[comment.id] = comment
        return comment
    
    def get_comments(self, entity_id: str, version: Optional[int] = None) -> List[Comment]:
        """获取实体的评论列表"""
        comments = [c for c in self.comments.values() 
                   if c.entity_id == entity_id and not c.is_deleted]
        if version is not None:
            comments = [c for c in comments if c.version == version]
        # 按创建时间排序
        comments.sort(key=lambda x: x.created_at)
        return comments
    
    def get_comment(self, comment_id: str) -> Optional[Comment]:
        """获取评论"""
        return self.comments.get(comment_id)
    
    def update_comment(self, comment_id: str, content: str, user_id: str) -> Optional[Comment]:
        """更新评论（只能更新自己的评论）"""
        comment = self.comments.get(comment_id)
        if not comment or comment.user_id != user_id:
            return None
        comment.content = content
        comment.updated_at = datetime.now()
        return comment
    
    def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """删除评论（软删除）"""
        comment = self.comments.get(comment_id)
        if not comment or comment.user_id != user_id:
            return False
        comment.is_deleted = True
        comment.updated_at = datetime.now()
        return True
    
    def add_annotation(self, annotation: Annotation) -> Annotation:
        """添加标注"""
        self.annotations[annotation.id] = annotation
        return annotation
    
    def get_annotations(self, entity_id: str) -> List[Annotation]:
        """获取实体的标注列表"""
        annotations = [a for a in self.annotations.values() 
                      if a.entity_id == entity_id and not a.is_deleted]
        annotations.sort(key=lambda x: x.created_at)
        return annotations
    
    def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """获取标注"""
        return self.annotations.get(annotation_id)
    
    def update_annotation(self, annotation_id: str, tag: str, note: str, user_id: str) -> Optional[Annotation]:
        """更新标注"""
        annotation = self.annotations.get(annotation_id)
        if not annotation or annotation.user_id != user_id:
            return None
        annotation.tag = tag
        annotation.note = note
        annotation.updated_at = datetime.now()
        return annotation
    
    def delete_annotation(self, annotation_id: str, user_id: str) -> bool:
        """删除标注"""
        annotation = self.annotations.get(annotation_id)
        if not annotation or annotation.user_id != user_id:
            return False
        annotation.is_deleted = True
        annotation.updated_at = datetime.now()
        return True
    
    def create_approval(self, approval: Approval) -> Approval:
        """创建审批请求"""
        self.approvals[approval.id] = approval
        return approval
    
    def get_approval(self, approval_id: str) -> Optional[Approval]:
        """获取审批"""
        return self.approvals.get(approval_id)
    
    def get_approvals(self, entity_id: Optional[str] = None, status: Optional[ApprovalStatus] = None) -> List[Approval]:
        """获取审批列表"""
        approvals = list(self.approvals.values())
        if entity_id:
            approvals = [a for a in approvals if a.entity_id == entity_id]
        if status:
            approvals = [a for a in approvals if a.status == status]
        approvals.sort(key=lambda x: x.created_at, reverse=True)
        return approvals
    
    def approve(self, approval_id: str, approver_id: str, comment: Optional[str] = None) -> Optional[Approval]:
        """批准审批"""
        approval = self.approvals.get(approval_id)
        if not approval or approval.status != ApprovalStatus.PENDING:
            return None
        approval.approver_id = approver_id
        approval.status = ApprovalStatus.APPROVED
        approval.comment = comment
        approval.approved_at = datetime.now()
        approval.updated_at = datetime.now()
        return approval
    
    def reject(self, approval_id: str, approver_id: str, comment: Optional[str] = None) -> Optional[Approval]:
        """拒绝审批"""
        approval = self.approvals.get(approval_id)
        if not approval or approval.status != ApprovalStatus.PENDING:
            return None
        approval.approver_id = approver_id
        approval.status = ApprovalStatus.REJECTED
        approval.comment = comment
        approval.approved_at = datetime.now()
        approval.updated_at = datetime.now()
        return approval



