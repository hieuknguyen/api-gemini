import os
import re
import json
import time
import uuid
import logging
import urllib.parse
import asyncio
import threading
import socket
from fastapi import FastAPI, Header, HTTPException, Depends, status, Request, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
import api_docs_generator
import docx_exporter

import config
from models import (
    ChatRequest, ChatResponse, ManualAccountRequest, OAuthExchangeRequest, SettingsUpdateRequest,
    SkillUpdateRequest, ImageGenerateRequest, ImageGenerateResponse,
    UserCreateRequest, UserUpdateRequest, ApiKeyCreateRequest, LoginRequest, RegisterRequest,
    ExportDocxRequest, ParseBlocksRequest, ReadFolderRequest, ReadFolderResponse,
    ReadFileRequest, ReadFileResponse,
    OpenAIChatRequest, OpenAIChatResponse, OpenAIChoice, OpenAIUsage,
    OpenAIModelList, OpenAIModelInfo,
    MoMoPaymentCreateRequest, MoMoPaymentCreateResponse, MoMoConfigUpdateRequest
)
from account_manager import account_manager
from client import antigravity_client
from quota_tracker import quota_tracker
from skill_manager import skill_manager
from user_manager import user_manager
from session_manager import session_manager, normalize_messages_for_antigravity, message_text, extract_system_prompt
from gateway_protocol import GatewayProtocolError, PROTOCOL_VERSION
import image_generator
import file_processor
import quota_fetcher
from momo_payment import momo_service, TOKEN_PACKAGES


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("antigravity-api")

app = FastAPI(
    title="Antigravity AI Gateway",
    description="FastAPI gateway siêu nhẹ gọi Gemini trực tiếp bằng tài khoản Google Antigravity",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    try:
        import db
        db.run_migrations()
        logger.info("Đã đồng bộ và di chuyển dữ liệu vào MySQL thành công.")

        # Đảm bảo tài khoản Quản trị viên Tối cao và hạ quyền user khác an toàn
        user_manager.ensure_admin_account()
        admin_user = user_manager.get_admin_user()
        skill_manager.enforce_single_private_skill(admin_user.get("id") if admin_user else None)

        # Đồng bộ cấu hình từ MySQL vào bộ nhớ
        persisted = config.get_persisted_settings()
        if "strategy" in persisted and persisted["strategy"]:
            account_manager.strategy = persisted["strategy"]
            config.STRATEGY = persisted["strategy"]
            logger.info(f"Đã nạp chiến lược phân phối từ MySQL: {account_manager.strategy}")
        if "api_key" in persisted and persisted["api_key"]:
            config.API_KEY = persisted["api_key"]
        if "default_model" in persisted and persisted["default_model"]:
            config.DEFAULT_MODEL = persisted["default_model"]
    except Exception as e:
        logger.error(f"Lỗi khởi tạo database MySQL khi startup: {e}")

# ----------------- WEB UI ROUTE (REACT SPA & FALLBACK) -----------------
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="react-assets")

@app.get("/", response_class=HTMLResponse)
def index_page():
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return HTMLResponse(content=react_index.read_text(encoding="utf-8"))
    html_file = config.TEMPLATES_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Antigravity AI Gateway</h1><p>index.html not found</p>")

@app.get("/favicon.svg")
def get_favicon():
    fav = FRONTEND_DIST / "favicon.svg"
    if fav.exists():
        return FileResponse(fav)
    return Response(status_code=404)

@app.get("/api/docs/markdown")
@app.get("/docs/api.md")
def get_api_docs_markdown(request: Request, api_key: Optional[str] = None):
    """Tải về tài liệu đặc tả API đầy đủ nhất dạng Markdown (.md) cho AI Agents và Developers"""
    base_url = str(request.base_url).rstrip("/")
    resolved_key = api_key or request.headers.get("X-API-Key") or config.API_KEY or "sk-antigravity-default"
    md_content = api_docs_generator.generate_markdown_docs(base_url=base_url, api_key=resolved_key)
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="antigravity_api_documentation.md"'
        }
    )

@app.post("/api/export/docx")
def export_docx_api(req: ExportDocxRequest):
    """Xuất nội dung bài viết sang file Microsoft Word (.docx) chuyên nghiệp"""
    try:
        fname = (req.filename or "Antigravity_Content").strip()
        fname = re.sub(r'[\r\n\t]', '', fname)
        # Chuẩn hóa đuôi file nếu bị thừa dấu chấm hoặc thiếu .docx
        if not fname.endswith(".docx"):
            fname += ".docx"
        fname = re.sub(r'\.+docx$', '.docx', fname)

        buf = docx_exporter.markdown_to_docx(req.content, fname)

        # Header Content-Disposition theo chuẩn RFC 5987 / RFC 6266:
        # Fallback filename chỉ dùng ký tự ASCII để tránh lỗi latin-1 codec
        # filename*=UTF-8'' dùng URL-encode để hỗ trợ trọn vẹn tiếng Việt có dấu trên mọi trình duyệt
        ascii_fallback = "Antigravity_Content.docx"
        encoded_fname = urllib.parse.quote(fname, safe=".-_()")
        content_disposition = f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded_fname}'

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": content_disposition
            }
        )
    except Exception as e:
        logger.error(f"Lỗi xuất file docx: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xuất file docx: {str(e)}")

@app.get("/health")
def health_check():
    accounts = account_manager.get_accounts_public()
    ready = [a for a in accounts if a["is_active"] and not a["is_rate_limited"]]
    return {
        "status": "healthy",
        "service": "Antigravity FastAPI Gateway",
        "model": config.DEFAULT_MODEL,
        "total_accounts": len(accounts),
        "ready_accounts": len(ready)
    }

def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    key: Optional[str] = Query(None, alias="key")
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    # Ưu tiên theo thứ tự: Header x-goog-api-key -> X-API-Key -> Query param key -> Authorization: Bearer
    token = x_goog_api_key or x_api_key or key
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    is_valid, user_info, key_info = user_manager.validate_api_key(token)
    if not is_valid:
        logger.warning("Từ chối truy cập: API Key không hợp lệ hoặc bị tạm dừng.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key không hợp lệ hoặc đã bị tạm dừng trong hệ thống!"
        )

    # Kiểm tra hạn mức token đối với user thông thường
    role = user_info.get("role", "user")
    user_id = user_info.get("id")
    has_quota, cur_tokens = user_manager.check_user_token_quota(user_id, role)
    if not has_quota:
        logger.warning(f"Tài khoản '{user_info.get('name')}' ({user_info.get('email')}) đã hết token ({cur_tokens} tokens)")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Tài khoản của bạn đã hết số dư Token. Vui lòng nạp thêm Token qua MoMo để tiếp tục sử dụng dịch vụ!"
        )

    return token, user_info, key_info

def resolve_request_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    q_user_id: Optional[str] = Query(None, alias="user_id"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    key: Optional[str] = Query(None, alias="key")
) -> Optional[Dict[str, Any]]:
    """Xác định danh tính người dùng từ API Key hoặc Header/Query User ID"""
    token = x_goog_api_key or x_api_key or key
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()
    if token:
        is_valid, user_info, _ = user_manager.validate_api_key(token)
        if is_valid and user_info:
            return user_info

    uid = x_user_id or q_user_id
    if uid:
        u = user_manager.get_user(uid)
        if u and u.get("is_active", True):
            return u
    return None

def verify_admin_access(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    key: Optional[str] = Query(None, alias="key")
) -> Dict[str, Any]:
    """Chỉ cho phép tài khoản Admin có API Key / Token hợp lệ truy cập và quản lý nhóm tài khoản Antigravity"""
    token = x_goog_api_key or x_api_key or key
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()

    if token:
        is_valid, user_info, _ = user_manager.validate_api_key(token)
        if is_valid and user_info:
            if user_info.get("role") == "admin":
                return user_info
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (Admin) mới có quyền truy cập và quản lý tài khoản Antigravity!"
            )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Từ chối truy cập: Yêu cầu đăng nhập hoặc cung cấp API Key của Quản trị viên (Admin)!"
    )

# ----------------- CHAT ENDPOINTS -----------------
def _sse_record(event, payload):
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _gateway_error_event(error):
    if isinstance(error, GatewayProtocolError):
        return error.as_event()
    return {"type": "error", "error": str(error), "error_code": "UPSTREAM_ERROR", "retryable": False}


def _record_error_usage(api_token, envelope):
    usage = envelope.get("usage") or envelope.get("tokens") or {}
    total = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0
    if isinstance(total, (int, float)) and total > 0:
        user_manager.record_usage(api_token, total)


def _interrupt_response(response):
    """Unblock a requests reader before close waits for its urllib3 read lock."""
    raw = getattr(response, "raw", None)
    connection_socket = getattr(getattr(raw, "connection", None), "sock", None)
    if not isinstance(connection_socket, socket.socket):
        file_pointer = getattr(getattr(getattr(raw, "_fp", None), "fp", None), "raw", None)
        connection_socket = getattr(file_pointer, "_sock", None)
    if isinstance(connection_socket, socket.socket):
        try:
            connection_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        # Detach before closing the native handle; a later Python cleanup must
        # not close a reused handle. Windows recv can survive shutdown alone.
        try:
            handle = connection_socket.detach()
            if handle != -1:
                socket.close(handle)
        except OSError:
            pass
    try:
        response.close()
    except Exception:
        logger.debug("Upstream đã đóng trong lúc dừng yêu cầu.", exc_info=True)


