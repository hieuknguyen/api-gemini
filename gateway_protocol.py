"""Wire validation shared by the upstream client and the chat routes."""

import json
import re
from html import unescape
from typing import Any, Dict, Iterator, Optional


PROTOCOL_VERSION = "graft-gateway/1"


def _clean_error_text(value: Any, *, limit: int = 1200) -> str:
    """Turn an upstream error into short, readable text without leaking secrets."""
    text = unescape(str(value or "")).strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", text)
    text = re.sub(
        r"(?i)(access_token|refresh_token|api[_-]?key|x-api-key)\s*[:=]\s*([\"']?)[^\s,;}\"']+\2",
        r"\1=[REDACTED]",
        text,
    )
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def format_upstream_error(status_code: int, response_text: Any) -> str:
    """Extract a useful provider error from JSON/HTML without exposing credentials."""
    raw = str(response_text or "").strip()
    payload = None
    if raw:
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            payload = None

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("detail")
        provider_code = error.get("status") or error.get("code")
    else:
        message = None
        provider_code = None

    if not message and isinstance(payload, dict):
        message = payload.get("detail") or payload.get("message")
    if not message:
        message = raw
    message = _clean_error_text(message) or "Upstream không trả về chi tiết lỗi."

    prefix = f"Google upstream HTTP {status_code}"
    if provider_code and str(provider_code) != str(status_code):
        prefix += f" {provider_code}"
    return f"{prefix}: {message}"


