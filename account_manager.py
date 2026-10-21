import json
import time
import uuid
import socket
import threading
import logging
import urllib.parse
import http.server
from typing import List, Dict, Any, Optional, Tuple
import requests
import config

logger = logging.getLogger("antigravity-accounts")

def format_duration(seconds: int) -> str:
    """Chuyển đổi giây thành định dạng giờ/phút/giây dễ đọc."""
    if seconds <= 0:
        return "0 giây"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0:
        parts.append(f"{h} giờ")
    if m > 0:
        parts.append(f"{m} phút")
    if s > 0 or not parts:
        parts.append(f"{s} giây")
    return " ".join(parts)

class ReusableHTTPServer(http.server.HTTPServer):
    allow_reuse_address = True

class AccountManager:
    def __init__(self):
        self.accounts_file = config.ACCOUNTS_FILE
        self.lock = threading.Lock()
        self.round_robin_index = 0
        self.strategy = config.STRATEGY
        self.oauth_server: Optional[http.server.HTTPServer] = None
        self.oauth_stop_event: Optional[threading.Event] = None
        self.oauth_state: Dict[str, Any] = {}
        self.last_selected_port: Optional[int] = None
        self.last_redirect_uri: Optional[str] = None
        self._ensure_file()

    def _ensure_file(self):
        if not self.accounts_file.exists():
            self.accounts_file.write_text("[]", encoding="utf-8")

    def load_accounts(self) -> List[Dict[str, Any]]:
        # 1. Đọc từ MySQL trước
        try:
            import db
            rows = db.fetch_all("SELECT * FROM accounts ORDER BY is_primary DESC, created_at ASC")
            if rows is not None and len(rows) > 0:
                accounts = []
                for r in rows:
                    acc = dict(r)
                    acc["is_active"] = bool(acc.get("is_active"))
                    acc["is_primary"] = bool(acc.get("is_primary"))
                    accounts.append(acc)
                return accounts
        except Exception as e:
            logger.debug(f"Chưa đọc được từ MySQL (có thể đang khởi động): {e}")

        # 2. Fallback file accounts.json
        with self.lock:
            try:
                data = json.loads(self.accounts_file.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception as e:
                logger.error(f"Lỗi đọc file accounts.json: {e}")
                return []

    def save_accounts(self, accounts: List[Dict[str, Any]]):
        # 1. Lưu vào MySQL
        try:
            import db
            now = time.time()
            for acc in accounts:
                db.execute("""
                    INSERT INTO accounts (
                        id, email, name, picture, refresh_token, access_token, 
                        token_expiry, project_id, is_active, is_primary, requests_count, 
                        rate_limited_until, error_message, last_used, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        email=VALUES(email), name=VALUES(name), picture=VALUES(picture),
                        refresh_token=VALUES(refresh_token), access_token=VALUES(access_token),
                        token_expiry=VALUES(token_expiry), project_id=VALUES(project_id),
                        is_active=VALUES(is_active), is_primary=VALUES(is_primary),
                        requests_count=VALUES(requests_count), rate_limited_until=VALUES(rate_limited_until),
                        error_message=VALUES(error_message), last_used=VALUES(last_used), updated_at=VALUES(updated_at)
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
                    acc.get("last_used", 0) if isinstance(acc.get("last_used"), (int, float)) else 0,
                    acc.get("created_at", now),
                    now
                ))
        except Exception as e:
            logger.error(f"Lỗi lưu accounts vào MySQL: {e}")

        # 2. Đồng thời lưu backup ra accounts.json
        with self.lock:
            try:
                self.accounts_file.write_text(json.dumps(accounts, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.error(f"Lỗi ghi file accounts.json: {e}")

    def get_accounts_public(self) -> List[Dict[str, Any]]:
        accounts = self.load_accounts()
        now = time.time()
        res = []
        for acc in accounts:
            rate_limited_until = acc.get("rate_limited_until", 0)
            cooldown_left = max(0, int(rate_limited_until - now)) if rate_limited_until > now else 0
            res.append({
                "id": acc.get("id"),
                "email": acc.get("email"),
                "name": acc.get("name"),
                "picture": acc.get("picture"),
                "project_id": acc.get("project_id"),
                "is_active": acc.get("is_active", True),
                "is_primary": acc.get("is_primary", False),
                "is_rate_limited": cooldown_left > 0,
                "cooldown_left": cooldown_left,
                "requests_count": acc.get("requests_count", 0),
                "last_used": acc.get("last_used"),
                "error_message": acc.get("error_message")
            })
        return res

    def get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        try:
            import db
            r = db.fetch_one("SELECT * FROM accounts WHERE id = %s", (account_id,))
            if r:
                acc = dict(r)
                acc["is_active"] = bool(acc.get("is_active"))
                acc["is_primary"] = bool(acc.get("is_primary"))
                return acc
        except Exception:
            pass

        accounts = self.load_accounts()
        for acc in accounts:
            if acc.get("id") == account_id:
                return acc
        return None

    def get_available_account(self, custom_strategy: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], int]:
        accounts = self.load_accounts()
        now = time.time()
        active_accounts = [a for a in accounts if a.get("is_active", True)]
        if not active_accounts:
            return None, 0

        # Phân loại tài khoản sẵn sàng vs rate limited
        ready_accounts = []
        min_cooldown = float("inf")
        for a in active_accounts:
            rate_limited_until = a.get("rate_limited_until", 0)
            if rate_limited_until <= now:
                ready_accounts.append(a)
            else:
                left = int(rate_limited_until - now)
                if left < min_cooldown:
                    min_cooldown = left

        if not ready_accounts:
            # Nếu thời gian chờ ngắn (<= 15s), tự động chờ rồi thử lại để tránh báo lỗi gián đoạn Codex/user
            wait_time = max(1, int(min_cooldown)) if min_cooldown != float("inf") else 8
            if wait_time <= 15:
                logger.info(f"Tất cả tài khoản Google đang trong cooldown, tự động chờ {wait_time}s để phục hồi...")
                time.sleep(wait_time)
                return self.get_available_account(custom_strategy)
            return None, wait_time

        strategy = custom_strategy or self.strategy
        if strategy == "round_robin" and len(ready_accounts) > 1:
            self.round_robin_index = (self.round_robin_index + 1) % len(ready_accounts)
            return ready_accounts[self.round_robin_index], 0

        # Mặc định failover: ưu tiên tài khoản primary, sau đó lần lượt
        ready_accounts.sort(key=lambda a: (not a.get("is_primary", False), a.get("requests_count", 0)))
        return ready_accounts[0], 0

    def mark_rate_limited(self, account_id: str, duration_seconds: int = 300, error_message: str = "Rate limit / Quota exhausted"):
        now = time.time()
        until = now + duration_seconds
        try:
            import db
            db.execute("UPDATE accounts SET rate_limited_until = %s, error_message = %s WHERE id = %s", (until, error_message, account_id))
        except Exception:
            pass

        accounts = self.load_accounts()
        for acc in accounts:
            if acc.get("id") == account_id:
                acc["rate_limited_until"] = until
                acc["error_message"] = error_message
                logger.warning(f"Tài khoản {acc.get('email')} bị rate limit, cooldown {format_duration(duration_seconds)}")
                break
        self.save_accounts(accounts)

    def report_success(self, account_id: str):
        now = time.time()
        try:
            import db
            db.execute("""
                UPDATE accounts 
                SET requests_count = requests_count + 1, last_used = %s, error_message = NULL, rate_limited_until = 0 
                WHERE id = %s
            """, (now, account_id))
        except Exception:
            pass

        accounts = self.load_accounts()
        for acc in accounts:
            if acc.get("id") == account_id:
                acc["requests_count"] = acc.get("requests_count", 0) + 1
                acc["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
                acc["error_message"] = None
                acc["rate_limited_until"] = 0
                break
        self.save_accounts(accounts)

    def toggle_account(self, account_id: str) -> bool:
        new_state = True
        try:
            import db
            db.execute("UPDATE accounts SET is_active = NOT is_active WHERE id = %s", (account_id,))
            r = db.fetch_one("SELECT is_active FROM accounts WHERE id = %s", (account_id,))
            if r:
                new_state = bool(r["is_active"])
                # Đồng bộ JSON backup
                with self.lock:
                    try:
                        if self.accounts_file.exists():
                            data = json.loads(self.accounts_file.read_text(encoding="utf-8"))
                            for a in data:
                                if a.get("id") == account_id:
                                    a["is_active"] = new_state
                                    break
                            self.accounts_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass
                return new_state
        except Exception as e:
            logger.error(f"Lỗi toggle account trong MySQL: {e}")

        # Fallback nếu không có MySQL
        accounts = self.load_accounts()
        for acc in accounts:
            if acc.get("id") == account_id:
                acc["is_active"] = not acc.get("is_active", True)
                new_state = acc["is_active"]
                break
        self.save_accounts(accounts)
        return new_state

    def reset_cooldown(self, account_id: str):
        try:
            import db
            db.execute("UPDATE accounts SET rate_limited_until = 0, error_message = NULL WHERE id = %s", (account_id,))
        except Exception:
            pass

        accounts = self.load_accounts()
        for acc in accounts:
            if acc.get("id") == account_id:
                acc["rate_limited_until"] = 0
                acc["error_message"] = None
                break
        self.save_accounts(accounts)

    def set_primary(self, account_id: str):
        try:
            import db
            db.execute("UPDATE accounts SET is_primary = FALSE")
            db.execute("UPDATE accounts SET is_primary = TRUE WHERE id = %s", (account_id,))
        except Exception:
            pass

        accounts = self.load_accounts()
        for acc in accounts:
            acc["is_primary"] = (acc.get("id") == account_id)
        self.save_accounts(accounts)

    def delete_account(self, account_id: str):
        try:
            import db
            db.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
        except Exception:
            pass

        accounts = self.load_accounts()
        accounts = [a for a in accounts if a.get("id") != account_id]
        if accounts and not any(a.get("is_primary") for a in accounts):
            accounts[0]["is_primary"] = True
            try:
                import db
                db.execute("UPDATE accounts SET is_primary = TRUE WHERE id = %s", (accounts[0]["id"],))
            except Exception:
                pass
        self.save_accounts(accounts)

    def fetch_user_info(self, access_token: str) -> Dict[str, Any]:
        try:
            res = requests.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            logger.warning(f"Lỗi lấy thông tin userinfo: {e}")
        return {}

    def resolve_project_id(self, access_token: str) -> str:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            **config.ANTIGRAVITY_HEADERS
        }
        for endpoint in config.ENDPOINTS:
            try:
                res = requests.post(
                    f"{endpoint}/v1internal:loadCodeAssist",
                    headers=headers,
                    json={"metadata": {"ideType": "IDE_UNSPECIFIED", "platform": "PLATFORM_UNSPECIFIED", "pluginType": "GEMINI"}},
                    timeout=10
                )
                if res.status_code == 200:
                    proj = res.json().get("cloudaicompanionProject")
                    if isinstance(proj, dict):
                        return proj.get("id", "aicode-consumers")
                    elif isinstance(proj, str):
                        return proj
                elif res.status_code == 404:
                    continue
            except Exception:
                pass
        return "aicode-consumers"

    def add_or_update_account(self, refresh_token: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        token_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
            },
            timeout=15
        )
        if token_res.status_code != 200:
            raise ValueError(f"Refresh Token không hợp lệ ({token_res.status_code}): {token_res.text}")

        tokens = token_res.json()
        access_token = tokens["access_token"]
        userinfo = self.fetch_user_info(access_token)
        project_id = self.resolve_project_id(access_token)

        email = userinfo.get("email") or f"user_{uuid.uuid4().hex[:6]}@gmail.com"
        name = custom_name or userinfo.get("name") or email.split("@")[0]
        picture = userinfo.get("picture")

        accounts = self.load_accounts()
        existing = None
        for a in accounts:
            if a.get("email") == email or a.get("refresh_token") == refresh_token:
                existing = a
                break

        if existing:
            existing["refresh_token"] = refresh_token
            existing["name"] = name
            existing["picture"] = picture or existing.get("picture")
            existing["project_id"] = project_id
            existing["is_active"] = True
            existing["error_message"] = None
            account_data = existing
        else:
            is_first = len(accounts) == 0
            account_data = {
                "id": f"acc_{uuid.uuid4().hex[:12]}",
                "email": email,
                "name": name,
                "picture": picture,
                "refresh_token": refresh_token,
                "project_id": project_id,
                "is_active": True,
                "is_primary": is_first,
                "rate_limited_until": 0,
                "requests_count": 0,
                "last_used": None,
                "error_message": None
            }
            accounts.append(account_data)

        self.save_accounts(accounts)
        return account_data

    def exchange_code_or_url(self, raw_input: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Nhận vào raw_input có thể là:
        1. URL callback hoàn chỉnh (ví dụ: http://localhost:51122/oauth-callback?code=4/0A...&scope=...)
        2. Mã authorization code trực tiếp (bắt đầu bằng 4/...)
        3. Refresh token trực tiếp (bắt đầu bằng 1//...)
        Tự động nhận diện và hoàn tất thêm hoặc cập nhật tài khoản Google.
        """
        raw_input = (raw_input or "").strip()
        if not raw_input:
            raise ValueError("Chuỗi nhập vào không được để trống")

        # Trường hợp 1: Dán URL callback hoàn chỉnh hoặc chứa 'code='
        if "http://" in raw_input or "https://" in raw_input or "code=" in raw_input:
            try:
                if "http" in raw_input:
                    parsed = urllib.parse.urlparse(raw_input)
                    qs = urllib.parse.parse_qs(parsed.query)
                    error = qs.get("error", [None])[0]
                    if error:
                        raise ValueError(f"Google thông báo lỗi xác thực: {error}")
                    code = qs.get("code", [None])[0]
                    redirect_uri = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                else:
                    qs = urllib.parse.parse_qs(raw_input)
                    code = qs.get("code", [None])[0]
                    redirect_uri = self.last_redirect_uri or f"http://localhost:{config.OAUTH_PORTS[0]}/oauth-callback"

                if not code:
                    raise ValueError("Không tìm thấy mã xác thực 'code' trong đường dẫn URL đã dán")

                acc = self.exchange_oauth_code(code, redirect_uri, custom_name)
                self._stop_oauth_listener_if_running()
                return acc
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"Không thể xử lý URL callback: {e}")

        # Trường hợp 2: Bắt đầu bằng '4/' (Google OAuth Authorization Code)
        if raw_input.startswith("4/"):
            candidate_uris = []
            if self.last_redirect_uri:
                candidate_uris.append(self.last_redirect_uri)
            for p in config.OAUTH_PORTS:
                uri = f"http://localhost:{p}/oauth-callback"
                if uri not in candidate_uris:
                    candidate_uris.append(uri)

            last_error = None
            for uri in candidate_uris:
                try:
                    acc = self.exchange_oauth_code(raw_input, uri, custom_name)
                    self._stop_oauth_listener_if_running()
                    return acc
                except Exception as ex:
                    last_error = ex
            raise ValueError(f"Không thể đổi Authorization Code thành Refresh Token: {last_error}")

        # Trường hợp 3: Refresh Token (hoặc chuỗi token thông thường)
        return self.add_or_update_account(raw_input, custom_name)

    def exchange_oauth_code(self, code: str, redirect_uri: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """Đổi Authorization Code lấy Refresh Token từ máy chủ Google OAuth"""
        code = urllib.parse.unquote(code.strip())
        t_res = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
            },
            timeout=15
        )
        if t_res.status_code != 200:
            raise ValueError(f"Google từ chối mã xác thực ({t_res.status_code}): {t_res.text}")

        t_data = t_res.json()
        refresh_token = t_data.get("refresh_token")
        if not refresh_token:
            raise ValueError("Google không trả về Refresh Token (có thể do tài khoản đã cấp quyền trước đó). Hãy đăng nhập lại với tùy chọn cấp quyền đầy đủ.")

        return self.add_or_update_account(refresh_token, custom_name)

    def _stop_oauth_listener_if_running(self):
        """Dừng server listener cục bộ nếu đang chạy ngầm khi đã xác thực xong"""
        try:
            if hasattr(self, "oauth_stop_event") and self.oauth_stop_event:
                self.oauth_stop_event.set()
            if hasattr(self, "oauth_server") and self.oauth_server:
                self.oauth_server.server_close()
                self.oauth_server = None
        except Exception:
            pass

    def start_oauth_flow(self, host: str = "0.0.0.0") -> Dict[str, Any]:
        # Clean up any previous oauth server if still active
        self._stop_oauth_listener_if_running()
        time.sleep(0.15)

        selected_port = None
        for port in config.OAUTH_PORTS:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    selected_port = port
                    break

        if not selected_port:
            selected_port = config.OAUTH_PORTS[0]

        redirect_uri = f"http://localhost:{selected_port}/oauth-callback"
        self.last_selected_port = selected_port
        self.last_redirect_uri = redirect_uri
        auth_params = {
            "client_id": config.CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.OAUTH_SCOPES),
            "access_type": "offline",
            "prompt": "consent"
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

        manager = self
        stop_event = threading.Event()
        self.oauth_stop_event = stop_event

        class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return

                if parsed.path == "/oauth-callback":
                    qs = urllib.parse.parse_qs(parsed.query)
                    code = qs.get("code", [None])[0]
                    error = qs.get("error", [None])[0]

                    if code:
                        try:
                            t_res = requests.post(
                                "https://oauth2.googleapis.com/token",
                                data={
                                    "grant_type": "authorization_code",
                                    "code": code,
                                    "redirect_uri": redirect_uri,
                                    "client_id": config.CLIENT_ID,
                                    "client_secret": config.CLIENT_SECRET,
                                },
                                timeout=15
                            )
                            if t_res.status_code == 200:
                                t_data = t_res.json()
                                refresh_token = t_data.get("refresh_token")
                                if refresh_token:
                                    manager.add_or_update_account(refresh_token)
                                    self._send_html("Đăng nhập thành công!", "Tài khoản Google Antigravity đã được thêm vào hệ thống. Bạn có thể đóng cửa sổ này.")
                                    stop_event.set()
                                    return
                                else:
                                    self._send_html("Cảnh báo", "Không nhận được refresh_token từ Google. Hãy thử lại với prompt=consent.", is_error=True)
                                    stop_event.set()
                                    return
                            else:
                                self._send_html("Lỗi xác thực", f"Google trả về lỗi {t_res.status_code}: {t_res.text}", is_error=True)
                                stop_event.set()
                                return
                        except Exception as ex:
                            self._send_html("Lỗi", f"Xảy ra lỗi xử lý token: {ex}", is_error=True)
                            stop_event.set()
                            return

                    self._send_html("Lỗi ủy quyền", f"Google từ chối ủy quyền: {error}", is_error=True)
                    stop_event.set()
                else:
                    self.send_response(404)
                    self.end_headers()

            def _send_html(self, title, message, is_error=False):
                self.send_response(200 if not is_error else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                color = "#ef4444" if is_error else "#10b981"
                html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }}
    .card {{ background: #1e293b; padding: 2rem 2.5rem; border-radius: 1rem; text-align: center; max-width: 420px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    h2 {{ color: {color}; margin-top: 0; }}
    p {{ color: #94a3b8; line-height: 1.5; }}
    button {{ background: #3b82f6; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 0.5rem; cursor: pointer; font-size: 0.95rem; margin-top: 1rem; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>{title}</h2>
    <p>{message}</p>
    <button onclick="window.close()">Đóng cửa sổ này</button>
  </div>
  <script>setTimeout(() => {{ window.close(); }}, 3000);</script>
</body>
</html>"""
                self.wfile.write(html.encode("utf-8"))

            def log_message(self, format, *args):
                pass

        server = ReusableHTTPServer((host, selected_port), OAuthCallbackHandler)
        server.timeout = 1.0
        self.oauth_server = server

        def run_srv():
            start_time = time.time()
            try:
                while not stop_event.is_set() and (time.time() - start_time < 180):
                    server.handle_request()
            except Exception:
                pass
            finally:
                try:
                    server.server_close()
                except Exception:
                    pass

        t = threading.Thread(target=run_srv, daemon=True)
        t.start()

        return {
            "url": auth_url,
            "auth_url": auth_url,
            "port": selected_port,
            "redirect_uri": redirect_uri
        }

account_manager = AccountManager()
