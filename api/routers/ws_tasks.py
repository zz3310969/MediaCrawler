"""
多任务 WebSocket 路由
支持任务日志和事件的实时推送
"""
import asyncio
import logging
from typing import Dict, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from api.services.factory import get_session_store, get_event_bus, get_storage
from api.schemas.event import TaskEvent, EventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class TaskConnectionManager:
    """任务 WebSocket 连接管理器"""
    
    def __init__(self):
        # {task_id: {WebSocket, ...}}
        self._task_connections: Dict[str, Set[WebSocket]] = {}
        # {session_id: {WebSocket, ...}}
        self._session_connections: Dict[str, Set[WebSocket]] = {}
        # {websocket: {"session_id": ..., "task_id": ...}}
        self._connection_info: Dict[WebSocket, Dict] = {}
        # 锁
        self._lock = asyncio.Lock()
    
    async def connect_task(
        self, 
        websocket: WebSocket, 
        task_id: str, 
        session_id: str
    ) -> bool:
        """连接到特定任务"""
        await websocket.accept()
        
        async with self._lock:
            if task_id not in self._task_connections:
                self._task_connections[task_id] = set()
            self._task_connections[task_id].add(websocket)
            
            self._connection_info[websocket] = {
                "session_id": session_id,
                "task_id": task_id,
                "type": "task"
            }
        
        logger.debug(f"WS connected to task {task_id[:8]}")
        return True
    
    async def connect_session(
        self, 
        websocket: WebSocket, 
        session_id: str
    ) -> bool:
        """连接到会话（接收所有任务事件）"""
        await websocket.accept()
        
        async with self._lock:
            if session_id not in self._session_connections:
                self._session_connections[session_id] = set()
            self._session_connections[session_id].add(websocket)
            
            self._connection_info[websocket] = {
                "session_id": session_id,
                "type": "session"
            }
        
        logger.debug(f"WS connected to session {session_id[:8]}")
        return True
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """断开连接"""
        async with self._lock:
            info = self._connection_info.pop(websocket, None)
            if info:
                if info.get("type") == "task":
                    task_id = info.get("task_id")
                    if task_id in self._task_connections:
                        self._task_connections[task_id].discard(websocket)
                        if not self._task_connections[task_id]:
                            del self._task_connections[task_id]
                elif info.get("type") == "session":
                    session_id = info.get("session_id")
                    if session_id in self._session_connections:
                        self._session_connections[session_id].discard(websocket)
                        if not self._session_connections[session_id]:
                            del self._session_connections[session_id]
        
        logger.debug("WS disconnected")
    
    async def send_to_task(self, task_id: str, data: dict) -> int:
        """发送消息到特定任务的所有连接"""
        async with self._lock:
            connections = self._task_connections.get(task_id, set()).copy()
        
        count = 0
        disconnected = []
        
        for ws in connections:
            try:
                await ws.send_json(data)
                count += 1
            except Exception:
                disconnected.append(ws)
        
        # 清理断开的连接
        for ws in disconnected:
            await self.disconnect(ws)
        
        return count
    
    async def send_to_session(self, session_id: str, data: dict) -> int:
        """发送消息到会话的所有连接"""
        async with self._lock:
            connections = self._session_connections.get(session_id, set()).copy()
        
        count = 0
        disconnected = []
        
        for ws in connections:
            try:
                await ws.send_json(data)
                count += 1
            except Exception:
                disconnected.append(ws)
        
        # 清理断开的连接
        for ws in disconnected:
            await self.disconnect(ws)
        
        return count
    
    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            "task_connections": sum(len(v) for v in self._task_connections.values()),
            "session_connections": sum(len(v) for v in self._session_connections.values()),
            "total_connections": len(self._connection_info)
        }


# 全局连接管理器
ws_manager = TaskConnectionManager()


async def event_handler(event: TaskEvent) -> None:
    """事件处理器：将事件推送到 WebSocket"""
    data = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "task_id": event.task_id,
        "session_id": event.session_id,
        "timestamp": event.timestamp.isoformat(),
        "payload": event.payload
    }
    
    # 发送到任务订阅者
    await ws_manager.send_to_task(event.task_id, data)
    
    # 发送到会话订阅者
    await ws_manager.send_to_session(event.session_id, data)


# 订阅 ID（用于清理）
_subscription_ids = []


async def setup_event_subscriptions():
    """设置事件订阅"""
    global _subscription_ids
    
    event_bus = get_event_bus()
    
    # 订阅所有事件类型
    for event_type in EventType:
        sub_id = await event_bus.subscribe(event_type, event_handler)
        _subscription_ids.append(sub_id)
    
    logger.info("WebSocket event subscriptions set up")


async def cleanup_event_subscriptions():
    """清理事件订阅"""
    global _subscription_ids
    
    event_bus = get_event_bus()
    
    for sub_id in _subscription_ids:
        await event_bus.unsubscribe(sub_id)
    
    _subscription_ids.clear()
    logger.info("WebSocket event subscriptions cleaned up")


@router.websocket("/ws/tasks/{task_id}/logs")
async def websocket_task_logs(
    websocket: WebSocket,
    task_id: str,
    session_id: str = Query(..., description="Session ID")
):
    """
    订阅特定任务的日志和事件
    
    Query params:
        - session_id: 会话 ID（用于权限验证）
    """
    # 验证 session
    session_store = get_session_store()
    session = await session_store.get(session_id)
    
    if not session:
        await websocket.close(code=4001, reason="Invalid session")
        return
    
    # 验证任务权限
    storage = get_storage()
    task = await storage.get(task_id)
    
    if not task:
        await websocket.close(code=4004, reason="Task not found")
        return
    
    if task.session_id != session_id:
        await websocket.close(code=4003, reason="Permission denied")
        return
    
    # 连接
    await ws_manager.connect_task(websocket, task_id, session_id)
    
    try:
        # 发送历史日志
        logs = await storage.get_logs(task_id, limit=100)
        for log in reversed(logs):  # 从旧到新
            await websocket.send_json({
                "event_type": "task.log",
                "task_id": task_id,
                "timestamp": log.timestamp.isoformat(),
                "payload": {
                    "level": log.level,
                    "message": log.message
                }
            })
        
        # 发送当前任务状态
        await websocket.send_json({
            "event_type": "task.status",
            "task_id": task_id,
            "payload": {
                "status": task.status,
                "progress": task.progress.model_dump()
            }
        })
        
        # 保持连接，处理心跳
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    
    except WebSocketDisconnect:
        logger.debug(f"WS disconnected from task {task_id[:8]}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/session/events")
async def websocket_session_events(
    websocket: WebSocket,
    session_id: str = Query(..., description="Session ID")
):
    """
    订阅当前用户所有任务的事件
    
    Query params:
        - session_id: 会话 ID
    """
    # 验证 session
    session_store = get_session_store()
    session = await session_store.get(session_id)
    
    if not session:
        await websocket.close(code=4001, reason="Invalid session")
        return
    
    # 连接
    await ws_manager.connect_session(websocket, session_id)
    
    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id
        })
        
        # 保持连接，处理心跳
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    
    except WebSocketDisconnect:
        logger.debug(f"WS disconnected from session {session_id[:8]}")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取 WebSocket 连接统计"""
    return ws_manager.get_stats()

