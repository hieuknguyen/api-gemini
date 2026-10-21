import os
import json
import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

import pymysql
import pymysql.cursors
from dbutils.pooled_db import PooledDB

logger = logging.getLogger("antigravity-db")

BASE_DIR = Path(__file__).resolve().parent

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "antigravity")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "antigravity_secret")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "antigravity_db")

_pool: Optional[PooledDB] = None

def get_pool() -> PooledDB:
    global _pool
    if _pool is None:
        _init_pool()
    return _pool

def _init_pool():
    global _pool
    # Đảm bảo database đã tồn tại
    _ensure_database_exists()

    _pool = PooledDB(
        creator=pymysql,
        maxconnections=20,
        mincached=2,
        maxcached=10,
        maxshared=5,
        blocking=True,
        maxusage=None,
        setsession=[],
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    logger.info(f"Kết nối thành công MySQL Pool tới {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}")

def _ensure_database_exists():
    """Thử kết nối và tạo database nếu chưa có với retry loop"""
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                charset="utf8mb4",
                autocommit=True
            )
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.close()
            return
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Không thể kết nối MySQL sau {max_retries} lần thử: {e}")
                raise
            logger.warning(f"Chờ MySQL sẵn sàng ({attempt}/{max_retries})... {e}")
            time.sleep(2)

@contextmanager
def get_cursor():
    pool = get_pool()
    conn = pool.connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()

def execute(sql: str, params: Optional[tuple] = None) -> int:
    with get_cursor() as cur:
        return cur.execute(sql, params or ())

def fetch_all(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def fetch_one(sql: str, params: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()

def init_tables():
    """Tạo cấu trúc bảng trong MySQL"""
    with get_cursor() as cur:
        # 1. Bảng Accounts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                picture TEXT,
                refresh_token TEXT NOT NULL,
                access_token TEXT,
                token_expiry DOUBLE DEFAULT 0,
                project_id VARCHAR(128),
                is_active BOOLEAN DEFAULT TRUE,
                is_primary BOOLEAN DEFAULT FALSE,
                requests_count INT DEFAULT 0,
                rate_limited_until DOUBLE DEFAULT 0,
                error_message TEXT,
                last_used VARCHAR(64) DEFAULT NULL,
                created_at DOUBLE DEFAULT 0,
                updated_at DOUBLE DEFAULT 0,
                INDEX idx_email (email),
                INDEX idx_is_active (is_active),
                INDEX idx_is_primary (is_primary)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 2. Bảng Skills
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) DEFAULT NULL,
                name VARCHAR(255) NOT NULL,
                system_prompt TEXT NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                created_at VARCHAR(64),
                updated_at VARCHAR(64),
                INDEX idx_user_id (user_id),
                INDEX idx_is_default (is_default)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 3. Bảng Settings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key VARCHAR(64) PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at DOUBLE DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 4. Bảng Requests / Quota Log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requests_log (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                timestamp DOUBLE NOT NULL,
                account_id VARCHAR(64) NOT NULL,
                account_email VARCHAR(255) NOT NULL,
                model VARCHAR(128) NOT NULL,
                prompt_tokens INT DEFAULT 0,
                completion_tokens INT DEFAULT 0,
                total_tokens INT DEFAULT 0,
                status VARCHAR(32) DEFAULT 'success',
                INDEX idx_timestamp (timestamp),
                INDEX idx_account_id (account_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 5. Bảng Users (Tài khoản người dùng / Dự án gọi API)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) DEFAULT '',
                password VARCHAR(255) DEFAULT NULL,
                note TEXT,
                role VARCHAR(32) DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                created_at VARCHAR(64),
                updated_at VARCHAR(64),
                INDEX idx_is_active (is_active),
                INDEX idx_role (role),
                INDEX idx_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 6. Bảng API Keys (Khóa API riêng biệt thuộc về từng User)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                key_value VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                requests_count INT DEFAULT 0,
                total_tokens BIGINT DEFAULT 0,
                last_used_at VARCHAR(64) DEFAULT NULL,
                created_at VARCHAR(64),
                INDEX idx_user_id (user_id),
                INDEX idx_key_value (key_value),
                INDEX idx_key_active (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # 7. Bảng Payment Transactions (Lịch sử nạp tiền qua MoMo)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                order_id VARCHAR(64) NOT NULL UNIQUE,
                request_id VARCHAR(64) NOT NULL,
                amount INT NOT NULL,
                tokens_granted BIGINT NOT NULL,
                package_name VARCHAR(128) DEFAULT '',
                status VARCHAR(32) DEFAULT 'pending',
                payment_url TEXT,
                qr_code_url TEXT,
                deeplink TEXT,
                momo_trans_id VARCHAR(64) DEFAULT NULL,
                message TEXT,
                created_at VARCHAR(64),
                updated_at VARCHAR(64),
                INDEX idx_user_id (user_id),
                INDEX idx_order_id (order_id),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)

        # Cập nhật schema cho bảng đã tồn tại (Migration an toàn)
        try:
            cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(32) DEFAULT 'user'")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN password VARCHAR(255) DEFAULT NULL")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN balance DOUBLE DEFAULT 0")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE users ADD COLUMN token_balance BIGINT DEFAULT 100000")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE skills ADD COLUMN user_id VARCHAR(64) DEFAULT NULL")
            cur.execute("ALTER TABLE skills ADD INDEX idx_user_id (user_id)")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE skills DROP COLUMN icon")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE skills DROP COLUMN description")
        except Exception:
            pass
    logger.info("Đã khởi tạo toàn bộ bảng MySQL thành công.")

