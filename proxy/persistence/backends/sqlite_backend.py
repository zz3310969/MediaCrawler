# -*- coding: utf-8 -*-
# @Desc    : SQLite 存储后端实现

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from proxy.types import PersistedProxy, AccountProxyBinding, ProxyQualityMetrics, BindingStatus
from proxy.persistence.proxy_store import ProxyStore, BindingStore


class SqliteProxyStore(ProxyStore):
    """SQLite代理存储实现"""
    
    def __init__(self, db_path: str = "data/proxy.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def init(self) -> None:
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
    
    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def _create_tables(self) -> None:
        """创建表"""
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS proxies (
                proxy_id TEXT PRIMARY KEY,
                ip TEXT NOT NULL,
                port INTEGER NOT NULL,
                protocol TEXT DEFAULT 'http',
                username TEXT,
                password TEXT,
                source TEXT NOT NULL,
                source_name TEXT,
                country TEXT DEFAULT 'CN',
                province TEXT,
                city TEXT,
                isp TEXT,
                is_active INTEGER DEFAULT 1,
                is_validated INTEGER DEFAULT 0,
                last_validated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expired_at TEXT,
                UNIQUE(ip, port)
            );
            
            CREATE TABLE IF NOT EXISTS proxy_quality_metrics (
                proxy_id TEXT PRIMARY KEY,
                total_requests INTEGER DEFAULT 0,
                success_requests INTEGER DEFAULT 0,
                failed_requests INTEGER DEFAULT 0,
                timeout_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0,
                min_response_time REAL,
                max_response_time REAL,
                p95_response_time REAL,
                consecutive_failures INTEGER DEFAULT 0,
                consecutive_successes INTEGER DEFAULT 0,
                last_success_at TEXT,
                last_failure_at TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (proxy_id) REFERENCES proxies(proxy_id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_proxies_source ON proxies(source);
            CREATE INDEX IF NOT EXISTS idx_proxies_active ON proxies(is_active);
            CREATE INDEX IF NOT EXISTS idx_proxies_protocol ON proxies(protocol);
        """)
        await self._conn.commit()
    
    async def save_proxy(self, proxy: PersistedProxy) -> None:
        """保存代理"""
        await self._conn.execute("""
            INSERT OR REPLACE INTO proxies 
            (proxy_id, ip, port, protocol, username, password, source, source_name,
             country, province, city, isp, is_active, is_validated, last_validated_at,
             created_at, updated_at, expired_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proxy.proxy_id, proxy.ip, proxy.port, proxy.protocol,
            proxy.username, proxy.password, proxy.source, proxy.source_name,
            proxy.country, proxy.province, proxy.city, proxy.isp,
            1 if proxy.is_active else 0, 1 if proxy.is_validated else 0,
            proxy.last_validated_at.isoformat() if proxy.last_validated_at else None,
            proxy.created_at.isoformat(), proxy.updated_at.isoformat(),
            proxy.expired_at.isoformat() if proxy.expired_at else None,
        ))
        await self._conn.commit()
    
    async def save_proxies(self, proxies: List[PersistedProxy]) -> int:
        """批量保存代理"""
        count = 0
        for proxy in proxies:
            try:
                await self.save_proxy(proxy)
                count += 1
            except Exception:
                continue
        return count
    
    async def get_proxy(self, proxy_id: str) -> Optional[PersistedProxy]:
        """获取代理"""
        cursor = await self._conn.execute(
            "SELECT * FROM proxies WHERE proxy_id = ?", (proxy_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_proxy(row)
        return None
    
    async def get_proxy_by_address(self, ip: str, port: int) -> Optional[PersistedProxy]:
        """通过地址获取代理"""
        cursor = await self._conn.execute(
            "SELECT * FROM proxies WHERE ip = ? AND port = ?", (ip, port)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_proxy(row)
        return None
    
    async def get_all_proxies(
        self,
        source: Optional[str] = None,
        protocol: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PersistedProxy]:
        """获取代理列表"""
        conditions = []
        params = []
        
        if source is not None:
            conditions.append("source = ?")
            params.append(source)
        if protocol is not None:
            conditions.append("protocol = ?")
            params.append(protocol)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM proxies WHERE {where_clause} ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_proxy(row) for row in rows]
    
    async def get_available_proxies(
        self,
        protocol: Optional[str] = None,
        min_quality_score: float = 0.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """获取可用代理列表"""
        conditions = ["p.is_active = 1", "(p.expired_at IS NULL OR p.expired_at > datetime('now'))"]
        params = []
        
        if protocol:
            conditions.append("p.protocol = ?")
            params.append(protocol)
        
        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT p.*, COALESCE(q.total_requests, 0) as total_requests,
                   COALESCE(q.success_requests, 0) as success_requests
            FROM proxies p
            LEFT JOIN proxy_quality_metrics q ON p.proxy_id = q.proxy_id
            WHERE {where_clause}
            ORDER BY 
                CASE WHEN q.total_requests > 0 
                     THEN CAST(q.success_requests AS REAL) / q.total_requests 
                     ELSE 0.5 END DESC,
                p.updated_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_proxy(row) for row in rows]
    
    async def update_proxy(self, proxy: PersistedProxy) -> bool:
        """更新代理"""
        proxy.updated_at = datetime.now()
        cursor = await self._conn.execute("""
            UPDATE proxies SET
                ip = ?, port = ?, protocol = ?, username = ?, password = ?,
                source = ?, source_name = ?, country = ?, province = ?, city = ?, isp = ?,
                is_active = ?, is_validated = ?, last_validated_at = ?,
                updated_at = ?, expired_at = ?
            WHERE proxy_id = ?
        """, (
            proxy.ip, proxy.port, proxy.protocol, proxy.username, proxy.password,
            proxy.source, proxy.source_name, proxy.country, proxy.province, proxy.city, proxy.isp,
            1 if proxy.is_active else 0, 1 if proxy.is_validated else 0,
            proxy.last_validated_at.isoformat() if proxy.last_validated_at else None,
            proxy.updated_at.isoformat(),
            proxy.expired_at.isoformat() if proxy.expired_at else None,
            proxy.proxy_id,
        ))
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def update_proxy_status(self, proxy_id: str, is_active: bool) -> bool:
        """更新代理状态"""
        cursor = await self._conn.execute(
            "UPDATE proxies SET is_active = ?, updated_at = ? WHERE proxy_id = ?",
            (1 if is_active else 0, datetime.now().isoformat(), proxy_id)
        )
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def delete_proxy(self, proxy_id: str) -> bool:
        """删除代理"""
        cursor = await self._conn.execute(
            "DELETE FROM proxies WHERE proxy_id = ?", (proxy_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def delete_expired_proxies(self) -> int:
        """删除过期代理"""
        cursor = await self._conn.execute(
            "DELETE FROM proxies WHERE expired_at IS NOT NULL AND expired_at < datetime('now')"
        )
        await self._conn.commit()
        return cursor.rowcount
    
    async def count_proxies(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """统计代理数量"""
        conditions = []
        params = []
        
        if source is not None:
            conditions.append("source = ?")
            params.append(source)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cursor = await self._conn.execute(
            f"SELECT COUNT(*) FROM proxies WHERE {where_clause}", params
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def save_quality_metrics(self, metrics: ProxyQualityMetrics) -> None:
        """保存质量指标"""
        await self._conn.execute("""
            INSERT OR REPLACE INTO proxy_quality_metrics
            (proxy_id, total_requests, success_requests, failed_requests, timeout_requests,
                avg_response_time, min_response_time, max_response_time, p95_response_time,
             consecutive_failures, consecutive_successes, last_success_at, last_failure_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.proxy_id, metrics.total_requests, metrics.success_requests,
            metrics.failed_requests, metrics.timeout_requests,
            metrics.avg_response_time, metrics.min_response_time,
            metrics.max_response_time, metrics.p95_response_time,
            metrics.consecutive_failures, metrics.consecutive_successes,
            metrics.last_success_at.isoformat() if metrics.last_success_at else None,
            metrics.last_failure_at.isoformat() if metrics.last_failure_at else None,
            metrics.updated_at.isoformat(),
        ))
        await self._conn.commit()
    
    async def get_quality_metrics(self, proxy_id: str) -> Optional[ProxyQualityMetrics]:
        """获取质量指标"""
        cursor = await self._conn.execute(
            "SELECT * FROM proxy_quality_metrics WHERE proxy_id = ?", (proxy_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_quality_metrics(row)
        return None
    
    async def get_proxies_by_quality(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
        limit: int = 100,
    ) -> List[PersistedProxy]:
        """按质量分获取代理"""
        # 计算质量分的SQL表达式
        query = """
            SELECT p.*, q.total_requests, q.success_requests, q.avg_response_time, q.consecutive_failures,
                CASE 
                    WHEN q.total_requests = 0 THEN 50
                    ELSE (
                        (CAST(q.success_requests AS REAL) / q.total_requests * 60) +
                    (CASE WHEN q.avg_response_time <= 0 THEN 30
                        WHEN q.avg_response_time >= 5000 THEN 0
                              ELSE 30 - (q.avg_response_time / 5000.0 * 30) END) +
                        (MAX(0, 10 - q.consecutive_failures * 2))
                    )
                END as quality_score
            FROM proxies p
            LEFT JOIN proxy_quality_metrics q ON p.proxy_id = q.proxy_id
            WHERE p.is_active = 1
            HAVING quality_score >= ? AND quality_score <= ?
            ORDER BY quality_score DESC
            LIMIT ?
        """
        cursor = await self._conn.execute(query, (min_score, max_score, limit))
        rows = await cursor.fetchall()
        return [self._row_to_proxy(row) for row in rows]
    
    def _row_to_proxy(self, row: aiosqlite.Row) -> PersistedProxy:
        """Row转换为PersistedProxy"""
        return PersistedProxy(
            proxy_id=row["proxy_id"],
            ip=row["ip"],
            port=row["port"],
            protocol=row["protocol"],
            username=row["username"],
            password=row["password"],
            source=row["source"],
            source_name=row["source_name"],
            country=row["country"] or "CN",
            province=row["province"],
            city=row["city"],
            isp=row["isp"],
            is_active=bool(row["is_active"]),
            is_validated=bool(row["is_validated"]),
            last_validated_at=datetime.fromisoformat(row["last_validated_at"]) if row["last_validated_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expired_at=datetime.fromisoformat(row["expired_at"]) if row["expired_at"] else None,
        )
    
    def _row_to_quality_metrics(self, row: aiosqlite.Row) -> ProxyQualityMetrics:
        """Row转换为ProxyQualityMetrics"""
        return ProxyQualityMetrics(
            proxy_id=row["proxy_id"],
            total_requests=row["total_requests"],
            success_requests=row["success_requests"],
            failed_requests=row["failed_requests"],
            timeout_requests=row["timeout_requests"],
            avg_response_time=row["avg_response_time"],
            min_response_time=row["min_response_time"],
            max_response_time=row["max_response_time"],
            p95_response_time=row["p95_response_time"],
            consecutive_failures=row["consecutive_failures"],
            consecutive_successes=row["consecutive_successes"],
            last_success_at=datetime.fromisoformat(row["last_success_at"]) if row["last_success_at"] else None,
            last_failure_at=datetime.fromisoformat(row["last_failure_at"]) if row["last_failure_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SqliteBindingStore(BindingStore):
    """SQLite绑定存储实现"""
    
    def __init__(self, db_path: str = "data/proxy.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def init(self) -> None:
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
    
    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def _create_tables(self) -> None:
        """创建表"""
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS account_proxy_bindings (
                binding_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                proxy_id TEXT NOT NULL,
                is_sticky INTEGER DEFAULT 1,
                allow_auto_rebind INTEGER DEFAULT 1,
                bound_at TEXT NOT NULL,
                last_used_at TEXT,
                last_verified_at TEXT,
                status TEXT DEFAULT 'active',
                rebind_count INTEGER DEFAULT 0,
                UNIQUE(account_id, platform)
            );
            
            CREATE TABLE IF NOT EXISTS binding_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                binding_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                old_proxy_id TEXT,
                new_proxy_id TEXT,
                action TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_bindings_account ON account_proxy_bindings(account_id, platform);
            CREATE INDEX IF NOT EXISTS idx_bindings_proxy ON account_proxy_bindings(proxy_id);
            CREATE INDEX IF NOT EXISTS idx_bindings_status ON account_proxy_bindings(status);
        """)
        await self._conn.commit()
    
    async def save_binding(self, binding: AccountProxyBinding) -> None:
        """保存绑定"""
        await self._conn.execute("""
            INSERT OR REPLACE INTO account_proxy_bindings
            (binding_id, account_id, platform, proxy_id, is_sticky, allow_auto_rebind,
             bound_at, last_used_at, last_verified_at, status, rebind_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            binding.binding_id, binding.account_id, binding.platform, binding.proxy_id,
            1 if binding.is_sticky else 0, 1 if binding.allow_auto_rebind else 0,
            binding.bound_at.isoformat(),
            binding.last_used_at.isoformat() if binding.last_used_at else None,
            binding.last_verified_at.isoformat() if binding.last_verified_at else None,
            binding.status, binding.rebind_count,
        ))
        await self._conn.commit()
    
    async def get_binding(
        self,
        account_id: str,
        platform: str,
    ) -> Optional[AccountProxyBinding]:
        """获取绑定"""
        cursor = await self._conn.execute(
            "SELECT * FROM account_proxy_bindings WHERE account_id = ? AND platform = ?",
            (account_id, platform)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_binding(row)
        return None
    
    async def get_binding_by_id(self, binding_id: str) -> Optional[AccountProxyBinding]:
        """通过ID获取绑定"""
        cursor = await self._conn.execute(
            "SELECT * FROM account_proxy_bindings WHERE binding_id = ?", (binding_id,)
        )
        row = await cursor.fetchone()
        if row:
            return self._row_to_binding(row)
        return None
    
    async def get_bindings_by_proxy(self, proxy_id: str) -> List[AccountProxyBinding]:
        """获取使用指定代理的所有绑定"""
        cursor = await self._conn.execute(
            "SELECT * FROM account_proxy_bindings WHERE proxy_id = ?", (proxy_id,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_binding(row) for row in rows]
    
    async def get_all_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccountProxyBinding]:
        """获取绑定列表"""
        conditions = []
        params = []
        
        if platform is not None:
            conditions.append("platform = ?")
            params.append(platform)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM account_proxy_bindings WHERE {where_clause} ORDER BY bound_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_binding(row) for row in rows]
    
    async def update_binding(self, binding: AccountProxyBinding) -> bool:
        """更新绑定"""
        cursor = await self._conn.execute("""
            UPDATE account_proxy_bindings SET
                proxy_id = ?, is_sticky = ?, allow_auto_rebind = ?,
                last_used_at = ?, last_verified_at = ?, status = ?, rebind_count = ?
            WHERE binding_id = ?
        """, (
            binding.proxy_id,
            1 if binding.is_sticky else 0, 1 if binding.allow_auto_rebind else 0,
            binding.last_used_at.isoformat() if binding.last_used_at else None,
            binding.last_verified_at.isoformat() if binding.last_verified_at else None,
            binding.status, binding.rebind_count,
            binding.binding_id,
        ))
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def delete_binding(self, account_id: str, platform: str) -> bool:
        """删除绑定"""
        cursor = await self._conn.execute(
            "DELETE FROM account_proxy_bindings WHERE account_id = ? AND platform = ?",
            (account_id, platform)
        )
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def delete_binding_by_id(self, binding_id: str) -> bool:
        """通过ID删除绑定"""
        cursor = await self._conn.execute(
            "DELETE FROM account_proxy_bindings WHERE binding_id = ?", (binding_id,)
        )
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def count_bindings(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """统计绑定数量"""
        conditions = []
        params = []
        
        if platform is not None:
            conditions.append("platform = ?")
            params.append(platform)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cursor = await self._conn.execute(
            f"SELECT COUNT(*) FROM account_proxy_bindings WHERE {where_clause}", params
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def count_bindings_by_proxy(self, proxy_id: str) -> int:
        """统计代理的绑定数量"""
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM account_proxy_bindings WHERE proxy_id = ?", (proxy_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    
    async def record_rebind_history(
        self,
        binding_id: str,
        account_id: str,
        platform: str,
        old_proxy_id: Optional[str],
        new_proxy_id: str,
        action: str,
        reason: Optional[str] = None,
    ) -> None:
        """记录重绑历史"""
        await self._conn.execute("""
            INSERT INTO binding_history (binding_id, account_id, platform, old_proxy_id, new_proxy_id, action, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            binding_id, account_id, platform, old_proxy_id, new_proxy_id,
            action, reason, datetime.now().isoformat()
        ))
        await self._conn.commit()
    
    def _row_to_binding(self, row: aiosqlite.Row) -> AccountProxyBinding:
        """Row转换为AccountProxyBinding"""
        return AccountProxyBinding(
            binding_id=row["binding_id"],
            account_id=row["account_id"],
            platform=row["platform"],
            proxy_id=row["proxy_id"],
            is_sticky=bool(row["is_sticky"]),
            allow_auto_rebind=bool(row["allow_auto_rebind"]),
            bound_at=datetime.fromisoformat(row["bound_at"]),
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            last_verified_at=datetime.fromisoformat(row["last_verified_at"]) if row["last_verified_at"] else None,
            status=row["status"],
            rebind_count=row["rebind_count"],
        )
