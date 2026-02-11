"""
WebSocket 实时更新
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime

from ..core.tasks import TaskManager, TaskStatus


router = APIRouter(prefix="/ws", tags=["websocket"])

# WebSocket 连接管理
class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.task_manager: TaskManager = None
    
    def set_task_manager(self, tm: TaskManager):
        """设置任务管理器"""
        self.task_manager = tm
    
    async def connect(self, websocket: WebSocket):
        """接受连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息"""
        message_str = json.dumps(message, ensure_ascii=False, default=str)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_task_update(self, task_id: str):
        """广播任务更新"""
        if not self.task_manager:
            return
        
        task = self.task_manager.get_task(task_id)
        if task:
            await self.broadcast({
                "type": "task_update",
                "task_id": task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "timestamp": datetime.now().isoformat()
            })
    
    async def broadcast_statistics(self, stats: Dict[str, Any]):
        """广播统计信息"""
        await self.broadcast({
            "type": "statistics",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        })


manager = ConnectionManager()


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    await manager.connect(websocket)
    
    try:
        # 发送欢迎消息
        await manager.send_personal_message(
            json.dumps({
                "type": "connected",
                "message": "WebSocket 连接成功",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
        
        # 保持连接并接收消息
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "subscribe_task":
                    # 订阅任务更新
                    task_id = message.get("task_id")
                    if task_id and manager.task_manager:
                        task = manager.task_manager.get_task(task_id)
                        if task:
                            await manager.send_personal_message(
                                json.dumps({
                                    "type": "task_status",
                                    "task_id": task_id,
                                    "status": task.status,
                                    "progress": task.progress,
                                    "message": task.message
                                }),
                                websocket
                            )
                
                elif message_type == "ping":
                    # 心跳
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }),
                        websocket
                    )
            
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "无效的 JSON 格式"
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def set_task_manager(tm: TaskManager):
    """设置任务管理器"""
    manager.set_task_manager(tm)