def _managed_sse(event_builder, request=None, openai=False, metadata=None, on_error=None):
    """Run the blocking upstream iterator off the event loop and close it on disconnect."""
    async def stream():
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        cancelled = threading.Event()
        response_lock = threading.Lock()
        active_response = [None]
        end = object()

        def register_response(response):
            with response_lock:
                active_response[0] = response
            if response is not None and cancelled.is_set():
                _interrupt_response(response)

        def enqueue(value):
            try:
                loop.call_soon_threadsafe(queue.put_nowait, value)
            except RuntimeError:
                cancelled.set()

        def produce():
            iterator = None
            try:
                iterator = iter(event_builder(cancelled.is_set, register_response))
                for record in iterator:
                    if cancelled.is_set():
                        break
                    enqueue(record)
            except Exception as error:
                if not cancelled.is_set():
                    envelope = _gateway_error_event(error)
                    envelope.update(metadata or {})
                    if on_error is not None:
                        try:
                            on_error(envelope)
                        except Exception:
                            logger.error("Không thể ghi nhận usage của phản hồi lỗi.", exc_info=True)
                    if openai:
                        enqueue(_sse_record(None, {"error": {"message": envelope["error"], "code": envelope["error_code"], "type": "upstream_error", "retryable": envelope["retryable"]}}))
                    else:
                        enqueue(_sse_record("error", envelope))
            finally:
                try:
                    if iterator is not None and hasattr(iterator, "close"):
                        iterator.close()
                except Exception:
                    logger.debug("Iterator upstream đã đóng trong lúc dọn yêu cầu.", exc_info=True)
                finally:
                    enqueue(end)

        producer = asyncio.create_task(asyncio.to_thread(produce))
        last_keepalive = time.monotonic()
        try:
            while True:
                if request is not None and await request.is_disconnected():
                    break
                try:
                    value = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    if time.monotonic() - last_keepalive >= 15:
                        yield ": keep-alive\n\n"
                        last_keepalive = time.monotonic()
                    continue
                if value is end:
                    break
                yield value
        finally:
            cancelled.set()
            with response_lock:
                response = active_response[0]
            if response is not None:
                await asyncio.to_thread(_interrupt_response, response)
            # The producer owns generator.close(); calling it during next() is unsafe.
            # Retain its task until cleanup finishes after the socket is closed.
            producer.add_done_callback(lambda task: task.exception() if not task.cancelled() else None)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no", "X-Graft-Protocol-Version": PROTOCOL_VERSION,
    })


def _require_answer(answer, function_calls=None):
    if not (isinstance(answer, str) and answer.strip()) and not function_calls:
        raise GatewayProtocolError("EMPTY_RESPONSE", "AI Gateway đã kết thúc phản hồi nhưng không gửi nội dung trả lời.", retryable=True)