class GatewayProtocolError(RuntimeError):
    def __init__(self, error_code: str, message: str, *, retryable: bool = False,
                 finish_reason: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable
        self.finish_reason = finish_reason
        self.usage = None
        self.model = None

    def as_event(self) -> Dict[str, Any]:
        event = {"type": "error", "error": str(self), "error_code": self.error_code,
                 "retryable": self.retryable, "finish_reason": self.finish_reason}
        if self.usage is not None:
            event["usage"] = self.usage
            event["tokens"] = self.usage
        if self.model:
            event["model"] = self.model
        return event


def check_cancelled(should_cancel=None):
    if should_cancel is not None and should_cancel():
        raise GatewayProtocolError("CANCELLED", "Yêu cầu đã được dừng.")


def response_inner(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise GatewayProtocolError("INVALID_RESPONSE", "Upstream trả về dữ liệu không phải JSON object.")
    inner = data.get("response", data)
    if not isinstance(inner, dict):
        raise GatewayProtocolError("INVALID_RESPONSE", "Upstream trả về response không đúng định dạng.")
    for envelope in (data, inner):
        error = envelope.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            provider_code = (error.get("status") or error.get("code")) if isinstance(error, dict) else None
            if provider_code:
                message = f"{provider_code}: {message}"
            raise GatewayProtocolError("UPSTREAM_ERROR", _clean_error_text(message) or "Upstream báo lỗi.")
        feedback = envelope.get("promptFeedback") or {}
        if isinstance(feedback, dict):
            reason = feedback.get("blockReason")
            if reason and reason not in ("BLOCK_REASON_UNSPECIFIED", "UNSPECIFIED"):
                raise GatewayProtocolError("RESPONSE_BLOCKED", f"Upstream chặn yêu cầu: {reason}.",
                                           finish_reason=str(reason))
    return inner


def validate_finish_reason(reason: Any) -> str:
    if not reason:
        return ""
    value = str(reason).upper()
    if value in ("STOP", "FUNCTION_CALL", "TOOL_CALLS"):
        return value
    if value in ("MAX_TOKENS", "LENGTH"):
        raise GatewayProtocolError("RESPONSE_TRUNCATED", "Phản hồi upstream bị cắt vì hết giới hạn token.",
                                   finish_reason=value)
    if value in ("FINISH_REASON_UNSPECIFIED", "UNSPECIFIED"):
        return ""
    raise GatewayProtocolError("RESPONSE_BLOCKED", f"Upstream kết thúc phản hồi với lý do: {value}.",
                               finish_reason=value)


def validate_completion(text: str, function_calls: list, finish_reason: str,
                        *, require_finish: bool = False, allow_function_calls: bool = True):
    validate_finish_reason(finish_reason)
    if not text.strip() and not function_calls:
        raise GatewayProtocolError("EMPTY_RESPONSE", "Upstream không gửi nội dung trả lời hoặc lời gọi công cụ.",
                                   retryable=True, finish_reason=finish_reason or None)
    if function_calls and not allow_function_calls:
        raise GatewayProtocolError("UNSUPPORTED_TOOL_CALL", "Upstream gửi lời gọi công cụ nhưng API này không yêu cầu nhận công cụ.",
                                   finish_reason=finish_reason or None)
    if require_finish and not finish_reason:
        raise GatewayProtocolError("STREAM_INCOMPLETE", "Luồng upstream bị ngắt trước thông báo hoàn tất.",
                                   retryable=True)


def candidate_parts(candidate: Any) -> list:
    if not isinstance(candidate, dict):
        raise GatewayProtocolError("INVALID_RESPONSE", "Candidate upstream không hợp lệ.")
    content = candidate.get("content") or {}
    if not isinstance(content, dict):
        raise GatewayProtocolError("INVALID_RESPONSE", "Content upstream không hợp lệ.")
    parts = content.get("parts") or []
    if not isinstance(parts, list) or any(not isinstance(part, dict) for part in parts):
        raise GatewayProtocolError("INVALID_RESPONSE", "Các parts upstream không hợp lệ.")
    for part in parts:
        if "text" in part and not isinstance(part["text"], str):
            raise GatewayProtocolError("INVALID_RESPONSE", "Nội dung text upstream không hợp lệ.")
        if "functionCall" in part:
            call = part["functionCall"]
            if (not isinstance(call, dict) or not isinstance(call.get("name"), str)
                    or not call["name"] or not isinstance(call.get("args", {}), dict)):
                raise GatewayProtocolError("INVALID_RESPONSE", "Lời gọi công cụ upstream không hợp lệ.")
    return parts


def normalize_usage(metadata: Optional[dict], prompt: Any, text: str, *, estimate_missing: bool = True) -> Dict[str, Any]:
    meta = metadata if isinstance(metadata, dict) else {}
    def count(key):
        value = meta.get(key, 0)
        return max(0, value) if isinstance(value, int) else 0
    prompt_tokens = count("promptTokenCount")
    completion_tokens = count("candidatesTokenCount")
    total_tokens = count("totalTokenCount")
    cached_tokens = count("cachedContentTokenCount")
    thought_tokens = count("thoughtsTokenCount")
    if cached_tokens and (not prompt_tokens or prompt_tokens + completion_tokens + thought_tokens + cached_tokens == total_tokens):
        prompt_tokens += cached_tokens
    if not prompt_tokens and total_tokens > completion_tokens + thought_tokens:
        prompt_tokens = total_tokens - completion_tokens - thought_tokens
    # Preserve reported thought tokens separately; they are not visible output.
    if not completion_tokens and text and total_tokens > prompt_tokens + thought_tokens:
        completion_tokens = total_tokens - prompt_tokens - thought_tokens
    if not total_tokens:
        if not prompt_tokens and estimate_missing:
            prompt_tokens = max(1, len(str(prompt or "")) // 4)
        if not completion_tokens and text and estimate_missing:
            completion_tokens = max(1, len(text) // 4)
        total_tokens = prompt_tokens + completion_tokens + thought_tokens
    return {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": total_tokens, "cached_tokens": cached_tokens,
            "reasoning_tokens": thought_tokens, "prompt": prompt_tokens,
            "completion": completion_tokens, "total": total_tokens}


def stream_records(response, should_cancel=None) -> Iterator[Dict[str, Any]]:
    """Read unbuffered SSE, preserving UTF-8 and CRLF across byte boundaries."""
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "json" in content_type and "event-stream" not in content_type:
        check_cancelled(should_cancel)
        try:
            data = response.json()
        except (ValueError, TypeError) as exc:
            raise GatewayProtocolError("INVALID_RESPONSE", "Upstream gửi JSON không hợp lệ.") from exc
        for item in data if isinstance(data, list) else [data]:
            check_cancelled(should_cancel)
            yield item
        return

    response.encoding = "utf-8"
    characters = []
    skip_lf = False
    data_lines = []
    def decoded_record(lines):
        value = "\n".join(lines)
        if value.strip() == "[DONE]":
            return None
        try:
            return json.loads(value)
        except (ValueError, TypeError) as exc:
            raise GatewayProtocolError("INVALID_RESPONSE", "Upstream gửi SSE JSON không hợp lệ.") from exc

    for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
        check_cancelled(should_cancel)
        for character in chunk:
            if skip_lf:
                skip_lf = False
                if character == "\n":
                    continue
            if character not in ("\r", "\n"):
                characters.append(character)
                continue
            line = "".join(characters).lstrip("\ufeff")
            characters.clear()
            skip_lf = character == "\r"
            if not line:
                if data_lines:
                    record = decoded_record(data_lines)
                    data_lines.clear()
                    if record is None:
                        return
                    yield record
                continue
            field, separator, value = line.partition(":")
            if field == "data" and separator:
                data_lines.append(value[1:] if value.startswith(" ") else value)
    if characters:
        line = "".join(characters).lstrip("\ufeff")
        field, separator, value = line.partition(":")
        if field == "data" and separator:
            data_lines.append(value[1:] if value.startswith(" ") else value)
    if data_lines:
        record = decoded_record(data_lines)
        if record is not None:
            yield record
