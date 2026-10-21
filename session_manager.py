"""Convert client-owned history into stateless Gemini contents."""

from copy import deepcopy
import json
from typing import List, Dict, Any, Optional


def message_text(message: Dict[str, Any]) -> str:
    content = message.get("parts", message.get("content", message.get("text", "")))
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    texts = []
    for part in content:
        value = part.get("text") if isinstance(part, dict) else part
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())
    return "\n".join(texts)


def extract_system_prompt(messages: Optional[List[Dict[str, Any]]]) -> str:
    instructions = []
    for message in messages or []:
        if isinstance(message, dict) and str(message.get("role", "")).lower() in {"system", "developer"}:
            text = message_text(message)
            if text and text not in instructions:
                instructions.append(text)
    return "\n\n".join(instructions)


def _append_unique(parts, part):
    if part not in parts:
        parts.append(deepcopy(part))


def _image_part(image, client):
    if not isinstance(image, str) or not image.strip():
        raise ValueError("Ảnh đính kèm phải là chuỗi Base64 hoặc Data URI.")
    if image.startswith(("http://", "https://", "file://")):
        raise ValueError("Ảnh đính kèm cần được gửi dưới dạng Base64 hoặc Data URI.")
    if client is None:
        raise ValueError("Chưa cấu hình bộ xử lý ảnh đính kèm.")
    mime, data = client.parse_image(image)
    return {"inlineData": {"mimeType": mime, "data": data}}


def normalize_messages_for_antigravity(
    messages: Optional[List[Dict[str, Any]]] = None,
    prompt: Optional[str] = None,
    current_parts: Optional[List[Dict[str, Any]]] = None,
    antigravity_client=None,
) -> List[Dict[str, Any]]:
    """Normalize roles and attachments, adding the current turn only once."""
    turns = []
    call_names = {}
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        source_role = str(message.get("role", "user")).lower()
        if source_role in {"system", "developer"}:
            continue
        if source_role not in {"user", "human", "assistant", "model", "bot", "ai", "tool", "function"}:
            raise ValueError(f"Vai trò tin nhắn không được hỗ trợ: {source_role}")
        role = "model" if source_role in {"assistant", "model", "bot", "ai"} else "user"
        parts = []
        content = message.get("parts", message.get("content", message.get("text", "")))
        if isinstance(content, str):
            content = [{"text": content}]
        if isinstance(content, list):
            for part in content:
                if isinstance(part, str) and part.strip():
                    parts.append({"text": part.strip()})
                elif isinstance(part, dict):
                    if isinstance(part.get("text"), str) and part["text"].strip():
                        parts.append({"text": part["text"].strip()})
                    elif "image_url" in part:
                        image = part["image_url"]
                        image = image.get("url") if isinstance(image, dict) else image
                        _append_unique(parts, _image_part(image, antigravity_client))
                    elif any(key in part for key in ("inlineData", "inline_data", "fileData", "functionCall", "functionResponse")):
                        canonical = deepcopy(part)
                        if "inline_data" in canonical:
                            inline = canonical.pop("inline_data")
                            canonical["inlineData"] = {"mimeType": inline.get("mimeType", inline.get("mime_type")), "data": inline.get("data")}
                        _append_unique(parts, canonical)
                    elif part.get("type") == "image" and isinstance(part.get("source"), dict):
                        source = part["source"]
                        if source.get("type") != "base64":
                            raise ValueError("Ảnh cần dùng nguồn Base64.")
                        _append_unique(parts, _image_part(f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}", antigravity_client))
        native_calls = message.get("tool_calls") or []
        if message.get("function_call"):
            native_calls = list(native_calls) + [{"function": message["function_call"]}]
        for call in native_calls:
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise ValueError("Lời gọi công cụ phải có function hợp lệ.")
            function = call["function"]
            name = function.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Lời gọi công cụ thiếu tên function.")
            arguments = function.get("arguments", function.get("args", {}))
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments or "{}")
                except json.JSONDecodeError as error:
                    raise ValueError("Arguments của công cụ không phải JSON hợp lệ.") from error
            if not isinstance(arguments, dict):
                raise ValueError("Arguments của công cụ phải là JSON object.")
            if call.get("id"):
                call_names[call["id"]] = name
            _append_unique(parts, {"functionCall": {"name": name, "args": arguments}})
        if source_role in {"tool", "function"}:
            name = message.get("name") or call_names.get(message.get("tool_call_id"))
            output = message.get("content", message.get("text", ""))
            if name:
                parts = [{"functionResponse": {"name": name, "response": {"output": output}}}]
            else:
                # Legacy clients sometimes omit the function name/id. Preserve
                # their result as reference text rather than discard the turn.
                text = message_text(message) or json.dumps(output, ensure_ascii=False)
                parts = [{"text": f"Tool result:\n{text}"}]
        image_items = list(message.get("images") or [])
        if message.get("image"):
            image_items.insert(0, message["image"])
        for image in image_items:
            _append_unique(parts, _image_part(image, antigravity_client))
        if message.get("files"):
            import file_processor
            for item in message["files"]:
                if not isinstance(item, dict) or not item.get("data"):
                    continue
                result = file_processor.process_file(item["data"], item.get("filename", ""))
                if result["type"] == "inline":
                    _append_unique(parts, {"inlineData": {"mimeType": result["mime_type"], "data": result["data"]}})
                elif result.get("extracted_text"):
                    _append_unique(parts, {"text": f"Nội dung file {item.get('filename', '')}:\n{result['extracted_text']}"})
        if parts:
            turns.append({"role": role, "parts": parts})

    current = deepcopy(current_parts or ([{"text": prompt.strip()}] if prompt and prompt.strip() else []))
    if current:
        last = turns[-1] if turns else None
        same_text = last and last["role"] == "user" and message_text(last) == (prompt.strip() if prompt else message_text({"parts": current}))
        if last and last["role"] == "user" and (same_text or last["parts"] == current):
            for part in current:
                _append_unique(last["parts"], part)
        else:
            turns.append({"role": "user", "parts": current})

    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    normalized = []
    for turn in turns:
        if normalized and normalized[-1]["role"] == turn["role"]:
            normalized[-1]["parts"].extend(turn["parts"])
        else:
            normalized.append(turn)
    return normalized


class StatelessSessionManager:
    def get_contents_for_gemini(self, session_id=None, current_parts=None, limit=24):
        return [{"role": "user", "parts": current_parts}] if current_parts else []

    def list_sessions(self):
        return []

    def get_messages(self, session_id: str):
        return []

    def clear_session(self, session_id: str):
        return True

    def delete_session(self, session_id: str):
        return True


session_manager = StatelessSessionManager()
