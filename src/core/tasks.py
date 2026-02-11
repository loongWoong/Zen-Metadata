"""
任务管理模型和状态管理
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid
import json
from pathlib import Path


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型枚举"""
    COLLECT_RELATIONAL = "collect_relational"
    COLLECT_GRAPHDB = "collect_graphdb"
    COLLECT_CODE = "collect_code"
    COLLECT_FILESYSTEM = "collect_filesystem"
    COLLECT_METAMODEL = "collect_metamodel"  # 元模型采集器通用类型
    SYNC_DATA = "sync_data"
    EXPORT_DATA = "export_data"


class Task(BaseModel):
    """任务模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务ID")
    type: TaskType = Field(..., description="任务类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    config: Dict[str, Any] = Field(default_factory=dict, description="任务配置")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="进度百分比")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        use_enum_values = True


class TaskManager:
    """任务管理器"""
    
    def __init__(self, storage_path: str = "data/tasks.json"):
        """
        初始化任务管理器
        
        Args:
            storage_path: 任务存储文件路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, Task] = {}
        self._load_tasks()
    
    def _load_tasks(self):
        """从文件加载任务"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_id, task_data in data.items():
                        # 转换日期字符串
                        if 'created_at' in task_data:
                            task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                        if 'started_at' in task_data and task_data['started_at']:
                            task_data['started_at'] = datetime.fromisoformat(task_data['started_at'])
                        if 'completed_at' in task_data and task_data['completed_at']:
                            task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
                        self.tasks[task_id] = Task(**task_data)
            except Exception as e:
                print(f"加载任务失败: {e}")
    
    def _save_tasks(self):
        """保存任务到文件"""
        try:
            data = {}
            for task_id, task in self.tasks.items():
                task_dict = task.dict()
                # 转换日期为字符串
                if isinstance(task_dict.get('created_at'), datetime):
                    task_dict['created_at'] = task_dict['created_at'].isoformat()
                if isinstance(task_dict.get('started_at'), datetime):
                    task_dict['started_at'] = task_dict['started_at'].isoformat()
                if isinstance(task_dict.get('completed_at'), datetime):
                    task_dict['completed_at'] = task_dict['completed_at'].isoformat()
                data[task_id] = task_dict
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存任务失败: {e}")
    
    def create_task(self, task_type: TaskType, config: Dict[str, Any]) -> Task:
        """
        创建新任务
        
        Args:
            task_type: 任务类型
            config: 任务配置
            
        Returns:
            创建的任务
        """
        task = Task(
            type=task_type,
            status=TaskStatus.PENDING,
            config=config
        )
        self.tasks[task.id] = task
        self._save_tasks()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象或None
        """
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          message: Optional[str] = None,
                          progress: Optional[float] = None,
                          error: Optional[str] = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            message: 状态消息
            progress: 进度
            error: 错误信息
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.status = status
        if message is not None:
            task.message = message
        if progress is not None:
            task.progress = progress
        if error is not None:
            task.error = error
        
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.now()
            task.progress = 100.0 if status == TaskStatus.COMPLETED else task.progress
        
        self._save_tasks()
    
    def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比
            message: 进度消息
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.progress = max(0.0, min(100.0, progress))
        if message:
            task.message = message
        self._save_tasks()
    
    def set_task_result(self, task_id: str, result: Dict[str, Any]):
        """
        设置任务结果
        
        Args:
            task_id: 任务ID
            result: 任务结果
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.result = result
        self._save_tasks()
    
    def list_tasks(self, status: Optional[TaskStatus] = None, 
                   task_type: Optional[TaskType] = None,
                   limit: int = 100) -> List[Task]:
        """
        列出任务
        
        Args:
            status: 状态过滤
            task_type: 任务类型过滤
            limit: 限制数量
            
        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        
        # 按创建时间倒序排序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    def update_task_config(self, task_id: str, config: Dict[str, Any]) -> bool:
        """
        更新任务配置
        
        Args:
            task_id: 任务ID
            config: 新配置
            
        Returns:
            是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            return False
        
        # 只能更新非运行中任务的配置
        if task.status == TaskStatus.RUNNING:
            return False
        
        task.config = config
        self._save_tasks()
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False



