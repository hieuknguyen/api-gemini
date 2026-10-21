import os
import json
import time
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SETTINGS_FILE = BASE_DIR / "settings.json"
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
TEMPLATES_DIR = BASE_DIR / "templates"

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "antigravity")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "antigravity_secret")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "antigravity_db")

def get_persisted_settings() -> dict:
    try:
        import db
        rows = db.fetch_all("SELECT setting_key, setting_value FROM settings")
        if rows:
            res = {}
            for r in rows:
                k = r["setting_key"]
                v = r["setting_value"]
                try:
                    res[k] = json.loads(v)
                except Exception:
                    res[k] = v
            return res
    except Exception:
        pass

    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_persisted_settings(data: dict):
    try:
        import db
        now = time.time()
        for k, v in data.items():
            val_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            db.execute("""
                INSERT INTO settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), updated_at=VALUES(updated_at)
            """, (k, val_str, now))
    except Exception as e:
        print(f"Lỗi lưu cài đặt vào MySQL: {e}")

    try:
        current = {}
        if SETTINGS_FILE.exists():
            try:
                current = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        current.update(data)
        SETTINGS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Error saving settings.json backup: {e}")

def update_env_file(key: str, value: str):
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"Error updating .env: {e}")

def generate_random_api_key() -> str:
    """Sinh ngẫu nhiên mã API Key an toàn chuẩn sk-antigravity-..."""
    return f"sk-antigravity-{secrets.token_hex(16)}"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5678"))

# Ưu tiên lấy API_KEY từ MySQL settings, nếu chưa có thì lấy từ .env
_persisted = get_persisted_settings()
if "api_key" in _persisted and _persisted["api_key"]:
    API_KEY = _persisted["api_key"]
else:
    API_KEY = os.getenv("API_KEY", "")

CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

if "default_model" in _persisted and _persisted["default_model"]:
    DEFAULT_MODEL = _persisted["default_model"]
else:
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-3.8-flash-tiered")

if "strategy" in _persisted and _persisted["strategy"]:
    STRATEGY = _persisted["strategy"]
else:
    STRATEGY = os.getenv("STRATEGY", "failover")  # failover | round_robin

ENDPOINTS = [
    "https://daily-cloudcode-pa.googleapis.com",
    "https://cloudcode-pa.googleapis.com"
]

# Use Antigravity's shared consumer project by default. Users do not need to
# create or enable a Google Cloud project for this gateway's Antigravity flow.
# Set ANTIGRAVITY_PROJECT_ID only when an explicitly configured project is needed.
ANTIGRAVITY_PROJECT_ID = os.getenv("ANTIGRAVITY_PROJECT_ID", "aicode-consumers").strip() or "aicode-consumers"

OAUTH_PORTS = [51121, 51122, 51123, 51124, 51125, 51126]
OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs"
]

ANTIGRAVITY_HEADERS = {
    "User-Agent": "antigravity/1.15.8 win32/x64",
    "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    "Client-Metadata": '{"ideType":"IDE_UNSPECIFIED","platform":"PLATFORM_UNSPECIFIED","pluginType":"GEMINI"}'
}

SYSTEM_INSTRUCTION = (
    "You are Antigravity, a powerful agentic AI coding assistant designed by the Google Deepmind team "
    "working on Advanced Agentic Coding.You are pair programming with a USER to solve their coding task. "
    "The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question."
    "**Absolute paths only****Proactiveness**"
)
