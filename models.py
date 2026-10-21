from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from gateway_protocol import PROTOCOL_VERSION

class ChatRequest(BaseModel):
    prompt: Optional[str] = Field(None, description="Câu hỏi hoặc chỉ dẫn cho AI")
    session_id: Optional[str] = Field(None, description="ID phiên hội thoại do client định danh")
    messages: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách tin nhắn lịch sử (OpenAI/Gemini format)")
    contents: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách contents trực tiếp theo chuẩn Gemini")
    image: Optional[str] = Field(None, description="Chuỗi Base64 ảnh hoặc Data URI")
    images: Optional[List[str]] = Field(None, description="Danh sách ảnh Base64 nếu có nhiều ảnh")
    files: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách file đính kèm [{data: 'base64/dataURI', filename: 'ten.docx'}]")
    model: Optional[str] = Field(None, description="Tên model Gemini")
    thinking: Optional[bool] = Field(False, description="Có bật chế độ thinking hay không")
    web_search: Optional[bool] = Field(True, description="Cho phép AI tự động truy cập mạng tìm kiếm")
    skill_id: Optional[str] = Field(None, description="ID của Skill muốn áp dụng")
    custom_system_prompt: Optional[str] = Field(None, description="System Prompt tùy biến nếu không dùng skill_id")
    system_prompt: Optional[str] = Field(None, description="Tên tương thích cũ của custom_system_prompt")
    protocol_version: Optional[str] = Field(None, description="Phiên bản giao thức chat")
    request_id: Optional[str] = Field(None, description="ID yêu cầu do client định danh")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="Độ sáng tạo")
    max_tokens: Optional[int] = Field(8192, gt=0, description="Giới hạn token trả về")
    dual_ai_mode: Optional[bool] = Field(False, description="Có bật chế độ thảo luận và phản biện lặp giữa 2 AI hay không")
    evaluator_model: Optional[str] = Field(None, description="Mô hình đóng vai trò Giám khảo/Phản biện (Critic)")
    max_rounds: Optional[int] = Field(3, gt=0, description="Số vòng phản biện lặp tối đa giữa 2 AI")
    stream: Optional[bool] = Field(False, description="Bật/tắt streaming response chuẩn Server-Sent Events (SSE)")

class ContentBlock(BaseModel):
    type: str = Field(..., description="Loại khối nội dung: text, code, thought, table, callout, math, diagram, citations, key_value, task_list, suggestion, quote, image")
    content: Optional[str] = Field(None, description="Nội dung văn bản chính nếu có")
    language: Optional[str] = Field(None, description="Ngôn ngữ lập trình của code block hoặc loại diagram")
    filename: Optional[str] = Field(None, description="Tên file đính kèm khối code nếu có")
    lines_count: Optional[int] = Field(None, description="Số dòng code")
    title: Optional[str] = Field(None, description="Tiêu đề gợi nhớ của khối")
    variant: Optional[str] = Field(None, description="Biến thể của callout (note, tip, warning, caution, info, success)")
    headers: Optional[List[str]] = Field(None, description="Tiêu đề các cột trong bảng")
    rows: Optional[List[List[str]]] = Field(None, description="Các dòng dữ liệu trong bảng")
    alignments: Optional[List[str]] = Field(None, description="Căn lề cột (left, center, right)")
    formula: Optional[str] = Field(None, description="Công thức LaTeX toán học")
    display: Optional[bool] = Field(None, description="Hiển thị dạng block công thức")
    diagram_type: Optional[str] = Field(None, description="Loại sơ đồ (mermaid, graphviz, dot)")
    code: Optional[str] = Field(None, description="Mã nguồn sơ đồ")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách nguồn trích dẫn tìm kiếm")
    items: Optional[List[Any]] = Field(None, description="Danh sách các mục (checklist, gợi ý, key-value)")
    url: Optional[str] = Field(None, description="Đường dẫn ảnh")
    alt: Optional[str] = Field(None, description="Chú thích thay thế của ảnh")
    caption: Optional[str] = Field(None, description="Chú thích ảnh")
    raw: Optional[str] = Field(None, description="Văn bản Markdown gốc của khối")

class ChatResponse(BaseModel):
    response: str
    text: str
    model: str
    session_id: Optional[str] = None
    skill_id: Optional[str] = None
    skill_used: Optional[str] = None
    account_used: Optional[str] = None
    image_url: Optional[str] = None
    status: str = "success"
    dual_ai_mode: Optional[bool] = None
    rounds_count: Optional[int] = None
    discussion_history: Optional[List[Dict[str, Any]]] = Field(None, description="Lịch sử chi tiết các vòng thảo luận và phản biện giữa 2 AI")
    blocks: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách các khối nội dung JSON có cấu trúc chuyên biệt")
    tokens: Optional[Dict[str, Any]] = Field(None, description="Thống kê tokens: prompt_tokens (đã gửi), completion_tokens (đã nhận), total_tokens")
    usage: Optional[Dict[str, Any]] = Field(None, description="Thông tin usage token")
    finish_reason: Optional[str] = None
    function_calls: Optional[List[Dict[str, Any]]] = None
    protocol_version: str = PROTOCOL_VERSION
    request_id: Optional[str] = None

