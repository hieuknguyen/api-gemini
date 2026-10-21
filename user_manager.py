"""
User & Dedicated API Key Management Module
Quản lý Tài Khoản Người Dùng và Khóa API Riêng Biệt cho từng tài khoản:
- Lưu trữ chính vào MySQL (bảng `users` và `api_keys`)
- Tự động sao lưu dự phòng ra file JSON (users.json & api_keys.json)
- Tự động khởi tạo tài khoản mặc định kèm Master Key
- Hỗ trợ xác thực, kiểm tra trạng thái hoạt động (bật/tắt) và thống kê quota theo từng Key
"""

import json
import time
import uuid
import logging
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import config

logger = logging.getLogger("antigravity-users")

USERS_FILE = config.BASE_DIR / "users.json"
API_KEYS_FILE = config.BASE_DIR / "api_keys.json"


def hash_password(password: Optional[str]) -> Optional[str]:
    """Băm mật khẩu bằng thuật toán SHA-256 an toàn"""
    if not password or not str(password).strip():
        return None
    return hashlib.sha256(str(password).strip().encode("utf-8")).hexdigest()


class UserManager:
    def __init__(self):
        pass

    def _ensure_default_user_and_keys(self):
        """Không tự động tạo user mặc định - Người dùng tự quản lý tài khoản và key"""
        pass

    # ==================== DATABASE ACCESS ====================

    def _db_fetch_users(self) -> List[Dict[str, Any]]:
        try:
            import db
            rows = db.fetch_all("SELECT * FROM users ORDER BY created_at ASC")
            if rows:
                result = []
                for r in rows:
                    u = dict(r)
                    u["is_active"] = bool(u.get("is_active"))
                    u["role"] = str(u.get("role") or "user").strip().lower()
                    u["password"] = u.get("password")
                    u["balance"] = float(u.get("balance") or 0.0)
                    u["token_balance"] = int(u.get("token_balance") or 0)
                    result.append(u)
                return result
        except Exception as e:
            logger.debug(f"Không thể đọc users từ MySQL (dùng JSON fallback): {e}")

        # JSON fallback
        if USERS_FILE.exists():
            try:
                raw_users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                for u in raw_users:
                    u["role"] = str(u.get("role") or "user").strip().lower()
                    u["password"] = u.get("password")
                return raw_users
            except Exception:
                pass
        return []

    def _db_fetch_keys_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            import db
            rows = db.fetch_all("SELECT * FROM api_keys WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            if rows:
                result = []
                for r in rows:
                    k = dict(r)
                    k["is_active"] = bool(k.get("is_active"))
                    result.append(k)
                return result
        except Exception:
            pass

        # JSON fallback
        if API_KEYS_FILE.exists():
            try:
                all_keys = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                return [k for k in all_keys if k.get("user_id") == user_id]
            except Exception:
                pass
        return []

    def _db_save_user(self, user: Dict[str, Any]):
        try:
            import db
            db.execute("""
                INSERT INTO users (id, name, email, password, note, role, is_active, balance, token_balance, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name=VALUES(name), email=VALUES(email), password=VALUES(password),
                    note=VALUES(note), role=VALUES(role), is_active=VALUES(is_active),
                    balance=VALUES(balance), token_balance=VALUES(token_balance), updated_at=VALUES(updated_at)
            """, (
                user["id"], user["name"], user.get("email", ""), user.get("password"),
                user.get("note", ""), user.get("role", "user"), user.get("is_active", True),
                float(user.get("balance") or 0.0), int(user.get("token_balance") or 100000),
                user["created_at"], user.get("updated_at", user["created_at"])
            ))
        except Exception as e:
            logger.error(f"Lỗi lưu user vào MySQL: {e}")

        # Sync to JSON backup
        try:
            users = self._db_fetch_users()
            found = False
            for i, u in enumerate(users):
                if u["id"] == user["id"]:
                    users[i] = user
                    found = True
                    break
            if not found:
                users.append(user)
            USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _db_save_key(self, key_obj: Dict[str, Any]):
        try:
            import db
            db.execute("""
                INSERT INTO api_keys (id, user_id, key_value, name, is_active, requests_count, total_tokens, last_used_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    key_value=VALUES(key_value), name=VALUES(name), is_active=VALUES(is_active),
                    requests_count=VALUES(requests_count), total_tokens=VALUES(total_tokens),
                    last_used_at=VALUES(last_used_at)
            """, (
                key_obj["id"], key_obj["user_id"], key_obj["key_value"], key_obj["name"],
                key_obj.get("is_active", True), key_obj.get("requests_count", 0),
                key_obj.get("total_tokens", 0), key_obj.get("last_used_at"), key_obj["created_at"]
            ))
        except Exception as e:
            logger.error(f"Lỗi lưu key vào MySQL: {e}")

        # Sync to JSON backup
        try:
            all_keys = []
            if API_KEYS_FILE.exists():
                try:
                    all_keys = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                except Exception:
                    all_keys = []
            found = False
            for i, k in enumerate(all_keys):
                if k["id"] == key_obj["id"]:
                    all_keys[i] = key_obj
                    found = True
                    break
            if not found:
                all_keys.append(key_obj)
            API_KEYS_FILE.write_text(json.dumps(all_keys, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ==================== PUBLIC API METHODS ====================

    def get_users(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các tài khoản kèm các API Key thuộc về từng tài khoản"""
        users = self._db_fetch_users()
        for u in users:
            keys = self._db_fetch_keys_for_user(u["id"])
            u["keys"] = keys
            u["total_keys"] = len(keys)
            u["total_requests"] = sum(k.get("requests_count", 0) for k in keys)
            u["total_tokens"] = sum(k.get("total_tokens", 0) for k in keys)
        return users

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        users = self._db_fetch_users()
        for u in users:
            if u["id"] == user_id:
                u["keys"] = self._db_fetch_keys_for_user(user_id)
                return u
        return None

    def is_admin(self, user_id: str) -> bool:
        if not user_id:
            return False
        user = self.get_user(user_id)
        if user and user.get("is_active", True) and user.get("role") == "admin":
            return True
        return False

    def create_user(self, name: str, email: str = "", password: Optional[str] = None, note: str = "", role: str = "user") -> Dict[str, Any]:
        """Tạo một tài khoản người dùng / dự án mới"""
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        clean_role = str(role or "user").strip().lower()
        if clean_role not in ("admin", "user"):
            clean_role = "user"
        hashed_pass = hash_password(password)
        new_user = {
            "id": user_id,
            "name": name.strip(),
            "email": (email or "").strip(),
            "password": hashed_pass,
            "note": (note or "").strip(),
            "role": clean_role,
            "is_active": True,
            "balance": 0.0,
            "token_balance": 100000,
            "created_at": now,
            "updated_at": now,
            "keys": [],
            "total_keys": 0,
            "total_requests": 0,
            "total_tokens": 0
        }
        self._db_save_user(new_user)
        logger.info(f"Đã tạo tài khoản mới: {new_user['name']} (ID: {user_id}, Role: {clean_role})")
        return new_user

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user = self.get_user(user_id)
        if not user:
            return None
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        if "name" in updates and updates["name"] is not None:
            user["name"] = str(updates["name"]).strip()
        if "email" in updates and updates["email"] is not None:
            user["email"] = str(updates["email"]).strip()
        if "password" in updates and updates["password"] is not None:
            pwd = str(updates["password"]).strip()
            user["password"] = hash_password(pwd) if pwd else None
        if "note" in updates and updates["note"] is not None:
            user["note"] = str(updates["note"]).strip()
        if "role" in updates and updates["role"] is not None:
            clean_role = str(updates["role"]).strip().lower()
            if clean_role in ("admin", "user"):
                user["role"] = clean_role
        if "is_active" in updates and updates["is_active"] is not None:
            user["is_active"] = bool(updates["is_active"])
        user["updated_at"] = now
        self._db_save_user(user)
        return user

    def authenticate(self, email_or_name: str, password: str) -> Optional[Dict[str, Any]]:
        """Xác thực người dùng qua Email hoặc Tên người dùng kèm Mật khẩu"""
        if not email_or_name or not password:
            return None
        target = email_or_name.strip().lower()
        pwd = str(password).strip()
        pwd_hash = hash_password(pwd)
        users = self.get_users()
        for u in users:
            u_email = (u.get("email") or "").strip().lower()
            u_name = (u.get("name") or "").strip().lower()
            u_id = (u.get("id") or "").strip().lower()
            if target in (u_email, u_name, u_id):
                user_pwd = u.get("password")
                if user_pwd and (user_pwd == pwd or user_pwd == pwd_hash):
                    # Tự động nâng cấp mật khẩu cũ dạng rõ sang SHA-256
                    if user_pwd == pwd and user_pwd != pwd_hash:
                        try:
                            self.update_user(u["id"], {"password": pwd})
                            logger.info(f"Đã tự động nâng cấp mật khẩu sang SHA-256 cho tài khoản '{u.get('name')}'")
                        except Exception:
                            pass
                    if not u.get("is_active", True):
                        logger.warning(f"Đăng nhập thất bại: Tài khoản '{u.get('name')}' đang bị vô hiệu hóa.")
                        return None
                    return u
        return None

    def get_user_by_email_or_name(self, email_or_name: str) -> Optional[Dict[str, Any]]:
        """Tìm kiếm người dùng theo địa chỉ email hoặc tên người dùng (không phân biệt hoa thường)"""
        if not email_or_name:
            return None
        target = email_or_name.strip().lower()
        users = self._db_fetch_users()
        for u in users:
            u_email = (u.get("email") or "").strip().lower()
            u_name = (u.get("name") or "").strip().lower()
            if u_email == target or u_name == target:
                return u
        return None

    def ensure_admin_account(self):
        """
        Đảm bảo tài khoản Admin được cấu hình qua ADMIN_EMAIL và ADMIN_PASSWORD.
        """
        target_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        target_pass = os.getenv("ADMIN_PASSWORD", "").strip()
        if not target_email or len(target_pass) < 20:
            logger.error("Cần đặt ADMIN_EMAIL và ADMIN_PASSWORD (ít nhất 20 ký tự) để khởi tạo tài khoản Admin.")
            return

        try:
            users = self.get_users()
            admin_user = None
            for u in users:
                if (u.get("email") or "").strip().lower() == target_email:
                    admin_user = u
                    break

            if admin_user:
                admin_id = admin_user["id"]
                updates = {
                    "role": "admin",
                    "is_active": True
                }
                if not admin_user.get("password"):
                    updates["password"] = target_pass
                self.update_user(admin_id, updates)
            else:
                new_admin = self.create_user(
                    name=os.getenv("ADMIN_NAME", "API Gemini Admin"),
                    email=target_email,
                    password=target_pass,
                    note="API Gemini administrator",
                    role="admin"
                )
                admin_id = new_admin["id"]

            # Đảm bảo tài khoản admin có ít nhất 1 API Key đang hoạt động
            keys = self._db_fetch_keys_for_user(admin_id)
            active_keys = [k for k in keys if k.get("is_active", True)]
            target_key = config.API_KEY or config.generate_random_api_key()
            if not active_keys:
                self.create_api_key(admin_id, name="Admin API Key", custom_key=target_key)
            else:
                config.API_KEY = active_keys[0]["key_value"]

            # Đảm bảo các tài khoản khác không còn giữ quyền admin (hạ xuống role user an toàn)
            for u in users:
                if u["id"] != admin_id and u.get("role") == "admin":
                    logger.info(f"Hạ quyền tài khoản '{u.get('name')}' ({u['id']}) từ admin xuống user để chuyển admin cho {target_email}")
                    self.update_user(u["id"], {"role": "user"})

            logger.info(f"Đã đảm bảo tài khoản Admin: {target_email}")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo tài khoản admin: {e}")

    def get_admin_user(self) -> Optional[Dict[str, Any]]:
        """Lấy thông tin tài khoản Admin hệ thống"""
        try:
            import db
            row = db.fetch_one("SELECT * FROM users WHERE role = 'admin' ORDER BY created_at ASC LIMIT 1")
            if row:
                u = dict(row)
                u["is_active"] = bool(u.get("is_active"))
                u["role"] = "admin"
                return u
        except Exception:
            pass
        for u in self._db_fetch_users():
            if u.get("role") == "admin":
                return u
        return None

    def delete_user(self, user_id: str) -> bool:
        """Xóa tài khoản và toàn bộ các API Key của tài khoản đó"""
        try:
            import db
            db.execute("DELETE FROM api_keys WHERE user_id = %s", (user_id,))
            db.execute("DELETE FROM users WHERE id = %s", (user_id,))
        except Exception as e:
            logger.error(f"Lỗi xóa user {user_id} trong MySQL: {e}")

        # Đồng bộ JSON
        try:
            users = [u for u in self._db_fetch_users() if u["id"] != user_id]
            USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")
            if API_KEYS_FILE.exists():
                all_keys = [k for k in json.loads(API_KEYS_FILE.read_text(encoding="utf-8")) if k.get("user_id") != user_id]
                API_KEYS_FILE.write_text(json.dumps(all_keys, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        logger.info(f"Đã xóa tài khoản {user_id} và các key liên quan")
        return True

    # ==================== API KEY METHODS ====================

    def get_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin 1 API Key theo ID (bao gồm cả user_id sở hữu)"""
        if not key_id:
            return None
        try:
            import db
            row = db.fetch_one("SELECT * FROM api_keys WHERE id = %s", (key_id,))
            if row:
                k = dict(row)
                k["is_active"] = bool(k.get("is_active"))
                return k
        except Exception:
            pass

        # JSON fallback
        if API_KEYS_FILE.exists():
            try:
                all_keys = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                for k in all_keys:
                    if k.get("id") == key_id:
                        k_copy = dict(k)
                        k_copy["is_active"] = bool(k_copy.get("is_active", True))
                        return k_copy
            except Exception:
                pass
        return None

    def get_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Lấy danh sách API Key của 1 user (đảm bảo đúng 1 key duy nhất)"""
        keys = self._db_fetch_keys_for_user(user_id)
        if not keys:
            user = self.get_user(user_id)
            if user:
                new_k = self.create_api_key(user_id, name=f"Key - {user.get('name', 'User')}")
                return [new_k]
            return []
        if len(keys) > 1:
            # Dọn dẹp key dư thừa, giữ lại key đầu tiên
            main_k = keys[0]
            for extra in keys[1:]:
                self.delete_api_key(extra["id"])
            return [main_k]
        return keys

    def create_api_key(self, user_id: str, name: str = "", custom_key: Optional[str] = None) -> Dict[str, Any]:
        """Tạo hoặc đổi API Key duy nhất cho một tài khoản cụ thể (1 tài khoản = 1 key duy nhất)"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"Không tìm thấy tài khoản với ID: {user_id}")

        key_value = (custom_key or "").strip()
        if not key_value:
            key_value = config.generate_random_api_key()

        # Kiểm tra trùng key với tài khoản khác
        try:
            import db
            existing = db.fetch_one("SELECT id, user_id FROM api_keys WHERE key_value = %s", (key_value,))
            if existing and existing.get("user_id") != user_id:
                raise ValueError("Mã API Key này đã được sử dụng cho tài khoản khác, vui lòng chọn mã khác!")
        except ValueError:
            raise
        except Exception:
            pass

        now = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1 tài khoản chỉ được 1 key duy nhất: Nếu đã có key thì cập nhật đè lên key đó
        existing_keys = self._db_fetch_keys_for_user(user_id)
        if existing_keys:
            target_obj = existing_keys[0]
            target_obj["key_value"] = key_value
            target_obj["name"] = name.strip() or target_obj.get("name") or f"Key {user['name']}"
            target_obj["is_active"] = True
            self._db_save_key(target_obj)
            # Xóa các key thừa khác nếu có
            for extra_k in existing_keys[1:]:
                self.delete_api_key(extra_k["id"])
            ret_key = target_obj
        else:
            key_id = f"key_{uuid.uuid4().hex[:8]}"
            new_key = {
                "id": key_id,
                "user_id": user_id,
                "key_value": key_value,
                "name": name.strip() or f"Key {user['name']}",
                "is_active": True,
                "requests_count": 0,
                "total_tokens": 0,
                "last_used_at": None,
                "created_at": now
            }
            self._db_save_key(new_key)
            ret_key = new_key

        # Nếu là tài khoản Admin, đồng bộ luôn config.API_KEY và bảng settings
        if user.get("role") == "admin":
            config.API_KEY = key_value
            try:
                import db
                db.execute("UPDATE settings SET setting_value = %s WHERE setting_key = 'api_key'", (key_value,))
                p = config.get_persisted_settings()
                p["api_key"] = key_value
                config.save_persisted_settings(p)
                config.update_env_file("API_KEY", key_value)
            except Exception:
                pass

        logger.info(f"Đã cập nhật API Key duy nhất cho tài khoản {user['name']}: {key_value}")
        return ret_key

    def toggle_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Bật hoặc tạm dừng một API Key"""
        try:
            import db
            k = db.fetch_one("SELECT * FROM api_keys WHERE id = %s", (key_id,))
            if k:
                new_state = not bool(k["is_active"])
                db.execute("UPDATE api_keys SET is_active = %s WHERE id = %s", (new_state, key_id))
                k["is_active"] = new_state
                # Sync JSON
                if API_KEYS_FILE.exists():
                    try:
                        all_keys = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                        for item in all_keys:
                            if item["id"] == key_id:
                                item["is_active"] = new_state
                                break
                        API_KEYS_FILE.write_text(json.dumps(all_keys, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
                logger.info(f"Đã đổi trạng thái Key {key_id} sang: {'Bật' if new_state else 'Tạm dừng'}")
                return dict(k)
        except Exception as e:
            logger.error(f"Lỗi toggle key {key_id}: {e}")
        return None

    def delete_api_key(self, key_id: str) -> bool:
        """Xóa một API Key"""
        try:
            import db
            db.execute("DELETE FROM api_keys WHERE id = %s", (key_id,))
        except Exception as e:
            logger.error(f"Lỗi xóa key {key_id} trong MySQL: {e}")

        # Sync JSON
        if API_KEYS_FILE.exists():
            try:
                all_keys = [k for k in json.loads(API_KEYS_FILE.read_text(encoding="utf-8")) if k.get("id") != key_id]
                API_KEYS_FILE.write_text(json.dumps(all_keys, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        logger.info(f"Đã xóa API Key {key_id}")
        return True

    # ==================== AUTHENTICATION & USAGE TRACKING ====================

    def validate_api_key(self, token: Optional[str]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Xác thực tính hợp lệ của token khi client gửi request.
        Returns: (is_valid, user_info, key_info)
        """
        if not token:
            return False, None, None
        token = token.strip()

        # 0. Kiểm tra trực tiếp với config.API_KEY của hệ thống (Master Admin Key)
        if config.API_KEY and token == config.API_KEY.strip():
            admin_user = self.get_admin_user()
            if admin_user and admin_user.get("is_active", True):
                return True, {
                    "id": admin_user["id"],
                    "name": admin_user["name"],
                    "role": "admin",
                    "token_balance": 999999999999,
                    "balance": float(admin_user.get("balance") or 0.0)
                }, {"id": "master_key", "name": "Admin Master Key"}

        # 1. Tra cứu trong bảng api_keys (có kèm kiểm tra tài khoản user có active không)
        try:
            import db
            row = db.fetch_one("""
                SELECT k.id as key_id, k.name as key_name, k.key_value, k.is_active as key_active,
                       u.id as user_id, u.name as user_name, u.role as user_role, u.is_active as user_active,
                       u.token_balance as token_balance, u.balance as balance
                FROM api_keys k
                JOIN users u ON k.user_id = u.id
                WHERE k.key_value = %s
            """, (token,))
            if row:
                if not row["user_active"]:
                    logger.warning(f"Tài khoản '{row['user_name']}' đang bị vô hiệu hóa.")
                    return False, None, None
                if not row["key_active"]:
                    logger.warning(f"API Key '{row['key_name']}' đang bị tạm dừng.")
                    return False, None, None
                user_role = str(row.get("user_role") or "user").strip().lower()
                tok_bal = int(row.get("token_balance") or 0) if user_role != "admin" else 999999999999
                return True, {
                    "id": row["user_id"],
                    "name": row["user_name"],
                    "role": user_role,
                    "token_balance": tok_bal,
                    "balance": float(row.get("balance") or 0.0)
                }, {"id": row["key_id"], "name": row["key_name"]}
        except Exception:
            pass

        # 2. Kiểm tra JSON fallback
        if API_KEYS_FILE.exists():
            try:
                all_keys = json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
                for k in all_keys:
                    if k.get("key_value") == token:
                        if not k.get("is_active", True):
                            return False, None, None
                        # Kiểm tra tài khoản user trong users.json nếu có
                        user_name = "User"
                        user_role = "user"
                        tok_bal = 100000
                        bal = 0.0
                        if USERS_FILE.exists():
                            users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                            user_obj = next((u for u in users if u.get("id") == k.get("user_id")), None)
                            if user_obj:
                                if not user_obj.get("is_active", True):
                                    return False, None, None
                                user_name = user_obj.get("name", "User")
                                user_role = str(user_obj.get("role") or "user").strip().lower()
                                tok_bal = int(user_obj.get("token_balance", 100000))
                                bal = float(user_obj.get("balance", 0.0))
                        return True, {
                            "id": k.get("user_id"),
                            "name": user_name,
                            "role": user_role,
                            "token_balance": tok_bal,
                            "balance": bal
                        }, k
            except Exception:
                pass

        return False, None, None

    def add_user_tokens(self, user_id: str, tokens: int, amount: float = 0.0) -> bool:
        """Cộng token (và cập nhật số dư nếu có) cho người dùng khi thanh toán MoMo thành công"""
        try:
            import db
            db.execute("""
                UPDATE users 
                SET token_balance = token_balance + %s,
                    balance = balance + %s,
                    updated_at = %s
                WHERE id = %s
            """, (tokens, amount, time.strftime("%Y-%m-%d %H:%M:%S"), user_id))
            logger.info(f"Đã nạp thành công {tokens:,} tokens cho User {user_id}")
            return True
        except Exception as e:
            logger.error(f"Lỗi nạp token cho user {user_id}: {e}")
            return False

    def deduct_user_tokens(self, user_id: str, tokens: int) -> bool:
        """Trừ token tiêu thụ từ tài khoản người dùng"""
        try:
            import db
            db.execute("""
                UPDATE users 
                SET token_balance = GREATEST(0, token_balance - %s),
                    updated_at = %s
                WHERE id = %s
            """, (tokens, time.strftime("%Y-%m-%d %H:%M:%S"), user_id))
            return True
        except Exception as e:
            logger.error(f"Lỗi trừ token của user {user_id}: {e}")
            return False

    def check_user_token_quota(self, user_id: str, role: str = "user") -> Tuple[bool, int]:
        """Kiểm tra xem user có đủ token để gọi AI không (Admin luôn đủ)"""
        if role == "admin":
            return True, 999999999999
        try:
            import db
            row = db.fetch_one("SELECT token_balance FROM users WHERE id = %s", (user_id,))
            if row:
                bal = int(row.get("token_balance") or 0)
                return bal > 0, bal
        except Exception:
            pass
        return True, 100000

    def record_usage(self, token: Optional[str], total_tokens: int = 0):
        """Cập nhật số lượt gọi và lượng tokens tiêu thụ cho Key tương ứng và trừ token balance của user"""
        if not token:
            return
        token = token.strip()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            import db
            # 1. Cập nhật thống kê Key
            db.execute("""
                UPDATE api_keys
                SET requests_count = requests_count + 1,
                    total_tokens = total_tokens + %s,
                    last_used_at = %s
                WHERE key_value = %s
            """, (total_tokens, now, token))

            # 2. Nếu là user thường, trừ trực tiếp token_balance của user sở hữu key
            if total_tokens > 0:
                key_row = db.fetch_one("SELECT user_id FROM api_keys WHERE key_value = %s", (token,))
                if key_row and key_row.get("user_id"):
                    u_id = key_row["user_id"]
                    u_row = db.fetch_one("SELECT role FROM users WHERE id = %s", (u_id,))
                    if u_row and str(u_row.get("role") or "").lower() == "user":
                        self.deduct_user_tokens(u_id, total_tokens)
        except Exception as e:
            logger.error(f"Lỗi ghi nhận usage cho token: {e}")


# Singleton instance
user_manager = UserManager()
