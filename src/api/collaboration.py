"""
协作与知识沉淀API
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

from ..core.collaboration import (
    Comment, Annotation, Approval, ApprovalStatus, ApprovalLevel,
    CollaborationService
)
from ..core.auth import User
from ..core.user_storage import UserStorage
from .auth import get_current_user

router = APIRouter(prefix="/api/collaboration", tags=["协作"])

# 全局依赖
user_storage: Optional[UserStorage] = None
collaboration_service: Optional[CollaborationService] = None


def set_dependencies(storage: UserStorage, service: CollaborationService):
    """设置依赖"""
    global user_storage, collaboration_service
    user_storage = storage
    collaboration_service = service


# 请求模型
class CreateCommentRequest(BaseModel):
    """创建评论请求"""
    entity_id: str
    content: str
    parent_id: Optional[str] = None
    version: Optional[int] = None
    mentions: List[str] = []


class UpdateCommentRequest(BaseModel):
    """更新评论请求"""
    content: str


class CreateAnnotationRequest(BaseModel):
    """创建标注请求"""
    entity_id: str
    tag: str
    note: str
    category: Optional[str] = None


class UpdateAnnotationRequest(BaseModel):
    """更新标注请求"""
    tag: str
    note: str


class CreateApprovalRequest(BaseModel):
    """创建审批请求"""
    entity_id: str
    change_type: str
    change_data: Dict[str, Any]
    level: str


class BatchCreateCommentRequest(BaseModel):
    """批量创建评论请求"""
    entity_ids: List[str]
    content: str
    parent_id: Optional[str] = None
    version: Optional[int] = None
    mentions: List[str] = []


class BatchCreateAnnotationRequest(BaseModel):
    """批量创建标注请求"""
    entity_ids: List[str]
    tag: str
    note: str
    category: Optional[str] = None


class BatchCreateApprovalRequest(BaseModel):
    """批量创建审批请求"""
    entity_ids: List[str]
    change_type: str
    change_data: Dict[str, Any]
    level: str


# API端点
@router.post("/comments", response_model=Dict[str, Any])
async def create_comment(
    request: CreateCommentRequest,
    current_user: User = Depends(get_current_user)
):
    """创建评论"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    comment = Comment(
        id=str(uuid.uuid4()),
        entity_id=request.entity_id,
        user_id=current_user.id,
        content=request.content,
        parent_id=request.parent_id,
        version=request.version,
        mentions=request.mentions
    )
    
    collaboration_service.add_comment(comment)
    
    # 保存到数据库
    user_storage.create_comment(comment)
    
    return {
        "success": True,
        "comment": {
            "id": comment.id,
            "entity_id": comment.entity_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "parent_id": comment.parent_id,
            "version": comment.version,
            "created_at": comment.created_at.isoformat()
        }
    }


@router.get("/comments", response_model=Dict[str, Any])
async def get_comments(
    entity_id: str = Query(...),
    version: Optional[int] = Query(None),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取评论列表"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    comments = collaboration_service.get_comments(entity_id, version)
    
    return {
        "comments": [
            {
                "id": c.id,
                "entity_id": c.entity_id,
                "user_id": c.user_id,
                "content": c.content,
                "parent_id": c.parent_id,
                "version": c.version,
                "mentions": c.mentions,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in comments
        ],
        "count": len(comments)
    }


@router.put("/comments/{comment_id}", response_model=Dict[str, Any])
async def update_comment(
    comment_id: str,
    request: UpdateCommentRequest,
    current_user: User = Depends(get_current_user)
):
    """更新评论"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    comment = collaboration_service.update_comment(comment_id, request.content, current_user.id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在或无权限")
    
    return {"success": True, "comment_id": comment.id}


@router.delete("/comments/{comment_id}", response_model=Dict[str, Any])
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除评论"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    success = collaboration_service.delete_comment(comment_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="评论不存在或无权限")
    
    return {"success": True}


@router.post("/annotations", response_model=Dict[str, Any])
async def create_annotation(
    request: CreateAnnotationRequest,
    current_user: User = Depends(get_current_user)
):
    """创建标注"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    annotation = Annotation(
        id=str(uuid.uuid4()),
        entity_id=request.entity_id,
        user_id=current_user.id,
        tag=request.tag,
        note=request.note,
        category=request.category
    )
    
    collaboration_service.add_annotation(annotation)
    user_storage.create_annotation(annotation)
    
    return {
        "success": True,
        "annotation": {
            "id": annotation.id,
            "entity_id": annotation.entity_id,
            "user_id": annotation.user_id,
            "tag": annotation.tag,
            "note": annotation.note,
            "category": annotation.category,
            "created_at": annotation.created_at.isoformat()
        }
    }


@router.get("/annotations", response_model=Dict[str, Any])
async def get_annotations(
    entity_id: str = Query(...),
    current_user: Optional[User] = Depends(get_current_user)
):
    """获取标注列表"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    annotations = collaboration_service.get_annotations(entity_id)
    
    return {
        "annotations": [
            {
                "id": a.id,
                "entity_id": a.entity_id,
                "user_id": a.user_id,
                "tag": a.tag,
                "note": a.note,
                "category": a.category,
                "created_at": a.created_at.isoformat()
            }
            for a in annotations
        ],
        "count": len(annotations)
    }


@router.put("/annotations/{annotation_id}", response_model=Dict[str, Any])
async def update_annotation(
    annotation_id: str,
    request: UpdateAnnotationRequest,
    current_user: User = Depends(get_current_user)
):
    """更新标注"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    annotation = collaboration_service.update_annotation(
        annotation_id, request.tag, request.note, current_user.id
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="标注不存在或无权限")
    
    return {"success": True, "annotation_id": annotation.id}