@app.post("/api/chat")
@app.post("/webhook/antigravity-chat")
@app.post("/v1/chat")
def chat_endpoint(req: ChatRequest, request: Request = None, auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)):
    try:
        if not req.request_id:
            req.request_id = str(uuid.uuid4())
        if req.protocol_version is not None and req.protocol_version != PROTOCOL_VERSION:
            raise HTTPException(status_code=400, detail={"error": "Phiên bản giao thức Gateway không tương thích.",
                                                        "error_code": "PROTOCOL_MISMATCH", "retryable": False,
                                                        "protocol_version": PROTOCOL_VERSION, "request_id": req.request_id})
        api_token, user_info, key_info = auth_data
        user_id = user_info.get("id") if user_info else None

        model_name = req.model or config.DEFAULT_MODEL
        skill_name = None
        resolved_skill_id = None
        system_prompt = req.custom_system_prompt if req.custom_system_prompt is not None else req.system_prompt
        message_instructions = extract_system_prompt(req.contents or req.messages)
        if message_instructions and message_instructions != (system_prompt or "").strip():
            system_prompt = "\n\n".join(part for part in (message_instructions, system_prompt) if part)
        if req.skill_id:
            skill = skill_manager.get_skill(req.skill_id, user_id=user_id)
            if skill:
                skill_prompt = (skill.get("system_prompt") or "").strip()
                if system_prompt:
                    system_prompt = f"{skill_prompt}\n\n{system_prompt.strip()}"
                else:
                    system_prompt = skill_prompt
                skill_name = skill.get("name")
                resolved_skill_id = skill.get("id")

        # Xác định prompt chính từ req.prompt hoặc tin nhắn user cuối trong req.messages
        prompt = req.prompt
        if not prompt and (req.contents or req.messages):
            for m in reversed(req.contents or req.messages):
                if m.get("role") in ["user", "human"]:
                    prompt = message_text(m)
                    break
        prompt = (prompt or "").strip()
        if not prompt and not req.image and not req.images and not req.files and not req.messages and not req.contents:
            raise HTTPException(status_code=400, detail="Vui lòng cung cấp nội dung 'prompt', 'messages' hoặc file đính kèm")

        # Client Session ID (nếu client gửi để định danh phía client)
        session_id = req.session_id

        # Xây dựng các phần tử parts của lượt hỏi hiện tại (Text + Images + Files)
        current_parts: List[Dict[str, Any]] = []
        file_text_contexts: List[str] = []  # Chứa text trích xuất từ file không native

        if prompt and (req.prompt is not None or not (req.contents or req.messages)):
            current_parts.append({"text": prompt})

        first_img_mime = None
        first_img_b64 = None
        img_list = []
        if req.image:
            img_list.append(req.image)
        if req.images:
            img_list.extend(req.images)
        img_list = list(dict.fromkeys(img_list))
        for img_item in img_list:
            if isinstance(img_item, str) and img_item.strip():
                mime, b64_data = antigravity_client.parse_image(img_item)
                if not first_img_mime:
                    first_img_mime, first_img_b64 = mime, b64_data
                current_parts.append({
                    "inlineData": {
                        "mimeType": mime,
                        "data": b64_data
                    }
                })

        # Xử lý tất cả loại file đính kèm (DOCX, XLSX, PPTX, PDF, Audio, Video, ...)
        if req.files:
            processed_files = []
            for file_item in req.files:
                if not isinstance(file_item, dict):
                    continue
                file_data = file_item.get("data", "")
                file_name = file_item.get("filename", "")
                if not file_data or not isinstance(file_data, str) or not file_data.strip():
                    continue

                result = file_processor.process_file(file_data, file_name)
                processed_files.append(result)

                if result["type"] == "inline":
                    # Kiểm tra dữ liệu base64 hợp lệ, không rỗng và không dính tiền tố data:
                    data_val = result.get("data", "")
                    if data_val and isinstance(data_val, str) and not data_val.startswith("data:"):
                        current_parts.append({
                            "inlineData": {
                                "mimeType": result["mime_type"],
                                "data": data_val
                            }
                        })
                    else:
                        file_text_contexts.append({
                            "filename": file_name,
                            "type": "text_extract",
                            "extracted_text": f"[File rỗng hoặc không có dữ liệu: `{file_name}` (0 bytes)]"
                        })
                elif result["type"] == "text_extract":
                    # Cần chuyển đổi → thêm text vào context
                    file_text_contexts.append(result)

            # Nếu có file cần chuyển đổi text, thêm context vào đầu prompt
            if file_text_contexts:
                context_text = file_processor.build_file_context(file_text_contexts)
                if context_text:
                    # Chèn context text vào đầu parts (trước prompt)
                    current_parts.insert(0, {"text": f"📎 Tài liệu đính kèm:\n\n{context_text}\n\n---\n"})

        # Kiểm tra nếu người dùng yêu cầu tạo ảnh AI
        if image_generator.is_image_request(prompt, model_name):
            cleaned = image_generator.clean_image_prompt(prompt)
            enhanced = image_generator.enhance_prompt_with_gemini(antigravity_client, cleaned)
            img_url, seed = image_generator.build_image_url(enhanced, width=1024, height=1024, model="flux")
            md = image_generator.generate_image_markdown(
                user_prompt=prompt,
                enhanced_prompt=enhanced,
                image_url=img_url,
                width=1024,
                height=1024,
                seed=seed,
                model="Flux.1 AI"
            )
            image_blocks = [
                {
                    "type": "image",
                    "url": img_url,
                    "alt": prompt,
                    "caption": f"Tác phẩm AI: {prompt}",
                    "raw": md
                },
                {
                    "type": "callout",
                    "variant": "success",
                    "title": "Tạo ảnh AI thành công",
                    "content": f"Đã sinh ảnh nghệ thuật độ nét cao dựa trên prompt của bạn.\n- **Prompt gốc**: {prompt}\n- **Prompt tối ưu (Gemini)**: {enhanced}"
                }
            ]
            return ChatResponse(
                response=md,
                text=md,
                model="flux-image-generator",
                session_id=session_id,
                skill_id=resolved_skill_id,
                skill_used=skill_name or "Họa Sĩ AI",
                account_used="Pollinations Flux AI",
                image_url=img_url,
                status="success",
                blocks=image_blocks
            )

        # Chuẩn hóa danh sách contents đa lượt từ messages do Client gửi kèm (Stateless)
        contents_to_send = None
        if req.contents or req.messages:
            contents_to_send = normalize_messages_for_antigravity(
                messages=req.contents or req.messages,
                prompt=prompt if req.prompt is not None else None,
                current_parts=current_parts,
                antigravity_client=antigravity_client
            )
        elif current_parts:
            contents_to_send = [{"role": "user", "parts": current_parts}]
        if not contents_to_send:
            raise HTTPException(status_code=400, detail="Không có nội dung user hoặc tệp đính kèm hợp lệ.")

        # Kiểm tra chế độ Thảo luận & Phản biện giữa 2 AI (Actor-Critic Loop)
        if req.dual_ai_mode:
            from dual_ai_orchestrator import execute_dual_ai_discussion
            def run_dual_ai():
                answer, account_used, discussion_history, blocks, est_tokens, usage_dict = execute_dual_ai_discussion(
                    prompt=prompt, worker_model=model_name, evaluator_model=req.evaluator_model,
                    skill_prompt=system_prompt, skill_name=skill_name,
                    max_rounds=req.max_rounds if req.max_rounds is not None else 3,
                    image=req.image, images=req.images,
                    web_search=req.web_search if req.web_search is not None else True,
                    thinking=bool(req.thinking),
                    temperature=req.temperature if req.temperature is not None else 0.7,
                    max_tokens=req.max_tokens if req.max_tokens is not None else 8192,
                    contents=contents_to_send,
                )
                _require_answer(answer)
                user_manager.record_usage(api_token, usage_dict.get("total_tokens", est_tokens))
                rounds = {item.get("round") for item in discussion_history if isinstance(item, dict) and item.get("round") is not None}
                return ChatResponse(
                    response=answer, text=answer, model=model_name, session_id=session_id,
                    skill_id=resolved_skill_id, skill_used=f"2 AI: {skill_name or 'Chuẩn'}",
                    account_used=account_used, status="success", dual_ai_mode=True,
                    rounds_count=len(rounds), discussion_history=discussion_history,
                    blocks=blocks, tokens=usage_dict, usage=usage_dict,
                    finish_reason="STOP", request_id=req.request_id,
                )

            if req.stream:
                def dual_events(should_cancel, register_response):
                    activity = {"kind": "gateway", "event_id": "dual-ai", "status": "active",
                                "text": "Gateway đang chạy vòng tạo câu trả lời và phản biện giữa hai AI."}
                    yield _sse_record("activity", activity)
                    if should_cancel():
                        return
                    with antigravity_client.request_context(should_cancel=should_cancel, register_response=register_response):
                        result = run_dual_ai()
                    if should_cancel():
                        return
                    yield _sse_record("activity", dict(activity, status="done", text="Gateway đã hoàn tất vòng phản biện giữa hai AI."))
                    yield _sse_record("done", result.model_dump())
                return _managed_sse(dual_events, request, metadata={"protocol_version": PROTOCOL_VERSION, "request_id": req.request_id}, on_error=lambda envelope: _record_error_usage(api_token, envelope))
            return run_dual_ai()

        # Xử lý Streaming Response khi client yêu cầu stream=True
        if req.stream:
            def chat_stream_generator(should_cancel, register_response):
                upstream = antigravity_client.generate_stream(
                    prompt=prompt,
                    image=req.image,
                    images=req.images,
                    model=model_name,
                    thinking=bool(req.thinking),
                    web_search=req.web_search if req.web_search is not None else True,
                    system_prompt=system_prompt,
                    temperature=req.temperature if req.temperature is not None else 0.7,
                    max_tokens=req.max_tokens if req.max_tokens is not None else 8192,
                    contents=contents_to_send,
                    should_cancel=should_cancel, register_response=register_response,
                )
                try:
                    for ev in upstream:
                        if should_cancel():
                            return
                        ev_type = ev.get("type")
                        if ev_type in {"chunk", "thought"}:
                            yield _sse_record(ev_type, {"text": ev.get("text", "")})
                        elif ev_type == "function_call":
                            yield _sse_record("function_call", {"function_call": ev.get("function_call")})
                        elif ev_type == "done":
                            calls = ev.get("function_calls") or ([ev["function_call"]] if ev.get("function_call") else [])
                            _require_answer(ev.get("text"), calls)
                            usage_dict = ev.get("usage", {})
                            user_manager.record_usage(api_token, usage_dict.get("total_tokens", 0))
                            payload_done = {
                                "response": ev.get("text", ""), "text": ev.get("text", ""),
                                "model": ev.get("model", model_name), "session_id": session_id,
                                "skill_id": resolved_skill_id, "skill_used": skill_name,
                                "account_used": ev.get("account_used"), "status": "success",
                                "blocks": ev.get("blocks", []), "tokens": usage_dict, "usage": usage_dict,
                                "finish_reason": ev.get("finish_reason"), "function_calls": calls,
                                "protocol_version": PROTOCOL_VERSION, "request_id": req.request_id,
                            }
                            yield _sse_record("done", payload_done)
                            return
                        elif ev_type == "error":
                            _record_error_usage(api_token, ev)
                            yield _sse_record("error", dict(ev, protocol_version=PROTOCOL_VERSION, request_id=req.request_id))
                            return
                    if not should_cancel():
                        raise GatewayProtocolError("STREAM_INCOMPLETE", "Luồng AI kết thúc trước sự kiện hoàn tất.")
                finally:
                    if hasattr(upstream, "close"):
                        upstream.close()

            return _managed_sse(chat_stream_generator, request, metadata={"protocol_version": PROTOCOL_VERSION, "request_id": req.request_id}, on_error=lambda envelope: _record_error_usage(api_token, envelope))

        answer, account_used, blocks, usage_dict, metadata = antigravity_client.generate(
            prompt=prompt,
            image=req.image,
            images=req.images,
            model=model_name,
            thinking=bool(req.thinking),
            web_search=req.web_search if req.web_search is not None else True,
            system_prompt=system_prompt,
            temperature=req.temperature if req.temperature is not None else 0.7,
            max_tokens=req.max_tokens if req.max_tokens is not None else 8192,
            contents=contents_to_send,
            return_blocks=True,
            return_usage=True,
            return_metadata=True,
        )
        _require_answer(answer, metadata.get("function_calls"))

        # Cập nhật thống kê lượt gọi và tokens cho API Key tương ứng
        est_tokens = usage_dict.get("total_tokens") or (len(prompt or "") // 4 + len(answer or "") // 4)
        user_manager.record_usage(api_token, est_tokens)

        return ChatResponse(
            response=answer,
            text=answer,
            model=metadata.get("model") or model_name,
            session_id=session_id,
            skill_id=resolved_skill_id,
            skill_used=skill_name,
            account_used=account_used,
            status="success",
            blocks=blocks,
            tokens=usage_dict,
            usage=usage_dict,
            finish_reason=metadata.get("finish_reason"), function_calls=metadata.get("function_calls"),
            request_id=req.request_id,
        )
    except HTTPException:
        raise
    except GatewayProtocolError as error:
        _record_error_usage(api_token, error.as_event())
        raise HTTPException(status_code=502, detail=dict(error.as_event(), protocol_version=PROTOCOL_VERSION, request_id=req.request_id)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as e:
        logger.error(f"Lỗi xử lý chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ================= OPENAI-COMPATIBLE ENDPOINTS =================
# Endpoint chuẩn OpenAI để tương thích với Codex, Cursor, Continue.dev, Cline, v.v.

AVAILABLE_MODELS = [
    "gemini-4-argon",
    "gemini-3.8-flash-tiered",
    "gemini-2.5-flash",
    "claude-sonnet-4-6",
    # Alias models — tự động chuyển hướng bên trong
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-3-pro",
    "gemini-3.1-pro",
    "gemini-3.1-pro-high",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gpt-oss-120b",
    "gpt-5.6-luna",
    "gpt-5.6-terra",
    "gpt-reserve",
    "gpt-5.5",
]

@app.get("/v1/models", response_model=OpenAIModelList)
def openai_list_models():
    """Liệt kê tất cả model khả dụng — chuẩn OpenAI /v1/models"""
    return OpenAIModelList(
        data=[OpenAIModelInfo(id=m, created=int(time.time())) for m in AVAILABLE_MODELS]
    )

@app.post("/v1/chat/completions")
def openai_chat_completions(req: OpenAIChatRequest, request: Request = None, auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)):
    """Endpoint chat chuẩn OpenAI — tương thích hoàn toàn với OpenAI SDK, Codex, Cursor, Cline, Continue.dev (hỗ trợ cả Streaming và Non-streaming)"""
    try:
        api_token, user_info, key_info = auth_data

        model_name = req.model or config.DEFAULT_MODEL

        # Tách system prompt từ messages
        system_prompt = extract_system_prompt(req.messages) or None
        conversation_messages = []
        for msg in req.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("system", "developer"):
                continue
            else:
                conversation_messages.append(msg)

        # Nếu không có contents nào (messages rỗng hoặc chỉ có system)
        contents_to_send = normalize_messages_for_antigravity(
            messages=conversation_messages, antigravity_client=antigravity_client,
        )
        if not contents_to_send:
            raise HTTPException(status_code=400, detail="Không có tin nhắn user nào trong danh sách messages.")

        # Trích xuất prompt từ tin nhắn user cuối
        prompt = ""
        for msg in reversed(conversation_messages):
            if msg.get("role") in ("user", "human"):
                prompt = message_text(msg)
                break

        # Xử lý Streaming Response chuẩn OpenAI Chat Completions (SSE)
        if req.stream:
            stream_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
            created_ts = int(time.time())

            def openai_stream_generator(should_cancel, register_response):
                def chunk(delta, finish_reason=None, usage=None, model=None):
                    record = {
                        "id": stream_id, "object": "chat.completion.chunk", "created": created_ts,
                        "model": model or model_name,
                        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
                    }
                    if usage is not None:
                        record["usage"] = usage
                    return _sse_record(None, record)

                yield chunk({"role": "assistant", "content": ""})
                upstream = antigravity_client.generate_stream(
                    prompt=prompt, model=model_name, thinking=False, web_search=True,
                    system_prompt=system_prompt,
                    temperature=req.temperature if req.temperature is not None else 0.7,
                    max_tokens=req.max_tokens if req.max_tokens is not None else 8192,
                    contents=contents_to_send, should_cancel=should_cancel,
                    register_response=register_response,
                )
                try:
                    for ev in upstream:
                        if should_cancel():
                            return
                        kind = ev.get("type")
                        if kind == "chunk" and ev.get("text"):
                            yield chunk({"content": ev["text"]}, model=ev.get("model"))
                        elif kind == "thought" and ev.get("text"):
                            yield chunk({"reasoning_content": ev["text"]}, model=ev.get("model"))
                        elif kind == "error":
                            error = GatewayProtocolError(ev.get("error_code", "UPSTREAM_ERROR"), ev.get("error", "AI Gateway báo lỗi."), retryable=ev.get("retryable", False), finish_reason=ev.get("finish_reason"))
                            error.usage = ev.get("usage") or ev.get("tokens")
                            error.model = ev.get("model")
                            raise error
                        elif kind == "done":
                            calls = ev.get("function_calls") or ([ev["function_call"]] if ev.get("function_call") else [])
                            _require_answer(ev.get("text"), calls)
                            if calls:
                                tool_calls = [{"index": i, "id": f"call_{uuid.uuid4().hex[:16]}", "type": "function",
                                               "function": {"name": call.get("name", ""), "arguments": json.dumps(call.get("args", {}), ensure_ascii=False)}}
                                              for i, call in enumerate(calls)]
                                yield chunk({"tool_calls": tool_calls}, model=ev.get("model"))
                            usage = ev.get("usage", {})
                            user_manager.record_usage(api_token, usage.get("total_tokens", 0))
                            yield chunk({}, "tool_calls" if calls else "stop", usage, ev.get("model"))
                            yield "data: [DONE]\n\n"
                            return
                    if not should_cancel():
                        raise GatewayProtocolError("STREAM_INCOMPLETE", "Luồng AI kết thúc trước sự kiện hoàn tất.")
                finally:
                    if hasattr(upstream, "close"):
                        upstream.close()

            return _managed_sse(openai_stream_generator, request, openai=True, on_error=lambda envelope: _record_error_usage(api_token, envelope))

        # Gọi Antigravity backend (Non-streaming)
        answer, account_used, blocks, usage_dict, metadata = antigravity_client.generate(
            prompt=prompt,
            model=model_name,
            thinking=False,
            web_search=True,
            system_prompt=system_prompt,
            temperature=req.temperature if req.temperature is not None else 0.7,
            max_tokens=req.max_tokens if req.max_tokens is not None else 8192,
            contents=contents_to_send,
            return_blocks=True,
            return_usage=True,
            return_metadata=True,
        )
        _require_answer(answer, metadata.get("function_calls"))

        # Ghi nhận usage cho API Key
        est_tokens = usage_dict.get("total_tokens") or (len(prompt or "") // 4 + len(answer or "") // 4)
        user_manager.record_usage(api_token, est_tokens)

        # Wrap kết quả vào format OpenAI response
        calls = metadata.get("function_calls") or []
        message = {"role": "assistant", "content": answer}
        if calls:
            message["tool_calls"] = [{"id": f"call_{uuid.uuid4().hex[:16]}", "type": "function",
                                      "function": {"name": call.get("name", ""), "arguments": json.dumps(call.get("args", {}), ensure_ascii=False)}}
                                     for call in calls]
        return OpenAIChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            created=int(time.time()),
            model=metadata.get("model") or model_name,
            choices=[
                OpenAIChoice(
                    index=0,
                    message=message,
                    finish_reason="tool_calls" if calls else "stop"
                )
            ],
            usage=OpenAIUsage(
                prompt_tokens=usage_dict.get("prompt_tokens", 0),
                completion_tokens=usage_dict.get("completion_tokens", 0),
                total_tokens=usage_dict.get("total_tokens", 0)
            ),
            system_fingerprint=f"ag-{account_used}"
        )

    except HTTPException:
        raise
    except GatewayProtocolError as error:
        _record_error_usage(api_token, error.as_event())
        raise HTTPException(status_code=502, detail=error.as_event()) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as e:
        logger.error(f"Lỗi xử lý OpenAI chat completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.head("/v1/responses")
@app.head("/responses")
def head_responses():
    """Healthcheck endpoint cho Responses API (Codex CLI kiểm tra HEAD trước khi thực hiện inference)"""
    return Response(status_code=200)

@app.post("/v1/responses")
@app.post("/responses")
async def openai_responses_endpoint(
    request: Request,
    auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)
):
    """Endpoint OpenAI Responses API (chuẩn hiện đại của OpenAI Codex, Cursor, agentic tools)"""
    try:
        api_token, user_info, key_info = auth_data

        try:
            body = await request.json()
            logger.info(f"Codex /v1/responses received payload: {json.dumps(body, ensure_ascii=False)[:500]}")
        except Exception:
            body = {}

        model_name = body.get("model") or config.DEFAULT_MODEL
        inp = body.get("input", "")
        instructions = body.get("instructions")
        system_prompt = instructions.strip() if (instructions and isinstance(instructions, str) and instructions.strip()) else None
        stream = body.get("stream", False)

        # Chuyển đổi input thành format contents Gemini
        contents_to_send = []
        prompt = ""

        def extract_text_from_node(node: Any) -> str:
            if isinstance(node, str):
                return node.strip()
            if isinstance(node, dict):
                # Ưu tiên các trường văn bản phổ biến trong Responses API
                for k in ("text", "input_text", "output_text", "content"):
                    v = node.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
            return ""

        if isinstance(inp, str):
            prompt = inp.strip()
            if prompt:
                contents_to_send = [{"role": "user", "parts": [{"text": prompt}]}]
        elif isinstance(inp, list):
            for item in inp:
                if isinstance(item, str):
                    if item.strip():
                        contents_to_send.append({"role": "user", "parts": [{"text": item.strip()}]})
                elif isinstance(item, dict):
                    item_type = item.get("type")
                    role = item.get("role", "user")

                    # Xử lý các loại item công cụ đặc thù của Codex Responses API
                    if item_type == "custom_tool_call":
                        raw_js = item.get("input", "")
                        m = re.search(r'tools\.exec_command\(\s*\{.*?cmd\s*:\s*(".*?"|\'.*?\')', raw_js, re.DOTALL)
                        cmd_str = ""
                        if m:
                            try:
                                cmd_str = json.loads(m.group(1))
                            except Exception:
                                cmd_str = m.group(1).strip("\"'")
                        else:
                            cmd_str = raw_js.strip()
                        contents_to_send.append({
                            "role": "model",
                            "parts": [{"text": f"Tôi sẽ chạy lệnh sau trên terminal:\n```powershell\n{cmd_str}\n```"}]
                        })
                        continue

                    elif item_type == "custom_tool_call_output":
                        out_list = item.get("output", [])
                        out_texts = []
                        if isinstance(out_list, list):
                            for o in out_list:
                                if isinstance(o, dict) and o.get("text"):
                                    out_texts.append(o["text"])
                                elif isinstance(o, str):
                                    out_texts.append(o)
                        output_str = "\n".join(out_texts).strip()
                        contents_to_send.append({
                            "role": "user",
                            "parts": [{"text": f"[Kết quả thực thi dòng lệnh từ hệ thống]:\n{output_str}\n\nHãy phân tích kết quả trên và tiếp tục thực hiện bước tiếp theo để giải quyết yêu cầu."}]
                        })
                        continue

                    elif item_type == "function_call":
                        fn_name = item.get("name", "tool")
                        args = item.get("arguments", "")
                        contents_to_send.append({
                            "role": "model",
                            "parts": [{"text": f"Tôi sẽ gọi công cụ `{fn_name}` với tham số: {args}"}]
                        })
                        continue

                    elif item_type == "function_call_output":
                        fn_out = item.get("output", "")
                        contents_to_send.append({
                            "role": "user",
                            "parts": [{"text": f"[Kết quả trả về từ công cụ]:\n{fn_out}\n"}]
                        })
                        continue

                    gemini_role = "model" if role == "assistant" else "user"

                    parts = []
                    # 1. Nếu item có mảng content
                    content_val = item.get("content")
                    if isinstance(content_val, str) and content_val.strip():
                        parts.append({"text": content_val.strip()})
                    elif isinstance(content_val, list):
                        for sub in content_val:
                            t = extract_text_from_node(sub)
                            if t:
                                parts.append({"text": t})
                            elif isinstance(sub, dict):
                                img_url = sub.get("image_url", {})
                                url = img_url.get("url", "") if isinstance(img_url, dict) else str(img_url)
                                if url and url.startswith("data:"):
                                    try:
                                        mime, b64_data = antigravity_client.parse_image(url)
                                        parts.append({"inlineData": {"mimeType": mime, "data": b64_data}})
                                    except Exception:
                                        pass
                    # 2. Nếu item trực tiếp chứa text/input_text (không bọc trong content)
                    else:
                        direct_text = extract_text_from_node(item)
                        if direct_text:
                            parts.append({"text": direct_text})

                    if parts:
                        contents_to_send.append({"role": gemini_role, "parts": parts})

            # Tìm câu hỏi prompt user gần nhất để cung cấp cho Google Grounding
            for c in reversed(contents_to_send):
                if c.get("role") == "user":
                    user_texts = [p.get("text", "") for p in c.get("parts", []) if p.get("text")]
                    if user_texts:
                        prompt = " ".join(user_texts).strip()
                        break

            # Gộp các lượt liên tiếp cùng role để đảm bảo xen kẽ nghiêm ngặt user -> model -> user
            normalized_contents: List[Dict[str, Any]] = []
            for turn in contents_to_send:
                if not normalized_contents:
                    normalized_contents.append(turn)
                else:
                    if normalized_contents[-1]["role"] == turn["role"]:
                        normalized_contents[-1]["parts"].extend(turn["parts"])
                    else:
                        normalized_contents.append(turn)

            # Lượt đầu tiên phải là user
            while normalized_contents and normalized_contents[0]["role"] != "user":
                normalized_contents.pop(0)

            contents_to_send = normalized_contents

        if not contents_to_send:
            fallback_prompt = prompt or "Xin chào"
            contents_to_send = [{"role": "user", "parts": [{"text": fallback_prompt}]}]
            prompt = fallback_prompt

        logger.info(f"Codex extracted prompt: '{prompt}' | turns: {len(contents_to_send)}")

        exec_tool = [
            {
                "functionDeclarations": [
                    {
                        "name": "exec_command",
                        "description": "Execute a shell or powershell command on the user's computer to run, build, test, inspect, or manage the project.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "cmd": {
                                    "type": "STRING",
                                    "description": "The exact shell/powershell command string to execute, e.g. 'Get-ChildItem -Path .', 'npm run dev', 'php artisan serve'."
                                }
                            },
                            "required": ["cmd"]
                        }
                    }
                ]
            }
        ]

        codex_system_instructions = (
            (system_prompt or "") +
            "\n\n[CHỈ DẪN QUAN TRỌNG VỀ QUYỀN VÀ CÔNG CỤ TERMINAL]\n"
            "Bạn đang chạy bên trong ứng dụng Codex Desktop với ĐẦY ĐỦ QUYỀN thực thi dòng lệnh terminal/powershell trên máy tính của người dùng thông qua công cụ 'exec_command'.\n"
            "- Khi người dùng yêu cầu: chạy dự án, kiểm tra thư mục, đọc/sửa file, cài thư viện, khởi động server, hoặc chạy test:\n"
            "- BẠN BẮT BUỘC PHẢI GỌI HÀM 'exec_command' để trực tiếp thực thi câu lệnh trên máy người dùng!\n"
            "- TUYỆT ĐỐI KHÔNG trả lời rằng bạn không có quyền hoặc không có công cụ dòng lệnh!\n"
            "- TUYỆT ĐỐI KHÔNG chỉ liệt kê câu lệnh bằng văn bản rồi bảo người dùng tự mở terminal gõ, mà HÃY GỌI HÀM 'exec_command' để chạy ngay lập tức!"
        )

        resp_id = f"resp_{uuid.uuid4().hex[:24]}"
        msg_id = f"msg_{uuid.uuid4().hex[:16]}"

        if stream:
            async def event_generator():
                out_items = []
                out_idx = 0
                has_started_msg = False
                accumulated_answer = ""
                final_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

                # 1. response.created
                ev1 = {
                    "type": "response.created",
                    "response": {
                        "id": resp_id,
                        "object": "response",
                        "status": "in_progress",
                        "model": model_name
                    }
                }
                yield f"data: {json.dumps(ev1, ensure_ascii=False)}\n\n"

                for ev in antigravity_client.generate_stream(
                    prompt=prompt,
                    model=model_name,
                    thinking=False,
                    web_search=False,
                    system_prompt=codex_system_instructions,
                    temperature=0.3,
                    max_tokens=8192,
                    contents=contents_to_send,
                    tools=exec_tool,
                ):
                    ev_type = ev.get("type")
                    if ev_type == "chunk":
                        chunk_text = ev.get("text", "")
                        if chunk_text:
                            accumulated_answer += chunk_text
                            if not has_started_msg:
                                has_started_msg = True
                                ev2 = {
                                    "type": "response.output_item.added",
                                    "output_index": out_idx,
                                    "item": {
                                        "id": msg_id,
                                        "type": "message",
                                        "status": "in_progress",
                                        "role": "assistant",
                                        "content": []
                                    }
                                }
                                yield f"data: {json.dumps(ev2, ensure_ascii=False)}\n\n"

                                ev3 = {
                                    "type": "response.content_part.added",
                                    "output_index": out_idx,
                                    "content_index": 0,
                                    "part": {
                                        "type": "output_text",
                                        "text": ""
                                    }
                                }
                                yield f"data: {json.dumps(ev3, ensure_ascii=False)}\n\n"

                            ev4 = {
                                "type": "response.output_text.delta",
                                "output_index": out_idx,
                                "content_index": 0,
                                "delta": chunk_text
                            }
                            yield f"data: {json.dumps(ev4, ensure_ascii=False)}\n\n"

                    elif ev_type == "function_call":
                        fn_call = ev.get("function_call", {})
                        if fn_call:
                            if has_started_msg:
                                ev5 = {
                                    "type": "response.output_text.done",
                                    "output_index": out_idx,
                                    "content_index": 0,
                                    "text": accumulated_answer
                                }
                                yield f"data: {json.dumps(ev5, ensure_ascii=False)}\n\n"
                                ev6 = {
                                    "type": "response.content_part.done",
                                    "output_index": out_idx,
                                    "content_index": 0,
                                    "part": {"type": "output_text", "text": accumulated_answer}
                                }
                                yield f"data: {json.dumps(ev6, ensure_ascii=False)}\n\n"
                                msg_item = {
                                    "id": msg_id,
                                    "type": "message",
                                    "status": "completed",
                                    "role": "assistant",
                                    "content": [{"type": "output_text", "text": accumulated_answer}]
                                }
                                ev7 = {
                                    "type": "response.output_item.done",
                                    "output_index": out_idx,
                                    "item": msg_item
                                }
                                yield f"data: {json.dumps(ev7, ensure_ascii=False)}\n\n"
                                out_items.append(msg_item)
                                out_idx += 1
                                has_started_msg = False

                            call_id = f"call_{uuid.uuid4().hex[:24]}"
                            ctc_id = f"ctc_{uuid.uuid4().hex[:24]}"
                            cmd = fn_call.get("args", {}).get("cmd") or fn_call.get("args", {}).get("command") or ""
                            js_code = f"const r = await tools.exec_command({{cmd: {json.dumps(cmd)}}}); text(r.output);\n"

                            ev_tool_add = {
                                "type": "response.output_item.added",
                                "output_index": out_idx,
                                "item": {
                                    "id": ctc_id,
                                    "type": "custom_tool_call",
                                    "status": "in_progress",
                                    "call_id": call_id,
                                    "name": "exec",
                                    "input": ""
                                }
                            }
                            yield f"data: {json.dumps(ev_tool_add, ensure_ascii=False)}\n\n"

                            ev_tool_delta = {
                                "type": "response.custom_tool_call_input.delta",
                                "output_index": out_idx,
                                "call_id": call_id,
                                "delta": js_code
                            }
                            yield f"data: {json.dumps(ev_tool_delta, ensure_ascii=False)}\n\n"

                            ev_tool_done = {
                                "type": "response.custom_tool_call_input.done",
                                "output_index": out_idx,
                                "call_id": call_id,
                                "input": js_code
                            }
                            yield f"data: {json.dumps(ev_tool_done, ensure_ascii=False)}\n\n"

                            tool_item = {
                                "id": ctc_id,
                                "type": "custom_tool_call",
                                "status": "completed",
                                "call_id": call_id,
                                "name": "exec",
                                "input": js_code
                            }
                            ev_tool_item_done = {
                                "type": "response.output_item.done",
                                "output_index": out_idx,
                                "item": tool_item
                            }
                            yield f"data: {json.dumps(ev_tool_item_done, ensure_ascii=False)}\n\n"
                            out_items.append(tool_item)
                            out_idx += 1

                    elif ev_type == "done":
                        usage_data = ev.get("usage", {})
                        final_usage = {
                            "input_tokens": usage_data.get("prompt_tokens", 0),
                            "output_tokens": usage_data.get("completion_tokens", 0),
                            "total_tokens": usage_data.get("total_tokens", 0)
                        }
                        user_manager.record_usage(api_token, final_usage["total_tokens"])

                if has_started_msg:
                    ev5 = {
                        "type": "response.output_text.done",
                        "output_index": out_idx,
                        "content_index": 0,
                        "text": accumulated_answer
                    }
                    yield f"data: {json.dumps(ev5, ensure_ascii=False)}\n\n"
                    ev6 = {
                        "type": "response.content_part.done",
                        "output_index": out_idx,
                        "content_index": 0,
                        "part": {"type": "output_text", "text": accumulated_answer}
                    }
                    yield f"data: {json.dumps(ev6, ensure_ascii=False)}\n\n"
                    msg_item = {
                        "id": msg_id,
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": accumulated_answer}]
                    }
                    ev7 = {
                        "type": "response.output_item.done",
                        "output_index": out_idx,
                        "item": msg_item
                    }
                    yield f"data: {json.dumps(ev7, ensure_ascii=False)}\n\n"
                    out_items.append(msg_item)
                    out_idx += 1

                # 4. response.completed (kết thúc toàn bộ response)
                ev8 = {
                    "type": "response.completed",
                    "response": {
                        "id": resp_id,
                        "object": "response",
                        "status": "completed",
                        "model": model_name,
                        "output": out_items,
                        "usage": final_usage
                    }
                }
                yield f"data: {json.dumps(ev8, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        # Xử lý non-streaming khi stream=False
        answer, function_call, account_used, blocks, usage_dict = antigravity_client.generate(
            prompt=prompt,
            model=model_name,
            thinking=False,
            web_search=False,
            system_prompt=codex_system_instructions,
            temperature=0.3,
            max_tokens=8192,
            contents=contents_to_send,
            tools=exec_tool,
            return_function_call=True,
            return_blocks=True,
            return_usage=True
        )

        p_tokens = usage_dict.get("prompt_tokens", 0)
        c_tokens = usage_dict.get("completion_tokens", 0)
        tot_tokens = usage_dict.get("total_tokens", 0)
        user_manager.record_usage(api_token, tot_tokens)

        # Xử lý non-streaming
        out_items = []
        if answer and answer.strip():
            out_items.append({
                "id": msg_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": answer
                    }
                ]
            })
        if function_call:
            call_id = f"call_{uuid.uuid4().hex[:24]}"
            ctc_id = f"ctc_{uuid.uuid4().hex[:24]}"
            cmd = function_call.get("args", {}).get("cmd") or function_call.get("args", {}).get("command") or ""
            js_code = f"const r = await tools.exec_command({{cmd: {json.dumps(cmd)}}}); text(r.output);\n"
            out_items.append({
                "id": ctc_id,
                "type": "custom_tool_call",
                "status": "completed",
                "call_id": call_id,
                "name": "exec",
                "input": js_code
            })

        return {
            "id": resp_id,
            "object": "response",
            "status": "completed",
            "model": model_name,
            "output": out_items,
            "usage": {
                "input_tokens": p_tokens,
                "output_tokens": c_tokens,
                "total_tokens": tot_tokens
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý Responses API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ================= GEMINI-COMPATIBLE ENDPOINTS =================
# Endpoint chuẩn Google Gemini API: /v1beta/models/...:generateContent
# Tương thích với Google GenAI SDK (@google/genai, google-generativeai python), Gemini CLI, v.v.

@app.post("/v1beta/models/{model_path:path}:generateContent")
@app.post("/v1/models/{model_path:path}:generateContent")
async def gemini_generate_content(
    model_path: str,
    request: Request,
    auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)
):
    """Endpoint tương thích 100% chuẩn Google Gemini REST API (v1beta & v1)"""
    try:
        api_token, user_info, key_info = auth_data

        # Lấy model_name từ URL path (loại bỏ tiền tố models/ nếu có)
        model_name = model_path.strip().split(":")[-1] if ":" in model_path else model_path.strip()
        if model_name.startswith("models/"):
            model_name = model_name[7:]
        if not model_name:
            model_name = config.DEFAULT_MODEL

        # Đọc body JSON
        try:
            body = await request.json()
        except Exception:
            body = {}

        contents = body.get("contents", [])
        if not contents:
            raise HTTPException(status_code=400, detail="Thiếu trường 'contents' bắt buộc theo chuẩn Gemini API.")

        generation_config = body.get("generationConfig", {}) or {}
        temperature = generation_config.get("temperature", 0.7)
        max_tokens = generation_config.get("maxOutputTokens", 8192)

        # System instruction nếu có
        system_prompt = None
        sys_inst = body.get("systemInstruction", {}) or {}
        if isinstance(sys_inst, dict):
            sys_parts = sys_inst.get("parts", [])
            sys_texts = [p.get("text", "") for p in sys_parts if isinstance(p, dict) and p.get("text")]
            if sys_texts:
                system_prompt = "\n".join(sys_texts)
        elif isinstance(sys_inst, str):
            system_prompt = sys_inst

        # Trích xuất prompt từ turn cuối để dự phòng
        prompt = ""
        for c in reversed(contents):
            if c.get("role") in ("user", None):
                parts = c.get("parts", [])
                for p in parts:
                    if isinstance(p, dict) and p.get("text"):
                        prompt = p.get("text")
                        break
                if prompt:
                    break

        answer, account_used, blocks, usage_dict = antigravity_client.generate(
            prompt=prompt,
            model=model_name,
            thinking=False,
            web_search=True,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            contents=contents,
            return_blocks=True,
            return_usage=True
        )

        # Ghi nhận usage
        est_tokens = usage_dict.get("total_tokens") or (len(prompt or "") // 4 + len(answer or "") // 4)
        user_manager.record_usage(api_token, est_tokens)

        # Format phản hồi chuẩn Gemini API
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": answer}
                        ],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0
                }
            ],
            "usageMetadata": {
                "promptTokenCount": usage_dict.get("prompt_tokens", 0),
                "candidatesTokenCount": usage_dict.get("completion_tokens", 0),
                "totalTokenCount": usage_dict.get("total_tokens", 0)
            },
            "modelVersion": model_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý Gemini generateContent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1beta/models/{model_path:path}:streamGenerateContent")
