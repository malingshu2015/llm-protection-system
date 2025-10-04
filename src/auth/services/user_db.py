"""用户数据库管理模块。"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiosqlite

from src.auth.models.api_key import APIKey
from src.auth.models.session import UserSession
from src.auth.models.user import User, UserRole
from src.logger import logger


class UserDatabase:
    """用户数据库管理类。"""

    def __init__(self, db_path: str = "data/users.db"):
        """初始化数据库。

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_db_directory()

    def _ensure_db_directory(self) -> None:
        """确保数据库目录存在。"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """初始化数据库表。"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建用户表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_verified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login TEXT,
                    login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    preferences TEXT,
                    avatar_url TEXT
                )
            """)

            # 创建API密钥表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    scopes TEXT NOT NULL,
                    rate_limit INTEGER,
                    ip_whitelist TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # 创建会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    refresh_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")

            await db.commit()
            logger.info("用户数据库初始化成功")

    # ==================== 用户管理 ====================

    async def create_user(self, user: User) -> User:
        """创建用户。

        Args:
            user: 用户对象

        Returns:
            创建的用户对象
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (
                    id, username, email, phone, password_hash, salt, role, department,
                    is_active, is_verified, created_at, updated_at, last_login,
                    login_attempts, locked_until, preferences, avatar_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id, user.username, user.email, user.phone, user.password_hash,
                user.salt, user.role.value, user.department, int(user.is_active),
                int(user.is_verified), user.created_at.isoformat(), user.updated_at.isoformat(),
                user.last_login.isoformat() if user.last_login else None,
                user.login_attempts,
                user.locked_until.isoformat() if user.locked_until else None,
                json.dumps(user.preferences), user.avatar_url
            ))
            await db.commit()

        logger.info(f"创建用户成功: {user.username}")
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户。

        Args:
            user_id: 用户ID

        Returns:
            用户对象,如果不存在则返回None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_user(row)
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户。

        Args:
            username: 用户名

        Returns:
            用户对象,如果不存在则返回None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_user(row)
        return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户。

        Args:
            email: 邮箱

        Returns:
            用户对象,如果不存在则返回None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_user(row)
        return None

    async def update_user(self, user_id: str, updates: Dict) -> bool:
        """更新用户信息。

        Args:
            user_id: 用户ID
            updates: 更新的字段字典

        Returns:
            是否更新成功
        """
        # 构建更新语句
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [user_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?",
                values[:-1] + [datetime.utcnow().isoformat(), user_id]
            )
            await db.commit()
            return db.total_changes > 0

    async def delete_user(self, user_id: str) -> bool:
        """删除用户。

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await db.commit()
            return db.total_changes > 0

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        role: Optional[UserRole] = None
    ) -> List[User]:
        """获取用户列表。

        Args:
            limit: 返回数量限制
            offset: 偏移量
            role: 角色过滤

        Returns:
            用户列表
        """
        query = "SELECT * FROM users"
        params = []

        if role:
            query += " WHERE role = ?"
            params.append(role.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_user(row) for row in rows]

    def _row_to_user(self, row: aiosqlite.Row) -> User:
        """将数据库行转换为User对象。

        Args:
            row: 数据库行

        Returns:
            User对象
        """
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            phone=row["phone"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            role=UserRole(row["role"]),
            department=row["department"],
            is_active=bool(row["is_active"]),
            is_verified=bool(row["is_verified"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
            login_attempts=row["login_attempts"],
            locked_until=datetime.fromisoformat(row["locked_until"]) if row["locked_until"] else None,
            preferences=json.loads(row["preferences"]) if row["preferences"] else {},
            avatar_url=row["avatar_url"]
        )

    # ==================== API密钥管理 ====================

    async def create_api_key(self, api_key: APIKey) -> APIKey:
        """创建API密钥。

        Args:
            api_key: API密钥对象

        Returns:
            创建的API密钥对象
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO api_keys (
                    id, user_id, key_hash, key_prefix, name, description,
                    scopes, rate_limit, ip_whitelist, is_active, expires_at,
                    created_at, last_used_at, usage_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api_key.id, api_key.user_id, api_key.key_hash, api_key.key_prefix,
                api_key.name, api_key.description,
                json.dumps(api_key.scopes), api_key.rate_limit,
                json.dumps(api_key.ip_whitelist), int(api_key.is_active),
                api_key.expires_at.isoformat() if api_key.expires_at else None,
                api_key.created_at.isoformat(),
                api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                api_key.usage_count
            ))
            await db.commit()

        logger.info(f"创建API密钥成功: {api_key.name} (用户: {api_key.user_id})")
        return api_key

    async def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """根据ID获取API密钥。

        Args:
            key_id: 密钥ID

        Returns:
            API密钥对象,如果不存在则返回None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM api_keys WHERE id = ?", (key_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_api_key(row)
        return None

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """根据密钥哈希获取API密钥。

        Args:
            key_hash: 密钥哈希

        Returns:
            API密钥对象,如果不存在则返回None
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_api_key(row)
        return None

    async def list_api_keys_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[APIKey]:
        """获取用户的API密钥列表。

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            API密钥列表
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_api_key(row) for row in rows]

    async def update_api_key(self, key_id: str, updates: Dict) -> bool:
        """更新API密钥信息。

        Args:
            key_id: 密钥ID
            updates: 更新的字段字典

        Returns:
            是否更新成功
        """
        # 处理需要JSON序列化的字段
        if "scopes" in updates:
            updates["scopes"] = json.dumps(updates["scopes"])
        if "ip_whitelist" in updates:
            updates["ip_whitelist"] = json.dumps(updates["ip_whitelist"])

        # 构建更新语句
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [key_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE api_keys SET {set_clause} WHERE id = ?",
                values
            )
            await db.commit()
            return db.total_changes > 0

    async def delete_api_key(self, key_id: str) -> bool:
        """删除API密钥。

        Args:
            key_id: 密钥ID

        Returns:
            是否删除成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            await db.commit()
            return db.total_changes > 0

    async def update_api_key_usage(self, key_id: str) -> bool:
        """更新API密钥使用记录。

        Args:
            key_id: 密钥ID

        Returns:
            是否更新成功
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE api_keys
                SET usage_count = usage_count + 1,
                    last_used_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), key_id))
            await db.commit()
            return db.total_changes > 0

    def _row_to_api_key(self, row: aiosqlite.Row) -> APIKey:
        """将数据库行转换为APIKey对象。

        Args:
            row: 数据库行

        Returns:
            APIKey对象
        """
        return APIKey(
            id=row["id"],
            user_id=row["user_id"],
            key_hash=row["key_hash"],
            key_prefix=row["key_prefix"],
            name=row["name"],
            description=row["description"],
            scopes=json.loads(row["scopes"]) if row["scopes"] else [],
            rate_limit=row["rate_limit"],
            ip_whitelist=json.loads(row["ip_whitelist"]) if row["ip_whitelist"] else [],
            is_active=bool(row["is_active"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            usage_count=row["usage_count"]
        )

    # ==================== 会话管理 ====================
    # (后续实现)


# 全局数据库实例
user_db = UserDatabase()