class ParseBlocksRequest(BaseModel):
    text: str = Field(..., description="Văn bản Markdown cần phân giải thành các khối JSON có cấu trúc")

class ManualAccountRequest(BaseModel):
    refresh_token: str = Field(..., description="Google OAuth Refresh Token hoặc Callback URL / Code")
    name: Optional[str] = Field(None, description="Tên gợi nhớ cho tài khoản")

class OAuthExchangeRequest(BaseModel):
    code_or_url: str = Field(..., description="Authorization code, full callback URL, hoặc Refresh Token")
    name: Optional[str] = Field(None, description="Tên gợi nhớ cho tài khoản")

class SettingsUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    generate_random_key: Optional[bool] = None
    default_model: Optional[str] = None
    strategy: Optional[str] = None

class GoogleOAuthSettingsUpdateRequest(BaseModel):
    client_id: str = Field(..., description="Google OAuth Client ID")
    client_secret: Optional[str] = Field(None, description="Google OAuth Client Secret; omit to keep the current secret")

class SkillCreateRequest(BaseModel):
    name: str = Field(..., description="Tên của Skill")
    system_prompt: str = Field(..., description="Chỉ dẫn hệ thống cho AI")
    user_id: Optional[str] = Field(None, description="Mã người dùng sở hữu kỹ năng này")
    icon: Optional[str] = None
    description: Optional[str] = None

class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None

class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Mô tả bức ảnh muốn tạo")
    style: Optional[str] = Field(None, description="Phong cách nghệ thuật (photorealistic, anime, cyberpunk, ...)")
    aspect_ratio: Optional[str] = Field("1:1", description="Tỉ lệ khung hình (1:1, 16:9, 9:16, 4:3, 3:4)")
    model: Optional[str] = Field("flux", description="Mô hình tạo ảnh (flux, turbo, default)")
    enhance_prompt: Optional[bool] = Field(True, description="Sử dụng Gemini để dịch và tối ưu prompt nghệ thuật")
    seed: Optional[int] = Field(None, description="Hạt giống ngẫu nhiên")

class ImageGenerateResponse(BaseModel):
    status: str = "success"
    image_url: str
    prompt: str
    enhanced_prompt: str
    width: int
    height: int
    seed: int
    model: str
    markdown: str

class UserCreateRequest(BaseModel):
    name: str = Field(..., description="Tên người dùng hoặc dự án")
    email: Optional[str] = Field(None, description="Email liên hệ")
    password: Optional[str] = Field(None, description="Mật khẩu đăng nhập tài khoản")
    note: Optional[str] = Field(None, description="Ghi chú về tài khoản")
    role: Optional[str] = Field("user", description="Vai trò tài khoản: admin | user")

class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Tên người dùng hoặc dự án")
    email: Optional[str] = Field(None, description="Email liên hệ")
    password: Optional[str] = Field(None, description="Mật khẩu đăng nhập tài khoản")
    note: Optional[str] = Field(None, description="Ghi chú về tài khoản")
    role: Optional[str] = Field(None, description="Vai trò tài khoản: admin | user")
    is_active: Optional[bool] = Field(None, description="Trạng thái kích hoạt")

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., description="Tên gợi nhớ cho API Key")
    custom_key: Optional[str] = Field(None, description="Mã Key tùy chỉnh (nếu bỏ trống hệ thống tự sinh sk-antigravity-...)")

class LoginRequest(BaseModel):
    email: str = Field(..., description="Email hoặc tên người dùng đăng nhập")
    password: str = Field(..., description="Mật khẩu đăng nhập")

class RegisterRequest(BaseModel):
    name: str = Field(..., description="Họ và tên người dùng")
    email: str = Field(..., description="Địa chỉ Email đăng ký")
    password: str = Field(..., description="Mật khẩu đăng nhập (tối thiểu 6 ký tự)")
    note: Optional[str] = Field(None, description="Ghi chú về tài khoản")

class ExportDocxRequest(BaseModel):
    content: str = Field(..., description="Nội dung Markdown cần xuất sang file Word")
    filename: Optional[str] = Field("Antigravity_Content.docx", description="Tên file Word tải về")

