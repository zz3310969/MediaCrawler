"""
内存版任务存储实现
"""
import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from collections import deque

from api.interfaces.storage import ITaskStorage
from api.schemas.task import Task, TaskStatus
from api.schemas.event import LogEntry

logger = logging.getLogger(__name__)


class MemoryTaskStorage(ITaskStorage):
    """内存版任务存储"""
    
    def __init__(
        self,
        max_logs_per_task: int = 2000,
        log_retention_days: int = 7
    ):
        self._max_logs_per_task = max_logs_per_task
        self._log_retention_days = log_retention_days
        
        # 任务存储 {task_id: Task}
        self._tasks: Dict[str, Task] = {}
        # 会话任务映射 {session_id: [task_id, ...]}
        self._session_tasks: Dict[str, List[str]] = {}
        # 幂等键映射 {session_id:idempotency_key: task_id}
        self._idempotency_index: Dict[str, str] = {}
        # 日志存储 {task_id: deque[LogEntry]}
        self._logs: Dict[str, deque] = {}
        
        # 锁
        self._lock = asyncio.Lock()
    
    # ========== 任务 CRUD ==========
    
    async def create(self, task: Task) -> str:
        """创建任务，返回 task_id"""
        async with self._lock:
            if task.task_id in self._tasks:
                raise ValueError(f"Task {task.task_id} already exists")
            
            self._tasks[task.task_id] = task
            
            # 添加到会话索引
            if task.session_id not in self._session_tasks:
                self._session_tasks[task.session_id] = []
            self._session_tasks[task.session_id].append(task.task_id)
            
            # 添加幂等键索引
            if task.idempotency_key:
                key = f"{task.session_id}:{task.idempotency_key}"
                self._idempotency_index[key] = task.task_id
            
            # 初始化日志队列
            self._logs[task.task_id] = deque(maxlen=self._max_logs_per_task)
            
            logger.debug(f"Task {task.task_id[:8]} created")
            return task.task_id
    
    async def get(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    async def update(
        self, 
        task_id: str, 
        data: Dict,
        version: Optional[int] = None
    ) -> bool:
        """更新任务"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # 乐观锁检查
            if version is not None and task.version != version:
                logger.warning(f"Version mismatch for task {task_id[:8]}")
                return False
            
            # 更新字段
            for key, value in data.items():
                if hasattr(task, key):
                    if key == "progress" and isinstance(value, dict):
                        # 合并 progress 字段
                        for pk, pv in value.items():
                            setattr(task.progress, pk, pv)
                    elif key == "result" and isinstance(value, dict):
                        # 合并 result 字段
                        for rk, rv in value.items():
                            setattr(task.result, rk, rv)
                    elif key == "metadata" and isinstance(value, dict):
                        # 合并 metadata 字段
                        for mk, mv in value.items():
                            setattr(task.metadata, mk, mv)
                    else:
                        setattr(task, key, value)
            
            # 增加版本号
            task.version += 1
            
            return True
    
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        async with self._lock:
            task = self._tasks.pop(task_id, None)
            if not task:
                return False
            
            # 从会话索引移除
            if task.session_id in self._session_tasks:
                self._session_tasks[task.session_id] = [
                    tid for tid in self._session_tasks[task.session_id]
                    if tid != task_id
                ]
            
            # 从幂等键索引移除
            if task.idempotency_key:
                key = f"{task.session_id}:{task.idempotency_key}"
                self._idempotency_index.pop(key, None)
            
            # 删除日志
            self._logs.pop(task_id, None)
            
            logger.debug(f"Task {task_id[:8]} deleted")
            return True
    
    async def exists(self, task_id: str) -> bool:
        """任务是否存在"""
        return task_id in self._tasks
    
    # ========== 批量操作 ==========
    
    async def get_by_session(
        self, 
        session_id: str,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        """获取用户任务"""
        task_ids = self._session_tasks.get(session_id, [])
        
        # 过滤
        tasks = []
        for tid in task_ids:
            task = self._tasks.get(tid)
            if not task:
                continue
            if status and task.status != status:
                continue
            if platform and task.config.platform != platform:
                continue
            tasks.append(task)
        
        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        # 分页
        return tasks[offset:offset + limit]
    
    async def get_by_status(
        self, 
        status: TaskStatus,
        limit: int = 100
    ) -> List[Task]:
        """获取指定状态的任务"""
        tasks = [t for t in self._tasks.values() if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]
    
    async def bulk_update_status(
        self, 
        task_ids: List[str], 
        status: TaskStatus
    ) -> int:
        """批量更新状态，返回更新数量"""
        async with self._lock:
            count = 0
            for tid in task_ids:
                task = self._tasks.get(tid)
                if task:
                    task.status = status
                    task.version += 1
                    count += 1
            return count
    
    async def find_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[Task]:
        """根据幂等键查找任务"""
        key = f"{session_id}:{idempotency_key}"
        task_id = self._idempotency_index.get(key)
        if task_id:
            return self._tasks.get(task_id)
        return None
    
    # ========== 日志存储 ==========
    
    async def append_log(self, task_id: str, log_entry: LogEntry) -> bool:
        """追加日志"""
        async with self._lock:
            if task_id not in self._logs:
                self._logs[task_id] = deque(maxlen=self._max_logs_per_task)
            
            self._logs[task_id].append(log_entry)
            return True
    
    async def get_logs(
        self, 
        task_id: str, 
        limit: int = 100,
        offset: int = 0,
        level: Optional[str] = None
    ) -> List[LogEntry]:
        """获取日志"""
        logs = self._logs.get(task_id, deque())
        
        # 转换为列表
        result = list(logs)
        
        # 过滤级别
        if level:
            result = [log for log in result if log.level == level]
        
        # 分页（从最新开始）
        result.reverse()
        return result[offset:offset + limit]
    
    async def clear_logs(self, task_id: str) -> bool:
        """清空日志"""
        async with self._lock:
            if task_id in self._logs:
                self._logs[task_id].clear()
                return True
            return False
    
    async def trim_logs(self, task_id: str, max_count: int) -> int:
        """裁剪日志（保留最新 max_count 条），返回删除数量"""
        async with self._lock:
            logs = self._logs.get(task_id)
            if not logs:
                return 0
            
            current_count = len(logs)
            if current_count <= max_count:
                return 0
            
            # 只保留最新的 max_count 条
            deleted = current_count - max_count
            while len(logs) > max_count:
                logs.popleft()
            
            return deleted
    
    # ========== 统计查询 ==========
    
    async def count_by_status(
        self, 
        session_id: Optional[str] = None
    ) -> Dict[str, int]:
        """按状态统计"""
        counts = {status.value: 0 for status in TaskStatus}
        
        if session_id:
            task_ids = self._session_tasks.get(session_id, [])
            tasks = [self._tasks.get(tid) for tid in task_ids]
            tasks = [t for t in tasks if t]
        else:
            tasks = self._tasks.values()
        
        for task in tasks:
            counts[task.status] += 1
        
        return counts
    
    async def get_recent_tasks(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Task]:
        """获取最近任务"""
        return await self.get_by_session(session_id, limit=limit)
    
    async def count_by_session(self, session_id: str) -> int:
        """获取用户任务总数"""
        return len(self._session_tasks.get(session_id, []))
    
    # ========== 维护 ==========
    
    async def cleanup_old_tasks(self, days: int) -> int:
        """清理旧任务，返回清理数量"""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            to_delete = []
            
            for task_id, task in self._tasks.items():
                if task.created_at < cutoff:
                    # 只清理已完成的任务
                    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                        to_delete.append(task_id)
            
            for task_id in to_delete:
                task = self._tasks.pop(task_id)
                
                # 从会话索引移除
                if task.session_id in self._session_tasks:
                    self._session_tasks[task.session_id] = [
                        tid for tid in self._session_tasks[task.session_id]
                        if tid != task_id
                    ]
                
                # 从幂等键索引移除
                if task.idempotency_key:
                    key = f"{task.session_id}:{task.idempotency_key}"
                    self._idempotency_index.pop(key, None)
                
                # 删除日志
                self._logs.pop(task_id, None)
            
            if to_delete:
                logger.info(f"Cleaned up {len(to_delete)} old tasks")
            
            return len(to_delete)
    
    async def archive_task(self, task_id: str) -> bool:
        """归档任务"""
        # 内存版暂不实现归档功能
        return False