@router.delete("/annotations/{annotation_id}", response_model=Dict[str, Any])
async def delete_annotation(
    annotation_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除标注"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    success = collaboration_service.delete_annotation(annotation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="标注不存在或无权限")
    
    return {"success": True}


@router.post("/approvals", response_model=Dict[str, Any])
async def create_approval(
    request: CreateApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """创建审批请求"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    try:
        level = ApprovalLevel(request.level)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的审批级别")
    
    approval = Approval(
        id=str(uuid.uuid4()),
        entity_id=request.entity_id,
        change_type=request.change_type,
        change_data=request.change_data,
        requester_id=current_user.id,
        level=level,
        status=ApprovalStatus.PENDING
    )
    
    collaboration_service.create_approval(approval)
    user_storage.create_approval(approval)
    
    return {
        "success": True,
        "approval": {
            "id": approval.id,
            "entity_id": approval.entity_id,
            "change_type": approval.change_type,
            "level": approval.level.value,
            "status": approval.status.value,
            "created_at": approval.created_at.isoformat()
        }
    }


@router.get("/approvals", response_model=Dict[str, Any])
async def get_approvals(
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """获取审批列表"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    approval_status = None
    if status:
        try:
            approval_status = ApprovalStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的审批状态")
    
    approvals = collaboration_service.get_approvals(entity_id, approval_status)
    
    return {
        "approvals": [
            {
                "id": a.id,
                "entity_id": a.entity_id,
                "change_type": a.change_type,
                "requester_id": a.requester_id,
                "approver_id": a.approver_id,
                "level": a.level.value,
                "status": a.status.value,
                "comment": a.comment,
                "created_at": a.created_at.isoformat(),
                "approved_at": a.approved_at.isoformat() if a.approved_at else None
            }
            for a in approvals
        ],
        "count": len(approvals)
    }


@router.post("/approvals/{approval_id}/approve", response_model=Dict[str, Any])
async def approve(
    approval_id: str,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """批准审批"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 先从数据库加载审批
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    approvals = user_storage.get_approvals()
    approval = next((a for a in approvals if a.id == approval_id), None)
    if not approval or approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=404, detail="审批不存在或状态不正确")
    
    # 更新审批
    approval.approver_id = current_user.id
    approval.status = ApprovalStatus.APPROVED
    approval.comment = comment
    approval.approved_at = datetime.now()
    approval.updated_at = datetime.now()
    
    # 保存到数据库
    if not user_storage.update_approval(approval):
        raise HTTPException(status_code=500, detail="更新审批失败")
    
    # 同步到内存服务
    collaboration_service.approve(approval_id, current_user.id, comment)
    
    return {"success": True, "approval_id": approval.id}


@router.post("/comments/batch", response_model=Dict[str, Any])
async def batch_create_comments(
    request: BatchCreateCommentRequest,
    current_user: User = Depends(get_current_user)
):
    """批量创建评论"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    results = []
    errors = []
    
    for entity_id in request.entity_ids:
        try:
            comment = Comment(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                user_id=current_user.id,
                content=request.content,
                parent_id=request.parent_id,
                version=request.version,
                mentions=request.mentions
            )
            collaboration_service.add_comment(comment)
            user_storage.create_comment(comment)
            results.append({
                "entity_id": entity_id,
                "success": True,
                "comment_id": comment.id
            })
        except Exception as e:
            errors.append({
                "entity_id": entity_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total": len(request.entity_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/annotations/batch", response_model=Dict[str, Any])
async def batch_create_annotations(
    request: BatchCreateAnnotationRequest,
    current_user: User = Depends(get_current_user)
):
    """批量创建标注"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    results = []
    errors = []
    
    for entity_id in request.entity_ids:
        try:
            annotation = Annotation(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                user_id=current_user.id,
                tag=request.tag,
                note=request.note,
                category=request.category
            )
            collaboration_service.add_annotation(annotation)
            user_storage.create_annotation(annotation)
            results.append({
                "entity_id": entity_id,
                "success": True,
                "annotation_id": annotation.id
            })
        except Exception as e:
            errors.append({
                "entity_id": entity_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total": len(request.entity_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/approvals/batch", response_model=Dict[str, Any])
async def batch_create_approvals(
    request: BatchCreateApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """批量创建审批请求"""
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    try:
        level = ApprovalLevel(request.level)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的审批级别")
    
    results = []
    errors = []
    
    for entity_id in request.entity_ids:
        try:
            approval = Approval(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                change_type=request.change_type,
                change_data=request.change_data,
                requester_id=current_user.id,
                level=level,
                status=ApprovalStatus.PENDING
            )
            collaboration_service.create_approval(approval)
            user_storage.create_approval(approval)
            results.append({
                "entity_id": entity_id,
                "success": True,
                "approval_id": approval.id
            })
        except Exception as e:
            errors.append({
                "entity_id": entity_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total": len(request.entity_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/approvals/{approval_id}/reject", response_model=Dict[str, Any])
async def reject(
    approval_id: str,
    comment: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """拒绝审批"""
    if not collaboration_service:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    if not collaboration_service or not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 先从数据库加载审批
    if not user_storage:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    approvals = user_storage.get_approvals()
    approval = next((a for a in approvals if a.id == approval_id), None)
    if not approval or approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=404, detail="审批不存在或状态不正确")
    
    # 更新审批
    approval.approver_id = current_user.id
    approval.status = ApprovalStatus.REJECTED
    approval.comment = comment
    approval.approved_at = datetime.now()
    approval.updated_at = datetime.now()
    
    # 保存到数据库
    if not user_storage.update_approval(approval):
        raise HTTPException(status_code=500, detail="更新审批失败")
    
    # 同步到内存服务
    collaboration_service.reject(approval_id, current_user.id, comment)
    
    return {"success": True, "approval_id": approval.id}

