import time
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
import config

logger = logging.getLogger("antigravity-quota")
DB_PATH = config.BASE_DIR / "quota.db"

class QuotaTracker:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_sqlite_fallback()

    def _init_sqlite_fallback(self):
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS requests_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        account_id TEXT NOT NULL,
                        account_email TEXT NOT NULL,
                        model TEXT NOT NULL,
                        prompt_tokens INTEGER DEFAULT 0,
                        completion_tokens INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'success'
                    )
                """)
                conn.commit()
        except Exception:
            pass

    def record_usage(
        self,
        account_id: str,
        account_email: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        status: str = "success"
    ):
        if total_tokens <= 0:
            total_tokens = prompt_tokens + completion_tokens

        now = time.time()
        # 1. Lưu MySQL
        try:
            import db
            db.execute("""
                INSERT INTO requests_log 
                (timestamp, account_id, account_email, model, prompt_tokens, completion_tokens, total_tokens, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (now, account_id, account_email, model, prompt_tokens, completion_tokens, total_tokens, status))
            return
        except Exception as e:
            logger.error(f"Lỗi ghi log quota vào MySQL: {e}")

        # 2. Lưu SQLite backup
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute("""
                    INSERT INTO requests_log 
                    (timestamp, account_id, account_email, model, prompt_tokens, completion_tokens, total_tokens, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (now, account_id, account_email, model, prompt_tokens, completion_tokens, total_tokens, status))
                conn.commit()
        except Exception as e:
            logger.error(f"Lỗi ghi log quota vào SQLite: {e}")

    def get_stats(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        now = time.time()
        hour_cutoff = now - 3600             # 1 giờ qua
        day_cutoff = now - 86400            # 24 giờ qua
        week_cutoff = now - 7 * 86400       # 7 ngày qua
        month_cutoff = now - 30 * 86400     # 30 ngày qua

        # Thử đọc từ MySQL
        try:
            import db
            where_clause = "WHERE status = 'success'"
            params: List[Any] = []
            if account_id:
                where_clause += " AND account_id = %s"
                params.append(account_id)

            def query_window_mysql(cutoff: Optional[float]) -> Dict[str, int]:
                sub_where = where_clause
                sub_params = list(params)
                if cutoff is not None:
                    sub_where += " AND timestamp >= %s"
                    sub_params.append(cutoff)

                row = db.fetch_one(f"""
                    SELECT 
                        COUNT(*) as requests_count,
                        COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                        COALESCE(SUM(total_tokens), 0) as total_tokens
                    FROM requests_log
                    {sub_where}
                """, tuple(sub_params))

                if not row:
                    return {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

                return {
                    "requests": int(row.get("requests_count", 0)),
                    "prompt_tokens": int(row.get("prompt_tokens", 0)),
                    "completion_tokens": int(row.get("completion_tokens", 0)),
                    "total_tokens": int(row.get("total_tokens", 0))
                }

            stats = {
                "hour": query_window_mysql(hour_cutoff),
                "day": query_window_mysql(day_cutoff),
                "week": query_window_mysql(week_cutoff),
                "month": query_window_mysql(month_cutoff),
                "all_time": query_window_mysql(None),
                "by_account": {}
            }

            acc_rows = db.fetch_all("""
                SELECT 
                    account_id,
                    account_email,
                    COUNT(*) as total_reqs,
                    COALESCE(SUM(total_tokens), 0) as total_tokens
                FROM requests_log
                WHERE status = 'success'
                GROUP BY account_id, account_email
            """)

            for acc in acc_rows:
                aid = acc["account_id"]
                email = acc["account_email"]

                def query_acc_window_mysql(cutoff: Optional[float]) -> Dict[str, int]:
                    q = "SELECT COUNT(*) as reqs, COALESCE(SUM(total_tokens), 0) as tokens FROM requests_log WHERE status = 'success' AND account_id = %s"
                    p = [aid]
                    if cutoff is not None:
                        q += " AND timestamp >= %s"
                        p.append(cutoff)
                    r = db.fetch_one(q, tuple(p))
                    if not r:
                        return {"requests": 0, "tokens": 0}
                    return {"requests": int(r.get("reqs", 0)), "tokens": int(r.get("tokens", 0))}

                stats["by_account"][aid] = {
                    "account_id": aid,
                    "email": email,
                    "hour": query_acc_window_mysql(hour_cutoff),
                    "day": query_acc_window_mysql(day_cutoff),
                    "week": query_acc_window_mysql(week_cutoff),
                    "month": query_acc_window_mysql(month_cutoff),
                    "all_time": {
                        "requests": int(acc.get("total_reqs", 0)),
                        "tokens": int(acc.get("total_tokens", 0))
                    }
                }

            return stats
        except Exception as e:
            logger.debug(f"Chưa lấy stats từ MySQL, dùng SQLite fallback: {e}")

        # Fallback SQLite nếu MySQL chưa sẵn sàng
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.row_factory = sqlite3.Row
                where_clause = "WHERE status = 'success'"
                params: List[Any] = []
                if account_id:
                    where_clause += " AND account_id = ?"
                    params.append(account_id)

                def query_window_sqlite(cutoff: Optional[float]) -> Dict[str, int]:
                    sub_where = where_clause
                    sub_params = list(params)
                    if cutoff is not None:
                        sub_where += " AND timestamp >= ?"
                        sub_params.append(cutoff)

                    row = conn.execute(f"""
                        SELECT 
                            COUNT(*) as requests_count,
                            COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                            COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                            COALESCE(SUM(total_tokens), 0) as total_tokens
                        FROM requests_log
                        {sub_where}
                    """, sub_params).fetchone()

                    return {
                        "requests": row["requests_count"],
                        "prompt_tokens": row["prompt_tokens"],
                        "completion_tokens": row["completion_tokens"],
                        "total_tokens": row["total_tokens"]
                    }

                stats = {
                    "hour": query_window_sqlite(hour_cutoff),
                    "day": query_window_sqlite(day_cutoff),
                    "week": query_window_sqlite(week_cutoff),
                    "month": query_window_sqlite(month_cutoff),
                    "all_time": query_window_sqlite(None),
                    "by_account": {}
                }

                acc_rows = conn.execute("""
                    SELECT 
                        account_id,
                        account_email,
                        COUNT(*) as total_reqs,
                        COALESCE(SUM(total_tokens), 0) as total_tokens
                    FROM requests_log
                    WHERE status = 'success'
                    GROUP BY account_id, account_email
                """).fetchall()

                for acc in acc_rows:
                    aid = acc["account_id"]
                    email = acc["account_email"]

                    def query_acc_window_sqlite(cutoff: Optional[float]) -> Dict[str, int]:
                        q = "SELECT COUNT(*) as reqs, COALESCE(SUM(total_tokens), 0) as tokens FROM requests_log WHERE status = 'success' AND account_id = ?"
                        p = [aid]
                        if cutoff is not None:
                            q += " AND timestamp >= ?"
                            p.append(cutoff)
                        r = conn.execute(q, p).fetchone()
                        return {"requests": r["reqs"], "tokens": r["tokens"]}

                    stats["by_account"][aid] = {
                        "account_id": aid,
                        "email": email,
                        "hour": query_acc_window_sqlite(hour_cutoff),
                        "day": query_acc_window_sqlite(day_cutoff),
                        "week": query_acc_window_sqlite(week_cutoff),
                        "month": query_acc_window_sqlite(month_cutoff),
                        "all_time": {
                            "requests": acc["total_reqs"],
                            "tokens": acc["total_tokens"]
                        }
                    }

                return stats
        except Exception as e:
            logger.error(f"Lỗi đọc stats từ SQLite fallback: {e}")
            return {"hour": {}, "day": {}, "week": {}, "month": {}, "all_time": {}, "by_account": {}}

    def clear_logs(self):
        try:
            import db
            db.execute("DELETE FROM requests_log")
        except Exception:
            pass
        try:
            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                conn.execute("DELETE FROM requests_log")
                conn.commit()
        except Exception:
            pass

quota_tracker = QuotaTracker()