class ReadFolderRequest(BaseModel):
    folder_path: str = Field(..., description="Đường dẫn thư mục trên máy tính/máy chủ cần đọc")
    max_files: Optional[int] = Field(80, description="Số lượng file tối đa quét đọc")
    max_file_size_kb: Optional[int] = Field(250, description="Dung lượng tối đa mỗi file (KB)")

class ReadFolderResponse(BaseModel):
    success: bool
    folder_name: Optional[str] = None
    folder_path: Optional[str] = None
    total_files: Optional[int] = None
    tree: Optional[str] = None
    context_text: Optional[str] = None
    files: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class ReadFileRequest(BaseModel):
    file_path: str = Field(..., description="Đường dẫn file trên máy tính/máy chủ cần đọc")
    max_size_kb: Optional[int] = Field(500, description="Dung lượng tối đa mỗi file (KB)")

class ReadFileResponse(BaseModel):
    success: bool
    file_path: str
    filename: Optional[str] = None
    content: Optional[str] = None
    size: Optional[int] = None
    lang: Optional[str] = None
    error: Optional[str] = None


# =====================================================
# OpenAI-Compatible API Models (Chuẩn /v1/chat/completions)
# =====================================================

class OpenAIMessage(BaseModel):
    role: str = Field(..., description="Vai trò: system, user, assistant, developer")
    content: Any = Field(None, description="Nội dung tin nhắn (string hoặc list multimodal parts)")
    name: Optional[str] = Field(None, description="Tên người gửi (tùy chọn)")

class OpenAIChatRequest(BaseModel):
    model: str = Field(..., description="Model ID (vd: gemini-3.8-flash-tiered, claude-sonnet-4-6)")
    messages: List[Dict[str, Any]] = Field(..., description="Danh sách tin nhắn theo chuẩn OpenAI")
    temperature: Optional[float] = Field(0.7, description="Độ sáng tạo (0.0 - 2.0)")
    max_tokens: Optional[int] = Field(8192, description="Số token tối đa cho phần trả lời")
    top_p: Optional[float] = Field(None, description="Top-p sampling")
    stream: Optional[bool] = Field(False, description="Bật/tắt streaming response chuẩn Server-Sent Events (SSE)")
    stop: Optional[Any] = Field(None, description="Chuỗi hoặc danh sách stop sequences")
    n: Optional[int] = Field(1, description="Số lượng choices trả về")

class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class OpenAIChoice(BaseModel):
    index: int = 0
    message: Dict[str, Any] = Field(..., description="Tin nhắn trả lời từ AI")
    finish_reason: str = "stop"

class OpenAIChatResponse(BaseModel):
    id: str = Field(..., description="ID duy nhất của completion")
    object: str = "chat.completion"
    created: int = Field(..., description="Unix timestamp thời điểm tạo")
    model: str = Field(..., description="Model đã sử dụng")
    choices: List[OpenAIChoice] = Field(..., description="Danh sách kết quả")
    usage: OpenAIUsage = Field(default_factory=OpenAIUsage, description="Thống kê token usage")
    system_fingerprint: Optional[str] = Field(None, description="Fingerprint hệ thống")

class OpenAIModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "antigravity"

class OpenAIModelList(BaseModel):
    object: str = "list"
    data: List[OpenAIModelInfo]

# =====================================================
# MoMo Payment & Token Models
# =====================================================

class MoMoPaymentCreateRequest(BaseModel):
    package_id: Optional[str] = Field(None, description="Mã gói token (vd: pkg_starter, pkg_standard, pkg_pro, pkg_vip)")
    amount: Optional[int] = Field(None, description="Số tiền nạp tùy chỉnh (VND, tối thiểu 10,000)")
    redirect_url: Optional[str] = Field(None, description="URL chuyển hướng sau khi thanh toán trên MoMo")

class MoMoPaymentCreateResponse(BaseModel):
    status: str
    order_id: str
    amount: int
    tokens: int
    package_name: Optional[str] = None
    pay_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    deeplink: Optional[str] = None
    message: Optional[str] = None

class MoMoConfigUpdateRequest(BaseModel):
    partner_code: Optional[str] = Field(None, description="Mã đối tác MoMo Partner Code")
    access_key: Optional[str] = Field(None, description="Access Key từ MoMo Developer Portal")
    secret_key: Optional[str] = Field(None, description="Secret Key từ MoMo Developer Portal")
    ipn_url: Optional[str] = Field(None, description="Địa chỉ Webhook IPN công khai để MoMo gọi về")
    redirect_url: Optional[str] = Field(None, description="Địa chỉ URL quay lại sau khi thanh toán")
    environment: Optional[str] = Field(None, description="Môi trường MoMo: sandbox hoặc production")