@app.post("/v1/models/{model_path:path}:streamGenerateContent")
async def gemini_stream_generate_content(
    model_path: str,
    request: Request,
    auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)
):
    """Endpoint tương thích 100% chuẩn Google Gemini REST API Streaming (v1beta & v1)"""
    try:
        api_token, user_info, key_info = auth_data

        model_name = model_path.strip().split(":")[-1] if ":" in model_path else model_path.strip()
        if model_name.startswith("models/"):
            model_name = model_name[7:]
        if not model_name:
            model_name = config.DEFAULT_MODEL

        try:
            body = await request.json()
        except Exception:
            body = {}

        contents = body.get("contents", [])
        if not contents:
            raise HTTPException(status_code=400, detail="Thiếu trường 'contents' bắt buộc theo chuẩn Gemini API.")

        generation_config = body.get("generationConfig", {}) or {}
        temperature = generation_config.get("temperature", 0.7)
        max_tokens = generation_config.get("maxOutputTokens", 8192)

        system_prompt = None
        sys_inst = body.get("systemInstruction", {}) or {}
        if isinstance(sys_inst, dict):
            sys_parts = sys_inst.get("parts", [])
            sys_texts = [p.get("text", "") for p in sys_parts if isinstance(p, dict) and p.get("text")]
            if sys_texts:
                system_prompt = "\n".join(sys_texts)
        elif isinstance(sys_inst, str):
            system_prompt = sys_inst

        prompt = ""
        for c in reversed(contents):
            if c.get("role") in ("user", None):
                parts = c.get("parts", [])
                for p in parts:
                    if isinstance(p, dict) and p.get("text"):
                        prompt = p.get("text")
                        break
                if prompt:
                    break

        def gemini_sse_generator():
            final_usage = None
            for ev in antigravity_client.generate_stream(
                prompt=prompt,
                model=model_name,
                thinking=False,
                web_search=True,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                contents=contents,
            ):
                ev_type = ev.get("type")
                if ev_type == "chunk":
                    chunk_text = ev.get("text", "")
                    if chunk_text:
                        chunk_payload = {
                            "candidates": [
                                {
                                    "content": {
                                        "parts": [{"text": chunk_text}],
                                        "role": "model"
                                    },
                                    "index": 0
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
                elif ev_type == "done":
                    final_usage = ev.get("usage", {})
                    user_manager.record_usage(api_token, final_usage.get("total_tokens", 0))

            done_payload = {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": ""}],
                            "role": "model"
                        },
                        "finishReason": "STOP",
                        "index": 0
                    }
                ],
                "modelVersion": model_name
            }
            if final_usage:
                done_payload["usageMetadata"] = {
                    "promptTokenCount": final_usage.get("prompt_tokens", 0),
                    "candidatesTokenCount": final_usage.get("completion_tokens", 0),
                    "totalTokenCount": final_usage.get("total_tokens", 0)
                }
            yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            gemini_sse_generator(),
            media_type="text/event-stream",
            headers={
                "Content-Type": "text/event-stream; charset=utf-8",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý Gemini streamGenerateContent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/chat/parse-blocks")
def parse_chat_blocks(req: ParseBlocksRequest):
    """Phân giải trực tiếp chuỗi văn bản Markdown thành các khối JSON có cấu trúc chuyên biệt"""
    from response_parser import parse_response_to_blocks
    blocks = parse_response_to_blocks(req.text)
    return {
        "status": "success",
        "total_blocks": len(blocks),
        "blocks": blocks
    }

@app.post("/api/read-folder", response_model=ReadFolderResponse)
def read_folder_api(req: ReadFolderRequest):
    """
    Quét và đọc toàn bộ các file trong thư mục trên máy tính/máy chủ:
    - Xây dựng cây thư mục ASCII
    - Trích xuất toàn bộ nội dung code, text, tài liệu bên trong
    - Trả về context sẵn sàng đưa vào hội thoại của AI
    """
    res = file_processor.scan_directory_on_disk(
        folder_path=req.folder_path,
        max_files=req.max_files or 80,
        max_file_size=int((req.max_file_size_kb or 250) * 1024)
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Không thể đọc thư mục"))
    return res

@app.post("/api/read-file", response_model=ReadFileResponse)
def read_file_api(req: ReadFileRequest):
    """
    Đọc và trích xuất nội dung của một file cụ thể trên máy tính/máy chủ theo nhu cầu (On-Demand).
    """
    res = file_processor.read_single_file_from_disk(
        file_path=req.file_path,
        max_size=int((req.max_size_kb or 500) * 1024)
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Không thể đọc file"))
    return res


# ----------------- SESSION APIS -----------------
@app.get("/api/sessions")
def list_sessions_api():
    return session_manager.list_sessions()

@app.get("/api/sessions/{session_id}")
def get_session_detail_api(session_id: str):
    messages = session_manager.get_messages(session_id)
    return {"session_id": session_id, "messages": messages}

@app.post("/api/sessions/{session_id}/clear")
def clear_session_api(session_id: str):
    session_manager.clear_session(session_id)
    return {"session_id": session_id, "cleared": True}

@app.delete("/api/sessions/{session_id}")
def delete_session_api(session_id: str):
    session_manager.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}

# ----------------- ACCOUNT MANAGEMENT APIs (Chỉ dành cho Admin) -----------------
@app.get("/api/accounts")
def list_accounts(admin: Dict[str, Any] = Depends(verify_admin_access)):
    return account_manager.get_accounts_public()

@app.get("/api/accounts/quota-overview")
def get_accounts_quota_overview(force_refresh: bool = False, admin: Dict[str, Any] = Depends(verify_admin_access)):
    """Lấy tổng hợp hạn ngạch (% đã dùng, % còn lại) thực tế từ Google Antigravity cho toàn bộ tài khoản"""
    accounts = account_manager.load_accounts()
    return quota_fetcher.fetch_all_accounts_quota(accounts, force_refresh=force_refresh)

@app.get("/api/accounts/{account_id}/quota")
def get_account_quota_detail(account_id: str, force_refresh: bool = False, admin: Dict[str, Any] = Depends(verify_admin_access)):
    """Lấy hạn ngạch chi tiết của một tài khoản Google cụ thể"""
    acc = account_manager.get_account_by_id(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    return quota_fetcher.fetch_account_quota(acc, force_refresh=force_refresh)

@app.post("/api/accounts/oauth/start")
def start_oauth_flow(admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        return account_manager.start_oauth_flow()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts/manual")
def add_account_manual(req: ManualAccountRequest, admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        acc = account_manager.exchange_code_or_url(req.refresh_token, req.name)
        return {
            "status": "success",
            "id": acc["id"],
            "email": acc["email"],
            "name": acc["name"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/accounts/oauth/exchange")
def exchange_oauth_code(req: OAuthExchangeRequest, admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        acc = account_manager.exchange_code_or_url(req.code_or_url, req.name)
        return {
            "status": "success",
            "id": acc["id"],
            "email": acc["email"],
            "name": acc["name"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/accounts/{account_id}/toggle")
def toggle_account(account_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    new_state = account_manager.toggle_account(account_id)
    return {"id": account_id, "is_active": new_state}

@app.post("/api/accounts/{account_id}/reset-cooldown")
def reset_account_cooldown(account_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    account_manager.reset_cooldown(account_id)
    return {"id": account_id, "cooldown_reset": True}

@app.post("/api/accounts/{account_id}/primary")
def set_primary_account(account_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    account_manager.set_primary(account_id)
    return {"id": account_id, "is_primary": True}

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    account_manager.delete_account(account_id)
    return {"id": account_id, "deleted": True}

@app.post("/api/accounts/{account_id}/test")
def test_account(account_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    acc = account_manager.get_account_by_id(account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    try:
        token = antigravity_client.get_token_for_account(acc, force_refresh=True)
        proj = account_manager.resolve_project_id(token)
        account_manager.report_success(account_id)
        return {
            "status": "ok",
            "email": acc.get("email"),
            "project_id": proj
        }
    except Exception as e:
        account_manager.mark_rate_limited(account_id, 300, str(e))
        raise HTTPException(status_code=400, detail=str(e))

def sync_admin_user_api_key(new_key: str, admin_user_id: Optional[str] = None):
    """Đồng bộ đảm bảo API Key duy nhất giữa config.API_KEY và tài khoản Admin"""
    try:
        import db
        if not admin_user_id:
            adm = db.fetch_one("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
            if adm:
                admin_user_id = adm["id"]
        if admin_user_id:
            existing = db.fetch_one("SELECT id FROM api_keys WHERE user_id = %s ORDER BY created_at ASC LIMIT 1", (admin_user_id,))
            if existing:
                db.execute("UPDATE api_keys SET key_value = %s, is_active = 1 WHERE id = %s", (new_key, existing["id"]))
            else:
                user_manager.create_api_key(admin_user_id, name="Admin Key", custom_key=new_key)
            if user_manager.API_KEYS_FILE.exists():
                try:
                    all_keys = json.loads(user_manager.API_KEYS_FILE.read_text(encoding="utf-8"))
                    found = False
                    for k in all_keys:
                        if k.get("user_id") == admin_user_id:
                            k["key_value"] = new_key
                            k["is_active"] = True
                            found = True
                            break
                    if not found:
                        all_keys.append({
                            "id": f"key_{uuid.uuid4().hex[:8]}",
                            "user_id": admin_user_id,
                            "key_value": new_key,
                            "name": "Admin Key",
                            "is_active": True,
                            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                    user_manager.API_KEYS_FILE.write_text(json.dumps(all_keys, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Lỗi đồng bộ Admin API Key: {e}")

@app.get("/api/settings")
def get_settings(admin: Dict[str, Any] = Depends(verify_admin_access)):
    # Đảm bảo trả về API Key duy nhất của Admin
    admin_id = admin.get("id")
    current_key = config.API_KEY
    if admin_id:
        keys = user_manager._db_fetch_keys_for_user(admin_id)
        active_key = next((k["key_value"] for k in keys if k.get("is_active")), None)
        if active_key:
            current_key = active_key
            if config.API_KEY != active_key:
                config.API_KEY = active_key
    return {
        "status": "ok",
        "api_key": current_key,
        "strategy": account_manager.strategy,
        "default_model": config.DEFAULT_MODEL
    }

@app.post("/api/settings/generate-key")
def generate_random_api_key_endpoint(admin: Dict[str, Any] = Depends(verify_admin_access)):
    new_key = config.generate_random_api_key()
    old_key = config.API_KEY
    config.API_KEY = new_key

    # Đồng bộ vào tài khoản Admin
    sync_admin_user_api_key(new_key, admin.get("id"))

    # Lưu persistent vào settings.json
    persisted = config.get_persisted_settings()
    previous = persisted.get("previous_api_keys", [])
    if old_key and old_key not in previous:
        previous.append(old_key)
    persisted["previous_api_keys"] = previous
    persisted["api_key"] = new_key
    config.save_persisted_settings(persisted)
    config.update_env_file("API_KEY", new_key)

    logger.info("Đã tạo ngẫu nhiên X-API-Key mới.")
    return {
        "status": "ok",
        "api_key": new_key,
        "message": "Đã tạo ngẫu nhiên X-API-Key mới thành công!"
    }

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest, admin: Dict[str, Any] = Depends(verify_admin_access)):
    if req.strategy:
        account_manager.strategy = req.strategy
        config.STRATEGY = req.strategy
        config.save_persisted_settings({"strategy": req.strategy})
        logger.info(f"Đã cập nhật chiến lược tài khoản: {req.strategy}")
    if req.generate_random_key:
        new_key = config.generate_random_api_key()
        old_key = config.API_KEY
        config.API_KEY = new_key
        sync_admin_user_api_key(new_key, admin.get("id"))
        persisted = config.get_persisted_settings()
        previous = persisted.get("previous_api_keys", [])
        if old_key and old_key not in previous:
            previous.append(old_key)
        persisted["previous_api_keys"] = previous
        persisted["api_key"] = new_key
        config.save_persisted_settings(persisted)
        config.update_env_file("API_KEY", new_key)
    elif req.api_key:
        old_key = config.API_KEY
        clean_key = req.api_key.strip()
        config.API_KEY = clean_key
        sync_admin_user_api_key(clean_key, admin.get("id"))
        persisted = config.get_persisted_settings()
        previous = persisted.get("previous_api_keys", [])
        if old_key and old_key not in previous:
            previous.append(old_key)
        persisted["previous_api_keys"] = previous
        persisted["api_key"] = clean_key
        config.save_persisted_settings(persisted)
        config.update_env_file("API_KEY", clean_key)
    if req.default_model:
        config.DEFAULT_MODEL = req.default_model
        config.save_persisted_settings({"default_model": req.default_model})
    return {
        "status": "ok",
        "api_key": config.API_KEY,
        "strategy": account_manager.strategy,
        "default_model": config.DEFAULT_MODEL
    }

# ----------------- AUTHENTICATION APIS -----------------
@app.post("/api/auth/register")
def register_endpoint(req: RegisterRequest):
    """Đăng ký tài khoản người dùng thường mới (Role: user) kèm tự động tạo API Key riêng"""
    name = (req.name or "").strip()
    email = (req.email or "").strip().lower()
    pwd = (req.password or "").strip()

    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Tên tài khoản phải có ít nhất 2 ký tự!")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Địa chỉ email đăng ký không hợp lệ!")
    if not pwd or len(pwd) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có độ dài tối thiểu 6 ký tự!")

    # Kiểm tra trùng email
    if user_manager.get_user_by_email_or_name(email):
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng! Vui lòng đăng nhập hoặc chọn email khác.")

    # Kiểm tra trùng tên
    if user_manager.get_user_by_email_or_name(name):
        raise HTTPException(status_code=400, detail="Tên người dùng này đã tồn tại! Vui lòng chọn tên khác.")

    # Tạo tài khoản mới với role user cố định
    new_user = user_manager.create_user(
        name=name,
        email=email,
        password=pwd,
        note=req.note or "Tài khoản tự đăng ký qua Web UI",
        role="user"
    )

    # Tự động tạo 1 API Key đang hoạt động cho tài khoản mới
    new_key = user_manager.create_api_key(
        user_id=new_user["id"],
        name=f"Key mặc định - {name}"
    )

    clean_user = {k: v for k, v in new_user.items() if k != "password"}
    clean_user["has_password"] = True

    return {
        "status": "success",
        "message": "Đăng ký tài khoản thành công!",
        "user": clean_user,
        "api_key": new_key["key_value"]
    }

@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    """Đăng nhập bằng Email/Tài khoản và Mật khẩu"""
    user = user_manager.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác hoặc tài khoản đã bị vô hiệu hóa!"
        )

    # Lấy API Key đang hoạt động của user
    keys = user.get("keys") or user_manager._db_fetch_keys_for_user(user["id"])
    active_key = next((k["key_value"] for k in keys if k.get("is_active")), None)
    if not active_key and keys:
        active_key = keys[0]["key_value"]
    elif not active_key:
        new_key = user_manager.create_api_key(user["id"], name="Auto Session Key")
        active_key = new_key["key_value"]

    clean_user = {k: v for k, v in user.items() if k != "password"}
    clean_user["has_password"] = bool(user.get("password"))
    return {
        "status": "success",
        "message": f"Đăng nhập thành công với vai trò {user.get('role', 'user').upper()}",
        "user": clean_user,
        "api_key": active_key
    }

# ----------------- USER & DEDICATED API KEY APIS -----------------
@app.get("/api/users/summary")
def get_users_summary(user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    """Danh sách rút gọn người dùng để phục vụ bộ chuyển đổi tài khoản trên giao diện (không lộ API Keys, chỉ hiện Admin khi đã xác thực)"""
    try:
        users = user_manager.get_users()
        is_admin = bool(user_ctx and user_ctx.get("role") == "admin")
        return [
            {
                "id": u.get("id"),
                "name": u.get("name"),
                "email": u.get("email"),
                "role": u.get("role", "user"),
                "is_active": u.get("is_active", True)
            }
            for u in users
            if u.get("is_active", True) and (is_admin or u.get("role") != "admin")
        ]
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách tóm tắt users: {e}")
        return []

@app.get("/api/users")
def get_users_list(user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Yêu cầu đăng nhập để xem danh sách tài khoản!"
            )
        users = user_manager.get_users()
        # Nếu là User thông thường, chỉ hiển thị thông tin tài khoản của chính mình
        if user_ctx.get("role") != "admin":
            users = [u for u in users if u.get("id") == user_ctx.get("id")]
        
        clean_users = []
        for u in users:
            u_copy = dict(u)
            u_copy["has_password"] = bool(u_copy.get("password"))
            u_copy.pop("password", None)
            clean_users.append(u_copy)
        return clean_users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users")
def create_user_endpoint(req: UserCreateRequest, admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        if not req.name or not req.name.strip():
            raise HTTPException(status_code=400, detail="Tên tài khoản không được để trống")
        return user_manager.create_user(
            name=req.name.strip(),
            email=req.email or "",
            password=req.password,
            note=req.note or "",
            role=req.role or "user"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi tạo tài khoản: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{user_id}")
def update_user_endpoint(user_id: str, req: UserUpdateRequest, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để chỉnh sửa tài khoản!")
        if user_ctx.get("role") != "admin" and user_ctx.get("id") != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền chỉnh sửa tài khoản của người khác!")
        if user_ctx.get("role") != "admin" and req.role is not None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Quản trị viên (Admin) mới có quyền thay đổi vai trò tài khoản!")

        updates = {k: v for k, v in req.dict().items() if v is not None}
        updated = user_manager.update_user(user_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để cập nhật")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi cập nhật tài khoản: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
def delete_user_endpoint(user_id: str, admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        target_user = user_manager.get_user(user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xóa")
        if target_user.get("id") == admin.get("id"):
            raise HTTPException(status_code=400, detail="Bạn không thể tự xóa tài khoản Quản trị viên của chính mình!")
        if (target_user.get("email") or "").strip().lower() == "nguyentrunghieu4390@gmail.com":
            raise HTTPException(status_code=400, detail="Không thể xóa tài khoản Quản trị viên Tối cao!")
        user_manager.delete_user(user_id)
        return {"id": user_id, "deleted": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xóa tài khoản: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/keys")
def get_user_keys_endpoint(user_id: str, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để xem API Key!")
        if user_ctx.get("role") != "admin" and user_ctx.get("id") != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xem API Key của tài khoản khác!")
        return user_manager.get_user_keys(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi lấy danh sách API Key của user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/keys")
def create_user_api_key_endpoint(user_id: str, req: ApiKeyCreateRequest, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để tạo API Key!")
        if user_ctx.get("role") != "admin" and user_ctx.get("id") != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền tạo API Key cho tài khoản khác!")
        if not req.name or not req.name.strip():
            raise HTTPException(status_code=400, detail="Tên gợi nhớ của Key không được để trống")
        return user_manager.create_api_key(
            user_id=user_id,
            name=req.name.strip(),
            custom_key=req.custom_key
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi tạo API Key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/keys/{key_id}/toggle")
def toggle_api_key_endpoint(key_id: str, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để đổi trạng thái API Key!")
        key_obj = user_manager.get_api_key(key_id)
        if not key_obj:
            raise HTTPException(status_code=404, detail="Không tìm thấy Key để đổi trạng thái")
        if user_ctx.get("role") != "admin" and key_obj.get("user_id") != user_ctx.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thay đổi trạng thái API Key của người khác!")
        res = user_manager.toggle_api_key(key_id)
        return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi toggle API Key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/keys/{key_id}")
def delete_api_key_endpoint(key_id: str, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    try:
        if not user_ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để xóa API Key!")
        key_obj = user_manager.get_api_key(key_id)
        if not key_obj:
            raise HTTPException(status_code=404, detail="Không tìm thấy Key để xóa")
        if user_ctx.get("role") != "admin" and key_obj.get("user_id") != user_ctx.get("id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xóa API Key của người khác!")
        user_manager.delete_api_key(key_id)
        return {"id": key_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xóa API Key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- QUOTA APIS (Chỉ dành cho Admin) -----------------
@app.get("/api/quota/stats")
def get_quota_stats(account_id: Optional[str] = None, admin: Dict[str, Any] = Depends(verify_admin_access)):
    try:
        return quota_tracker.get_stats(account_id)
    except Exception as e:
        logger.error(f"Lỗi lấy thống kê quota: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quota/clear")
def clear_quota_logs(admin: Dict[str, Any] = Depends(verify_admin_access)):
    quota_tracker.clear_logs()
    return {"status": "ok", "message": "Đã xóa toàn bộ dữ liệu thống kê quota"}

# ----------------- SKILL MANAGEMENT APIS -----------------
@app.get("/api/skills")
def list_skills(user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    user_id = user_ctx.get("id") if user_ctx else None
    return skill_manager.load_skills(user_id=user_id)

@app.post("/api/skills")
def create_skill():
    raise HTTPException(status_code=409, detail="Project chỉ giữ lại kỹ năng Viết content đã được chỉ định.")

@app.put("/api/skills/{skill_id}")
def update_skill(skill_id: str, req: SkillUpdateRequest, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    if not user_ctx:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để cập nhật kỹ năng!")
    user_id = user_ctx.get("id")
    is_admin = bool(user_ctx.get("role") == "admin")
    updates = {k: v for k, v in req.dict().items() if v is not None}
    try:
        res = skill_manager.update_skill(skill_id, updates, user_id=user_id, is_admin=is_admin)
        if not res:
            raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng để cập nhật")
        return res
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/skills/{skill_id}")
def delete_skill(skill_id: str, user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    if not user_ctx:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập để xóa kỹ năng!")
    user_id = user_ctx.get("id")
    is_admin = bool(user_ctx.get("role") == "admin")
    try:
        ok = skill_manager.delete_skill(skill_id, user_id=user_id, is_admin=is_admin)
        if not ok:
            raise HTTPException(status_code=404, detail="Không tìm thấy kỹ năng")
        return {"id": skill_id, "deleted": True}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skills/import-ai")
def import_skills_disabled():
    raise HTTPException(status_code=409, detail="Project chỉ giữ lại kỹ năng Viết content đã được chỉ định.")
# ----------------- IMAGE GENERATION APIS -----------------
@app.post("/api/image/generate", response_model=ImageGenerateResponse)
def generate_image_api(req: ImageGenerateRequest, auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)):
    try:
        width, height = image_generator.ASPECT_RATIOS.get(req.aspect_ratio or "1:1", (1024, 1024))
        cleaned = image_generator.clean_image_prompt(req.prompt)
        enhanced = cleaned
        if req.enhance_prompt:
            enhanced = image_generator.enhance_prompt_with_gemini(antigravity_client, cleaned, style=req.style)
        elif req.style:
            mod = image_generator.STYLE_MODIFIERS.get(req.style, "")
            if mod:
                enhanced = f"{cleaned}, {mod}"

        img_url, seed = image_generator.build_image_url(
            prompt=enhanced,
            width=width,
            height=height,
            model=req.model or "flux",
            seed=req.seed
        )
        md = image_generator.generate_image_markdown(
            user_prompt=req.prompt,
            enhanced_prompt=enhanced,
            image_url=img_url,
            width=width,
            height=height,
            seed=seed,
            model=req.model or "Flux.1"
        )
        # Trừ token khi tạo ảnh cho user thông thường (5,000 tokens / ảnh)
        api_token, user_info, _ = auth_data
        if user_info and user_info.get("role") != "admin":
            user_manager.deduct_user_tokens(user_info["id"], 5000)

        return ImageGenerateResponse(
            status="success",
            image_url=img_url,
            prompt=req.prompt,
            enhanced_prompt=enhanced,
            width=width,
            height=height,
            seed=seed,
            model=req.model or "flux",
            markdown=md
        )
    except Exception as e:
        logger.error(f"Lỗi tạo ảnh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/image/enhance-prompt")
def enhance_image_prompt_api(req: ImageGenerateRequest, auth_data: Tuple[str, Dict[str, Any], Dict[str, Any]] = Depends(verify_api_key)):
    try:
        cleaned = image_generator.clean_image_prompt(req.prompt)
        enhanced = image_generator.enhance_prompt_with_gemini(antigravity_client, cleaned, style=req.style)
        return {"original": req.prompt, "enhanced": enhanced}
    except Exception as e:
        logger.error(f"Lỗi tối ưu prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- MOMO PAYMENT & TOKEN BILLING APIS -----------------

@app.get("/api/payment/packages")
def get_payment_packages():
    """Lấy danh sách các gói nạp token MoMo và bảng giá"""
    return {
        "status": "success",
        "packages": TOKEN_PACKAGES,
        "rate_vnd_per_million_tokens": 10000,
        "description": "Nạp token qua MoMo QR Code & MoMo App, tự động cộng token ngay lập tức"
    }

@app.get("/api/users/me")
@app.get("/api/auth/me")
def get_current_user_profile(user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    """Lấy thông tin tài khoản hiện tại, số dư VNĐ và số dư Tokens mới nhất"""
    if not user_ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu đăng nhập hoặc cung cấp API Key hợp lệ!"
        )
    fresh_user = user_manager.get_user(user_ctx.get("id"))
    if not fresh_user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản người dùng!")
    
    clean_user = {k: v for k, v in fresh_user.items() if k != "password"}
    clean_user["has_password"] = bool(fresh_user.get("password"))
    return clean_user

@app.post("/api/payment/momo/create", response_model=MoMoPaymentCreateResponse)
def create_momo_payment(
    req: MoMoPaymentCreateRequest,
    user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)
):
    """Tạo giao dịch nạp Token qua MoMo (trả về QR Code & Deep Link MoMo App)"""
    if not user_ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để thực hiện nạp token qua MoMo!"
        )
    
    user_id = user_ctx.get("id")
    package_id = req.package_id
    amount = req.amount

    if not package_id and not amount:
        package_id = "pkg_standard"

    res = momo_service.create_payment(
        user_id=user_id,
        package_id=package_id,
        custom_amount=amount,
        redirect_url=req.redirect_url
    )

    if res.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=res.get("message", "Không thể tạo liên kết thanh toán MoMo!")
        )

    return MoMoPaymentCreateResponse(
        status="success",
        order_id=res["order_id"],
        amount=res["amount"],
        tokens=res["tokens"],
        package_name=res.get("package_name"),
        pay_url=res.get("pay_url"),
        qr_code_url=res.get("qr_code_url"),
        deeplink=res.get("deeplink"),
        message=res.get("message")
    )

@app.post("/api/payment/momo/ipn")
async def momo_ipn_webhook(request: Request):
    """Webhook IPN từ máy chủ MoMo gọi về khi người dùng quét mã thanh toán thành công"""
    try:
        body = await request.json()
        logger.info(f"Nhận tín hiệu MoMo IPN Callback: {body.get('orderId')} - Code: {body.get('resultCode')}")
    except Exception as e:
        logger.error(f"Lỗi đọc payload IPN: {e}")
        return Response(status_code=400, content="Invalid payload")

    # Xác thực chữ ký HMAC-SHA256
    is_valid = momo_service.verify_ipn(body)
    if not is_valid:
        logger.warning(f"Chữ ký IPN không hợp lệ từ MoMo: {body.get('orderId')}")
        return Response(status_code=400, content="Invalid signature")

    # Xử lý giao dịch và cộng token tự động
    res = momo_service.handle_ipn(body)
    logger.info(f"Kết quả xử lý IPN đơn {body.get('orderId')}: {res}")

    return {"resultCode": 0, "message": "IPN received successfully"}

@app.get("/api/payment/momo/check/{order_id}")
def check_momo_order_status(
    order_id: str,
    user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)
):
    """Kiểm tra trạng thái đơn hàng (dùng cho Frontend polling chờ user quét mã MoMo)"""
    if not user_ctx:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")

    import db
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM payment_transactions WHERE order_id = %s", (order_id,))
        tx = cursor.fetchone()

    if not tx:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng!")

    if user_ctx.get("role") != "admin" and tx.get("user_id") != user_ctx.get("id"):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập đơn hàng này!")

    # Nếu đơn đang pending, thử chủ động query cổng MoMo
    if tx.get("status") == "pending":
        momo_res = momo_service.check_transaction_status(order_id)
        if momo_res.get("resultCode") == 0:
            momo_service.handle_ipn(momo_res)
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM payment_transactions WHERE order_id = %s", (order_id,))
                tx = cursor.fetchone()

    # Lấy số dư token mới nhất của user
    fresh_user = user_manager.get_user(tx.get("user_id"))
    new_token_balance = fresh_user.get("token_balance", 0) if fresh_user else 0

    return {
        "status": tx.get("status"),
        "order_id": order_id,
        "amount": tx.get("amount"),
        "tokens_granted": tx.get("tokens_granted"),
        "package_name": tx.get("package_name"),
        "message": tx.get("message"),
        "user_token_balance": new_token_balance,
        "updated_at": str(tx.get("updated_at") or "")
    }

@app.get("/api/payment/my-transactions")
def get_my_transactions(user_ctx: Optional[Dict[str, Any]] = Depends(resolve_request_user)):
    """Lịch sử giao dịch nạp token của người dùng hiện tại"""
    if not user_ctx:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập!")
    return momo_service.get_user_transactions(user_ctx["id"])

@app.get("/api/payment/admin/transactions")
def get_all_transactions_admin(admin: Dict[str, Any] = Depends(verify_admin_access)):
    """Toàn bộ lịch sử giao dịch MoMo cho Admin kiểm soát"""
    return momo_service.get_all_transactions()

@app.get("/api/payment/admin/momo-config")
def get_momo_config_admin(admin: Dict[str, Any] = Depends(verify_admin_access)):
    """Xem cấu hình kết nối MoMo Gateway hiện tại (Admin)"""
    cfg = dict(momo_service.config)
    sk = cfg.get("secret_key", "")
    if sk and len(sk) > 8:
        cfg["secret_key_masked"] = sk[:4] + "********" + sk[-4:]
    else:
        cfg["secret_key_masked"] = "********"
    return cfg

@app.post("/api/payment/admin/momo-config")
def update_momo_config_admin(
    req: MoMoConfigUpdateRequest,
    admin: Dict[str, Any] = Depends(verify_admin_access)
):
    """Cập nhật Partner Code, Access Key, Secret Key MoMo (Admin)"""
    new_cfg = {}
    if req.partner_code is not None:
        new_cfg["partner_code"] = req.partner_code.strip()
    if req.access_key is not None:
        new_cfg["access_key"] = req.access_key.strip()
    if req.secret_key is not None and req.secret_key.strip():
        new_cfg["secret_key"] = req.secret_key.strip()
    if req.ipn_url is not None:
        new_cfg["ipn_url"] = req.ipn_url.strip()
    if req.redirect_url is not None:
        new_cfg["redirect_url"] = req.redirect_url.strip()
    if req.environment is not None:
        new_cfg["environment"] = req.environment.strip().lower()

    updated = momo_service.update_config(new_cfg)
    return {
        "status": "success",
        "message": "Đã cập nhật cấu hình MoMo thành công!",
        "config": {
            "partner_code": updated.get("partner_code"),
            "access_key": updated.get("access_key"),
            "ipn_url": updated.get("ipn_url"),
            "redirect_url": updated.get("redirect_url"),
            "environment": updated.get("environment")
        }
    }

@app.post("/api/users/{user_id}/tokens")
def adjust_user_tokens_endpoint(
    user_id: str,
    payload: Dict[str, Any],
    admin: Dict[str, Any] = Depends(verify_admin_access)
):
    """Admin trực tiếp cộng hoặc điều chỉnh số dư token cho người dùng"""
    tokens = int(payload.get("tokens", 0))
    amount = float(payload.get("amount", 0))
    success = user_manager.add_user_tokens(user_id, tokens, amount)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng hoặc cập nhật thất bại!")
    u = user_manager.get_user(user_id)
    return {
        "status": "success",
        "message": f"Đã cập nhật token thành công cho người dùng {u.get('name')}",
        "user": {
            "id": u.get("id"),
            "name": u.get("name"),
            "token_balance": u.get("token_balance"),
            "balance": u.get("balance")
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)

