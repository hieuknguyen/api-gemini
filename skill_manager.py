import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

logger = logging.getLogger("antigravity-skills")
SKILLS_FILE = config.BASE_DIR / "skills.json"
CANONICAL_SKILL_ID = "skill_62cd9426"
CANONICAL_SKILL_NAME = "Viết content"

DEFAULT_SKILLS: List[Dict[str, Any]] = [
    {
        "id": CANONICAL_SKILL_ID,
        "name": CANONICAL_SKILL_NAME,
        "system_prompt": "Bạn là trợ lý viết content chuyên nghiệp. Tạo nội dung rõ ràng, phù hợp đối tượng và mục tiêu người dùng; làm rõ thông tin còn thiếu trước khi tự giả định.",
        "is_default": False,
        "created_at": "2026-09-13 00:00:00"
    }
]

class SkillManager:
    def __init__(self, skills_file: Path = SKILLS_FILE):
        self.skills_file = skills_file
        self._init_skills()

    def _init_skills(self):
        if not self.skills_file.exists():
            self.save_skills(DEFAULT_SKILLS)

    def enforce_single_private_skill(self, owner_id: Optional[str]):
        """Keep only the content-writing skill, owned by one account."""
        if not owner_id:
            logger.error("Không thể khóa quyền skill: chưa xác định được tài khoản sở hữu.")
            return

        skill = None
        try:
            if self.skills_file.exists():
                data = json.loads(self.skills_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    skill = next((item for item in data if item.get("id") == CANONICAL_SKILL_ID), None)
                    if not skill:
                        skill = next((item for item in data if str(item.get("name", "")).strip().lower() == "viết content"), None)
        except Exception as exc:
            logger.error(f"Không đọc được bản sao skills.json: {exc}")

        if not skill:
            skill = dict(DEFAULT_SKILLS[0])
        skill = dict(skill)
        skill.update({
            "id": CANONICAL_SKILL_ID,
            "name": CANONICAL_SKILL_NAME,
            "user_id": owner_id,
            "is_default": False,
            "is_system": False,
            "is_owner": True,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        try:
            import db
            db.execute("DELETE FROM skills")
        except Exception as exc:
            logger.warning(f"Không xóa được skill cũ trong MySQL; danh sách API vẫn sẽ bị giới hạn: {exc}")
        self.save_skills([skill])

    def load_skills(self, user_id: Optional[str] = None, include_all: bool = False) -> List[Dict[str, Any]]:
        if not user_id:
            return []

        try:
            import db
            rows = db.fetch_all(
                "SELECT * FROM skills WHERE id = %s AND user_id = %s LIMIT 1",
                (CANONICAL_SKILL_ID, user_id)
            )
            if rows is not None:
                return [self._for_owner(rows[0], user_id)] if rows else []
        except Exception as e:
            logger.debug(f"Chưa nạp skills từ MySQL: {e}")

        try:
            if not self.skills_file.exists():
                return []
            else:
                data = json.loads(self.skills_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            skill = next((s for s in data if s.get("id") == CANONICAL_SKILL_ID and s.get("user_id") == user_id), None)
            return [self._for_owner(skill, user_id)] if skill else []
        except Exception as e:
            logger.error(f"Lỗi nạp file skills.json: {e}")
            return []

    @staticmethod
    def _for_owner(row: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        skill = dict(row)
        skill.pop("icon", None)
        skill.pop("description", None)
        skill["is_default"] = False
        skill["is_system"] = False
        skill["is_owner"] = skill.get("user_id") == user_id
        return skill

    def save_skills(self, skills: List[Dict[str, Any]]):
        # 1. Lưu vào MySQL
        try:
            import db
            for s in skills:
                db.execute("""
                    INSERT INTO skills (
                        id, user_id, name, system_prompt, is_default, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name=VALUES(name), system_prompt=VALUES(system_prompt),
                        is_default=VALUES(is_default), user_id=VALUES(user_id),
                        updated_at=VALUES(updated_at)
                """, (
                    s.get("id"),
                    s.get("user_id", None),
                    s.get("name"),
                    s.get("system_prompt", ""),
                    s.get("is_default", False),
                    s.get("created_at", ""),
                    s.get("updated_at", "")
                ))
        except Exception as e:
            logger.error(f"Lỗi lưu skills vào MySQL: {e}")

        # 2. Backup ra file skills.json
        try:
            cleaned_skills = []
            for s in skills:
                sc = dict(s)
                sc.pop("icon", None)
                sc.pop("description", None)
                cleaned_skills.append(sc)
            self.skills_file.write_text(
                json.dumps(cleaned_skills, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Lỗi lưu file skills.json backup: {e}")

    def get_skill(self, skill_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not skill_id or not user_id or str(skill_id).strip() != CANONICAL_SKILL_ID:
            return None
        skills = self.load_skills(user_id=user_id)
        return skills[0] if skills else None

    def add_skill(self, name: str, system_prompt: str, user_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raise ValueError("Project chỉ giữ lại kỹ năng Viết content đã được chỉ định.")

    def update_skill(self, skill_id: str, updates: Dict[str, Any], user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        existing = self.get_skill(skill_id, user_id=user_id)
        if not existing:
            return None

        updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            import db
            db.execute(
                "UPDATE skills SET name = %s, system_prompt = %s, updated_at = %s WHERE id = %s AND user_id = %s",
                (CANONICAL_SKILL_NAME, updates.get("system_prompt", existing["system_prompt"]), updated_at,
                 skill_id, user_id)
            )
        except Exception as e:
            logger.error(f"Lỗi cập nhật skill trong MySQL: {e}")

        if updates.get("system_prompt") is not None:
            existing["system_prompt"] = str(updates["system_prompt"]).strip()
        existing["name"] = CANONICAL_SKILL_NAME
        existing.pop("icon", None)
        existing.pop("description", None)
        existing["updated_at"] = updated_at

        try:
            self.skills_file.write_text(json.dumps([existing], indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        return existing

    def delete_skill(self, skill_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> bool:
        raise ValueError("Không thể xóa kỹ năng duy nhất của project.")

skill_manager = SkillManager()