def run_migrations():
    """Tự động chuyển toàn bộ dữ liệu từ JSON & SQLite sang MySQL nếu bảng đang trống"""
    init_tables()
    _migrate_accounts()
    _migrate_skills()
    _migrate_settings()
    _migrate_quota_logs()

def _migrate_accounts():
    accounts_file = BASE_DIR / "accounts.json"
    row = fetch_one("SELECT COUNT(*) AS total FROM accounts")
    if row and row["total"] > 0:
        return

    if not accounts_file.exists():
        return

    try:
        data = json.loads(accounts_file.read_text(encoding="utf-8"))
        if not isinstance(data, list) or len(data) == 0:
            return

        now = time.time()
        for acc in data:
            execute("""
                INSERT INTO accounts (
                    id, email, name, picture, refresh_token, access_token, 
                    token_expiry, project_id, is_active, is_primary, requests_count, 
                    rate_limited_until, error_message, last_used, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    email=VALUES(email), name=VALUES(name), refresh_token=VALUES(refresh_token)
            """, (
                acc.get("id"),
                acc.get("email", ""),
                acc.get("name", ""),
                acc.get("picture", ""),
                acc.get("refresh_token", ""),
                acc.get("access_token", ""),
                acc.get("token_expiry", 0),
                acc.get("project_id", ""),
                acc.get("is_active", True),
                acc.get("is_primary", False),
                acc.get("requests_count", 0),
                acc.get("rate_limited_until", 0),
                acc.get("error_message", None),
                str(acc.get("last_used")) if acc.get("last_used") else None,
                acc.get("created_at", now),
                acc.get("updated_at", now)
            ))
        logger.info(f"Đã di chuyển thành công {len(data)} tài khoản từ accounts.json sang MySQL.")
    except Exception as e:
        logger.error(f"Lỗi di chuyển accounts.json sang MySQL: {e}")

def _migrate_skills():
    skills_file = BASE_DIR / "skills.json"
    row = fetch_one("SELECT COUNT(*) AS total FROM skills")
    if row and row["total"] > 0:
        return

    skills = []
    if skills_file.exists():
        try:
            data = json.loads(skills_file.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                skills = data
        except Exception as e:
            logger.error(f"Lỗi đọc skills.json: {e}")

    if not skills:
        from skill_manager import DEFAULT_SKILLS
        skills = DEFAULT_SKILLS

    for s in skills:
        execute("""
            INSERT INTO skills (
                id, user_id, name, system_prompt, is_default, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name=VALUES(name), system_prompt=VALUES(system_prompt), user_id=VALUES(user_id)
        """, (
            s.get("id"),
            s.get("user_id", None),
            s.get("name"),
            s.get("system_prompt", ""),
            s.get("is_default", False),
            s.get("created_at", ""),
            s.get("updated_at", "")
        ))
    logger.info(f"Đã di chuyển thành công {len(skills)} skills sang MySQL.")

def _migrate_settings():
    settings_file = BASE_DIR / "settings.json"
    if settings_file.exists():
        try:
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            now = time.time()
            for k, v in data.items():
                val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                execute("""
                    INSERT INTO settings (setting_key, setting_value, updated_at)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), updated_at=VALUES(updated_at)
                """, (k, val_str, now))
            logger.info("Đã di chuyển settings.json sang MySQL.")
        except Exception as e:
            logger.error(f"Lỗi di chuyển settings.json sang MySQL: {e}")

def _migrate_quota_logs():
    quota_db_path = BASE_DIR / "quota.db"
    row = fetch_one("SELECT COUNT(*) AS total FROM requests_log")
    if row and row["total"] > 0:
        return

    if not quota_db_path.exists():
        return

    try:
        conn = sqlite3.connect(quota_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM requests_log").fetchall()
        if rows:
            for r in rows:
                execute("""
                    INSERT INTO requests_log (
                        timestamp, account_id, account_email, model, 
                        prompt_tokens, completion_tokens, total_tokens, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    r["timestamp"],
                    r["account_id"],
                    r["account_email"],
                    r["model"],
                    r["prompt_tokens"],
                    r["completion_tokens"],
                    r["total_tokens"],
                    r["status"]
                ))
            logger.info(f"Đã di chuyển thành công {len(rows)} bản ghi tokens từ SQLite sang MySQL.")
        conn.close()
    except Exception as e:
        logger.error(f"Lỗi di chuyển quota.db sang MySQL: {e}")
