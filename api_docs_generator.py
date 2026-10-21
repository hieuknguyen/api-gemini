"""
Antigravity API Documentation Generator
Tạo tài liệu đặc tả kỹ thuật chi tiết nhất dạng Markdown (.md) dành cho AI Agents và Developers.
"""

DOCS_TEMPLATE = """# TÀI LIỆU KỸ THUẬT & HƯỚNG DẪN TÍCH HỢP TOÀN DIỆN - ANTIGRAVITY API GATEWAY
> **Phiên bản tài liệu:** v2.5.0  
> **Địa chỉ máy chủ (Base URL):** `{clean_url}`  
> **Khóa API:** `{key_display}`  
> **Định dạng tối ưu:** Markdown chuẩn cho AI Agents (Claude, GPT, Cursor, Copilot, LangChain).

---

## MỤC LỤC
1. [Giới Thiệu Tổng Quan & Kiến Trúc](#1-giới-thiệu-tổng-quan--kiến-trúc)
2. [Cơ Chế Xác Thực (Authentication)](#2-cơ-chế-xác-thực-authentication)
3. [Danh Sách Các Endpoints Chính](#3-danh-sách-các-endpoints-chính)
4. [Bảng Tra Cứu Toàn Bộ Tham Số Request Body](#4-bảng-tra-cứu-toàn-bộ-tham-số-request-body)
5. [Danh Sách Các Mô Hình AI Được Hỗ Trợ (Models)](#5-danh-sách-các-mô-hình-ai-được-hỗ-trợ-models)
6. [Cơ Chế Xử Lý Đa Phương Tiện & Tài Liệu (Multimodal Files)](#6-cơ-chế-xử-lý-đa-phương-tiện--tài-liệu-multimodal-files)
7. [Kiến Trúc Hội Thoại Đa Lượt Phi Trạng Thái (Stateless Multi-turn)](#7-kiến-trúc-hội-thoại-đa-lượt-phi-trạng-thái-stateless-multi-turn)
8. [Hệ Thống Kỹ Năng Tùy Biến (Skills & Personas)](#8-hệ-thống-kỹ-năng-tùy-biến-skills--personas)
9. [Endpoint Sinh Ảnh Nghệ Thuật AI (Flux.1)](#9-endpoint-sinh-ảnh-nghệ-thuật-ai-flux1)
10. [Cấu Trúc Kết Quả Trả Về & Xử Lý Lỗi (Response & Error Handling)](#10-cấu-trúc-kết-quả-trả-về--xử-lý-lỗi-response--error-handling)
11. [Bộ Code Mẫu Thực Chiến (Executable Code Examples)](#11-bộ-code-mẫu-thực-chiến-executable-code-examples)
    - 11.1. [Python: Trò chuyện cơ bản & Tắt Thinking](#111-python-trò-chuyện-cơ-bản--tắt-thinking)
    - 11.2. [Python: Tra cứu thông tin thời gian thực (Google Search Grounding)](#112-python-tra-cứu-thông-tin-thời-gian-thực-google-search-grounding)
    - 11.3. [Python: Nhận diện & Phân tích hình ảnh (Multimodal Vision)](#113-python-nhận-diện--phân-tích-hình-ảnh-multimodal-vision)
    - 11.4. [Python: Phân tích tài liệu PDF, Word, Excel, Âm thanh, Video](#114-python-phân-tích-tài-liệu-pdf-word-excel-âm-thanh-video)
    - 11.5. [Python: Quản lý ngữ cảnh hội thoại đa lượt (Stateless Memory)](#115-python-quản-lý-ngữ-cảnh-hội-thoại-đa-lượt-stateless-memory)
    - 11.6. [Python: Sinh ảnh nghệ thuật AI Flux.1](#116-python-sinh-ảnh-nghệ-thuật-ai-flux1)
    - 11.7. [cURL: Toàn bộ lệnh mẫu Terminal](#117-curl-toàn-bộ-lệnh-mẫu-terminal)
    - 11.8. [JavaScript / Node.js: Fetch & Axios](#118-javascript--nodejs-fetch--axios)
12. [Chỉ Dẫn Dành Riêng Cho AI Agents (AI System Prompt Directive)](#12-chỉ-dẫn-dành-riêng-cho-ai-agents-ai-system-prompt-directive)

---

## 1. GIỚI THIỆU TỔNG QUAN & KIẾN TRÚC
Antigravity API Gateway là giải pháp máy chủ API hiệu năng cao xây dựng trên nền tảng FastAPI, kết nối trực tiếp đến cụm tài khoản Google Antigravity (Google Cloud Vertex & DeepMind Gemini / Anthropic Claude).

### Điểm nổi bật:
- **Tự động luân chuyển & Chống Rate Limit (Auto-Failover / Round-Robin):** Tự động phát hiện lỗi 429 và đổi sang tài khoản dự phòng trong tích tắc, đảm bảo ứng dụng không bao giờ bị gián đoạn.
- **Kiến trúc Phi trạng thái (Stateless Architecture):** Máy chủ không lưu trữ bất kỳ tin nhắn riêng tư nào của người dùng. Client tự lưu trữ lịch sử và gửi kèm trong mỗi request.
- **Hỗ trợ Đa phương tiện Toàn diện (True Multimodal):** Đọc trực tiếp Ảnh, PDF, Audio, Video qua Google `inlineData`, đồng thời tự động bóc tách nội dung Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV để AI phân tích chuyên sâu.
- **Tìm kiếm Google Thời gian thực (Google Search Grounding):** Trực tiếp tích hợp Google Search, cung cấp thông tin thời tiết, tin tức, tỷ giá mới nhất kèm danh sách nguồn trích dẫn.
- **Kỹ năng Viết content riêng tư:** Chỉ tài khoản sở hữu mới được liệt kê, cập nhật hoặc sử dụng kỹ năng qua `skill_id`.

---

## 2. CƠ CHẾ XÁC THỰC (AUTHENTICATION)
Mọi yêu cầu gửi đến các endpoint nghiệp vụ phải kèm theo khóa API hợp lệ.

### Cách truyền Header:
Bạn có thể dùng một trong hai cách tương đương:
```http
X-API-Key: {key_display}
```
Hoặc:
```http
Authorization: Bearer {key_display}
```

> **Header bổ sung tùy chọn:**
> - `Content-Type: application/json` (Bắt buộc cho mọi request chứa body JSON)
> - `X-User-Id: usr_xxxxxxxx` (Tùy chọn: Định danh ID người dùng để chọn đúng môi trường)

---

## 3. DANH SÁCH CÁC ENDPOINTS CHÍNH

| Method | Endpoint | Mô Tả Chức Năng | Quyền Truy Cập |
|:---:|:---|:---|:---:|
| `POST` | `/v1/chat/completions` | **Chuẩn OpenAI:** Tương thích trực tiếp với OpenAI SDK, Codex, Cursor, Continue.dev, Cline | User / Admin |
| `GET` | `/v1/models` | **Chuẩn OpenAI:** Liệt kê toàn bộ danh sách model khả dụng | Công khai |
| `POST` | `/webhook/antigravity-chat` | **Endpoint Antigravity gốc:** Nhận diện ảnh, tài liệu, chat, kỹ năng, web search | User / Admin |
| `POST` | `/v1/chat` | Endpoint Antigravity tương thích chuẩn REST API | User / Admin |
| `POST` | `/api/image/generate` | Endpoint chuyên dụng sinh ảnh nghệ thuật AI Flux.1 | User / Admin |
| `POST` | `/api/image/enhance-prompt` | Tối ưu hóa prompt ảnh với Gemini | User / Admin |
| `GET` | `/api/skills` | Lấy danh sách kỹ năng của người dùng | Đã đăng nhập |
| `PUT` | `/api/skills/{skill_id}` | Cập nhật prompt Viết content của chủ sở hữu | Chủ sở hữu |
| `POST` | `/api/auth/register` | Đăng ký tài khoản thường mới (nhận API Key riêng) | Công khai |
| `POST` | `/api/auth/login` | Đăng nhập tài khoản bằng email & mật khẩu | Công khai |
| `GET` | `/api/docs/markdown` | Tải về file tài liệu Markdown chi tiết này | Công khai |
| `POST` | `/api/export/docx` | Xuất bài viết Markdown sang file Word (.docx) chuẩn đẹp | Công khai |

---

## 4. BẢNG TRA CỨU TOÀN BỘ THAM SỐ REQUEST BODY
Áp dụng cho cả hai endpoint: `POST /webhook/antigravity-chat` và `POST /v1/chat`.

| Tham Số | Kiểu Dữ Liệu | Bắt Buộc? | Mặc Định | Mô Tả & Chi Tiết Kỹ Thuật |
|:---|:---:|:---:|:---:|:---|
| `prompt` | `string` | Không* | `null` | Câu lệnh hoặc nội dung trao đổi của người dùng. (*Bắt buộc nếu không có mảng `messages`). |
| `model` | `string` | Không | `gemini-3.8-flash-tiered` | Mã mô hình AI xử lý (Xem mục 5). |
| `files` | `array[object]` | Không | `null` | Mảng chứa tài liệu: PDF, Word, Excel, PPTX, MP3, MP4, Text, Code... Mỗi object gồm `{"data": "base64/data_uri", "filename": "ten_file"}`. |
| `image` | `string` | Không | `null` | Chuỗi Base64 hoặc Data URI của 1 ảnh (`"data:image/png;base64,..."`). |
| `images` | `array[string]` | Không | `null` | Mảng chứa nhiều chuỗi Base64 khi gửi cùng lúc nhiều ảnh. |
| `messages` | `array[object]` | Không | `null` | Lịch sử hội thoại đầy đủ dạng `[{"role": "user"|"assistant", "content": "..."}]`. |
| `skill_id` | `string` | Không | `null` | Chỉ dùng ID kỹ năng Viết content riêng tư của tài khoản sở hữu; tài khoản khác không thể xem hoặc dùng ID đó. |
| `custom_system_prompt`| `string` | Không | `null` | Chỉ dẫn hệ thống trực tiếp cho lượt gọi này (kết hợp với skill). |
| `thinking` | `boolean` | Không | `false` | `false` = phản hồi tốc độ tối đa; `true` = kích hoạt chuỗi suy luận sâu từng bước. |
| `web_search` | `boolean` | Không | `true` | `true` = Tự động tìm kiếm Google thời gian thực khi cần thông tin mới; `false` = Tắt tra cứu mạng. |
| `temperature` | `float` | Không | `0.7` | Độ ngẫu nhiên (từ `0.0` phân tích logic chính xác đến `2.0` sáng tạo bay bổng). |
| `max_tokens` | `integer` | Không | `4096` | Giới hạn số token tối đa của câu trả lời (1024 - 65536). |
| `session_id` | `string` | Không | `null` | Mã định danh phiên làm việc phía client để đối soát log. |

---

## 5. DANH SÁCH CÁC MÔ HÌNH AI ĐƯỢC HỖ TRỢ (MODELS)

### 1. Nhóm Google Gemini:
- **`gemini-4-argon`:**
  - Model suy luận nâng cao cho kỹ thuật phần mềm, toán học và tác vụ nhiều bước. Đầu ra văn bản; không hỗ trợ tạo audio.
- **`gemini-3.8-flash-tiered` (Mặc định - Khuyến nghị):**
  - Tốc độ phản hồi cực nhanh, độ thông minh cao, hỗ trợ đa phương tiện (Ảnh, Tài liệu, Audio, Video), tự động tra cứu Google Search thời gian thực. Phù hợp cho 95% tác vụ hàng ngày và hệ thống tự động hóa.
- **`gemini-3.1-pro-high`:**
  - Mô hình tư duy suy luận mạnh mẽ nhất của Google. Tối ưu xuất sắc cho giải toán, phân tích kiến trúc phần mềm, lập trình phức tạp, viết code hàng nghìn dòng.
- **`gemini-2.5-flash`:**
  - Mô hình tối ưu chi phí và quota, ổn định cho các tác vụ phân loại dữ liệu, trích xuất thông tin ngắn.

### 2. Nhóm Anthropic Claude:
- **`claude-sonnet-4-6`:**
  - Văn phong tiếng Việt mượt mà, sâu sắc, trình bày văn bản chuyên nghiệp, biên dịch xuất sắc.
- **`claude-opus-4-6-thinking`:**
  - Tích hợp công nghệ tư duy Interleaved Thinking của Anthropic, phân tích đa chiều các bài toán hóc búa.

### 3. Nhóm Tạo Ảnh Nghệ Thuật:
- **`flux-image-generator`:**
  - Tự động chuyển tiếp prompt sang công cụ sinh ảnh nghệ thuật Flux.1, trả về đường dẫn ảnh chất lượng cao.

---

## 6. CƠ CHẾ XỬ LÝ ĐA PHƯƠNG TIỆN & TÀI LIỆU (MULTIMODAL FILES)

Hệ thống hỗ trợ nạp tài liệu thông qua trường `files` trong JSON payload:
```json
{
  "prompt": "Tóm tắt bảng lương và chỉ ra các nhân sự có doanh số cao nhất",
  "files": [
    {
      "data": "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,UEsDBBQABg...",
      "filename": "bang_luong_thang_9.xlsx"
    }
  ]
}
```

### Cơ chế hoạt động thông minh:
1. **Các định dạng AI hiểu trực tiếp (Native AI):**
   - **Ảnh:** PNG, JPEG, WEBP, GIF, HEIC...
   - **Tài liệu chuẩn:** PDF.
   - **Âm thanh:** MP3, WAV, AAC, OGG.
   - **Video:** MP4, MOV, WEBM.
   - -> *Hệ thống gửi nguyên bản dữ liệu nhị phân lên Google Antigravity qua giao thức `inlineData`.*
2. **Các định dạng văn phòng & dữ liệu (Office & Text):**
   - **Word:** `.docx`, `.doc`.
   - **Excel:** `.xlsx`, `.xls` (tự động xuất bảng biểu dạng Markdown Table hoặc CSV).
   - **PowerPoint:** `.pptx`.
   - **Dữ liệu & Code:** `.csv`, `.json`, `.txt`, `.py`, `.js`, `.html`...
   - -> *Backend tự động trích xuất toàn bộ văn bản và cấu trúc bảng đưa vào System Context của AI.*

---

## 7. KIẾN TRÚC HỘI THOẠI ĐA LƯỢT PHI TRẠNG THÁI (STATELESS MULTI-TURN)

Nhằm bảo mật quyền riêng tư tuyệt đối, Gateway **không lưu giữ nội dung tin nhắn** trên cơ sở dữ liệu máy chủ. Thay vào đó, Client hoặc ứng dụng ngoài tự lưu trữ lịch sử hội thoại trong file hoặc bộ nhớ tạm, và gửi kèm mảng `messages` trong mỗi lần gọi.

### Cấu trúc mảng `messages`:
```json
[
  {"role": "user", "content": "Tôi tên là Nguyễn Trung Hiếu, sinh năm 1990."},
  {"role": "assistant", "content": "Chào anh Hiếu! Em đã ghi nhớ thông tin của anh."},
  {"role": "user", "content": "Năm nay tôi bao nhiêu tuổi?"}
]
```
AI sẽ đọc toàn bộ mảng này và trả lời chính xác dựa trên ngữ cảnh đã trò chuyện trước đó!

---

## 8. HỆ THỐNG KỸ NĂNG TÙY BIẾN (SKILLS & PERSONAS)

Tài khoản sở hữu gửi kèm `"skill_id": "MÃ_SKILL_RIÊNG_TƯ"` để áp dụng kỹ năng Viết content.

Mỗi project chỉ có một kỹ năng **Viết content**, gắn với một tài khoản sở hữu. Chỉ tài khoản đó nhìn thấy và áp dụng được kỹ năng; project không cho phép tạo, import hoặc xóa thêm kỹ năng.

---

## 9. ENDPOINT SINH ẢNH NGHỆ THUẬT AI (FLUX.1)
Endpoint: `POST {clean_url}/api/image/generate`

### Body Parameters:
```json
{
  "prompt": "Một phi hành gia đứng giữa cánh đồng hoa oải hương tím biếc trên sao Hỏa, bầu trời rực rỡ dải ngân hà",
  "style": "photorealistic",
  "aspect_ratio": "16:9",
  "enhance_prompt": true
}
```

- `style`: `"none"`, `"photorealistic"`, `"anime"`, `"cyberpunk"`, `"digital-art"`, `"oil-painting"`, `"3d-render"`.
- `aspect_ratio`: `"1:1"` (vuông), `"16:9"` (ngang rộng), `"9:16"` (dọc story/tiktok), `"4:3"`, `"3:4"`.
- `enhance_prompt`: `true` để nhờ Gemini tối ưu hóa câu lệnh sang tiếng Anh chuẩn nghệ thuật.

---

## 10. CẤU TRÚC KẾT QUẢ TRẢ VỀ & XỬ LÝ LỖI (RESPONSE & ERROR HANDLING)

### Phản hồi thành công (HTTP 200 OK):
```json
{
  "status": "success",
  "response": "Nội dung phản hồi hoàn chỉnh của mô hình AI theo định dạng Markdown phong phú...",
  "text": "Nội dung văn bản (đồng bộ với response)",
  "model": "gemini-3.8-flash-tiered",
  "skill_used": "Trợ lý Toàn năng Antigravity",
  "account_used": "nguyentrunghieu4390@gmail.com",
  "session_id": "sess_f82bc194"
}
```

### Bảng mã lỗi thường gặp:
| Mã Lỗi HTTP | Nguyên Nhân | Cách Xử Lý |
|:---:|:---|:---|
| `401 Unauthorized` | Thiếu hoặc sai khóa API Key | Kiểm tra header `X-API-Key` hoặc đăng nhập lấy key mới |
| `403 Forbidden` | Tài khoản thường cố truy cập chức năng Admin | Chỉ Admin tối cao mới có quyền cấu hình pool Google Accounts |
| `400 Bad Request` | Thiếu prompt và thiếu messages, hoặc file base64 sai cú pháp | Kiểm tra lại cấu trúc body JSON gửi lên |
| `404 Not Found` | Sai endpoint URL | Đảm bảo gọi đúng `{clean_url}/webhook/antigravity-chat` |
| `429 Rate Limit` | Quota tài khoản tạm thời chạm ngưỡng | Hệ thống tự động chuyển tiếp failover sang tài khoản dự phòng |
| `500 Server Error` | Lỗi dịch vụ ngoại vi hoặc file hỏng | Kiểm tra log máy chủ qua `docker logs antigravity-gateway` |

---

## 11. BỘ CODE MẪU THỰC CHIẾN (EXECUTABLE CODE EXAMPLES)

### 11.1. Python: Trò chuyện cơ bản & Tắt Thinking
```python
import requests

url = "{clean_url}/webhook/antigravity-chat"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "{key_display}"
}

payload = {
    "prompt": "Giải thích ngắn gọn nguyên lý hoạt động của Docker Container trong 3 gạch đầu dòng.",
    "model": "gemini-3.8-flash-tiered",
    "thinking": False  # Tắt suy luận để phản hồi tức thì
}

response = requests.post(url, json=payload, headers=headers)
data = response.json()
print("AI:", data.get("response"))
```

### 11.2. Python: Tra cứu thông tin thời gian thực (Google Search Grounding)
```python
import requests

url = "{clean_url}/webhook/antigravity-chat"
headers = {"X-API-Key": "{key_display}"}

payload = {
    "prompt": "Giá vàng SJC và tỷ giá USD/VND hôm nay tại Việt Nam là bao nhiêu?",
    "model": "gemini-3.8-flash-tiered",
    "web_search": True  # Tự động kích hoạt Google Search
}

res = requests.post(url, json=payload, headers=headers).json()
print("Kết quả cập nhật thời gian thực:\n", res.get("response"))
```

### 11.3. Python: Nhận diện & Phân tích hình ảnh (Multimodal Vision)
```python
import requests
import base64

url = "{clean_url}/webhook/antigravity-chat"
headers = {"X-API-Key": "{key_display}"}

# Đọc file ảnh và chuyển sang chuỗi Base64
with open("hoa_don.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "prompt": "Hãy đọc hóa đơn này, trích xuất: Ngày mua, Tên cửa hàng, Danh sách món ăn và Tổng tiền thanh toán.",
    "image": f"data:image/jpeg;base64,{img_b64}",
    "model": "gemini-3.8-flash-tiered",
    "thinking": False
}

res = requests.post(url, json=payload, headers=headers).json()
print("Thông tin hóa đơn:\n", res.get("response"))
```

### 11.4. Python: Phân tích tài liệu PDF, Word, Excel, Âm thanh, Video
```python
import requests
import base64

url = "{clean_url}/webhook/antigravity-chat"
headers = {"X-API-Key": "{key_display}"}

def file_to_base64_uri(file_path: str, mime_type: str) -> str:
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"

payload = {
    "prompt": "Phân tích tài liệu này, chỉ ra các điểm rủi ro pháp lý chính và đề xuất hướng điều chỉnh.",
    "files": [
        {
            "filename": "hop_dong_dich_vu.pdf",
            "data": file_to_base64_uri("hop_dong_dich_vu.pdf", "application/pdf")
        }
    ],
    "model": "gemini-3.1-pro-high"  # Dùng Gemini 3.1 Pro cho phân tích tài liệu phức tạp
}

res = requests.post(url, json=payload, headers=headers).json()
print("Kết quả thẩm định hợp đồng:\n", res.get("response"))
```

### 11.5. Python: Quản lý ngữ cảnh hội thoại đa lượt (Stateless Memory)
```python
import os
import json
import requests

URL = "{clean_url}/webhook/antigravity-chat"
HEADERS = {"X-API-Key": "{key_display}"}
HISTORY_FILE = "chat_memory.json"

def get_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(messages):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def ask_ai(question: str):
    messages = get_history()
    messages.append({"role": "user", "content": question})

    payload = {
        "messages": messages,
        "model": "gemini-3.8-flash-tiered",
        "web_search": True
    }

    res = requests.post(URL, json=payload, headers=HEADERS).json()
    reply = res.get("response", "")
    print(f"\nNgười dùng: {question}")
    print(f"AI: {reply}")

    messages.append({"role": "assistant", "content": reply})
    save_history(messages)

# Kiểm tra tính năng nhớ ngữ cảnh:
ask_ai("Chào bạn, công ty của tôi tên là TechVina, chuyên gia công phần mềm.")
ask_ai("Hãy gợi ý cho công ty tôi 3 chiến lược marketing phù hợp nhất.")
```

### 11.6. Python: Sinh ảnh nghệ thuật AI Flux.1
```python
import requests

url = "{clean_url}/api/image/generate"
headers = {"X-API-Key": "{key_display}"}

payload = {
    "prompt": "Một góc phố cổ Hội An về đêm rực rỡ đèn lồng dưới mưa, phong cách màu nước nghệ thuật",
    "style": "photorealistic",
    "aspect_ratio": "16:9",
    "enhance_prompt": True
}

res = requests.post(url, json=payload, headers=headers).json()
print("Trạng thái:", res.get("status"))
print("Đường dẫn ảnh AI:", res.get("image_url"))
```

### 11.7. cURL: Toàn bộ lệnh mẫu Terminal

#### Chat cơ bản:
```bash
curl -X POST "{clean_url}/webhook/antigravity-chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {key_display}" \
  -d '{
    "prompt": "Viết 1 bài thơ ngắn 4 câu về mùa thu Hà Nội",
    "model": "gemini-3.8-flash-tiered",
    "thinking": false
  }'
```

#### Gọi áp dụng Kỹ Năng (Skill):
```bash
curl -X POST "{clean_url}/webhook/antigravity-chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: {key_display}" \
  -d '{
    "prompt": "Tối ưu hóa đoạn mã SQL sau để tăng tốc độ truy vấn: SELECT * FROM orders WHERE status = 1",
    "skill_id": "YOUR_PRIVATE_SKILL_ID"
  }'
```

### 11.8. JavaScript / Node.js: Fetch & Axios
```javascript
const axios = require('axios');

async function chatWithAntigravity() {
  const url = '{clean_url}/webhook/antigravity-chat';
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': '{key_display}'
  };

  const payload = {
    prompt: 'Viết một hàm JavaScript kiểm tra số nguyên tố tối ưu nhất.',
    model: 'gemini-3.8-flash-tiered',
    thinking: false
  };

  try {
    const res = await axios.post(url, payload, { headers });
    console.log('AI Response:', res.data.response);
  } catch (err) {
    console.error('Lỗi gọi API:', err.response ? err.response.data : err.message);
  }
}

chatWithAntigravity();
```

---

## 12. CHỈ DẪN DÀNH RIÊNG CHO AI AGENTS (AI SYSTEM PROMPT DIRECTIVE)

Khi một AI Agent (Cursor, Copilot, AutoGPT) đọc tài liệu này để tự động sinh mã hoặc tạo luồng tự động:

1. **Luôn ưu tiên mô hình `gemini-3.8-flash-tiered`**: Đây là mô hình mặc định mang lại tỉ lệ thành công cao nhất, tốc độ phản hồi dưới 1 giây và hỗ trợ đa phương tiện hoàn hảo.
2. **Luôn đặt `"thinking": false`** trừ khi người dùng yêu cầu rõ ràng về việc phân tích từng bước suy luận chuyên sâu.
3. **Luôn đặt Header `X-API-Key`**: Không bao giờ bỏ quên header này trong bất kỳ mã nguồn mẫu nào sinh ra.
4. **Xử lý tài liệu và ảnh:** Hãy mã hóa sang chuỗi Data URI Base64 dạng `data:<mime_type>;base64,<content>` trước khi đưa vào mảng `files` hoặc trường `image`.
5. **Định dạng câu trả lời:** Máy chủ luôn trả về Markdown chuẩn GFM, hãy render trực tiếp trường `response` ra giao diện người dùng.

---
*Tài liệu được sinh tự động bởi Antigravity API Gateway - Bản quyền thuộc về Quản trị viên Nguyễn Trung Hiếu.*
"""

def generate_markdown_docs(base_url: str = "http://localhost:5678", api_key: str = "sk-antigravity-...") -> str:
    clean_url = (base_url or "http://localhost:5678").rstrip("/")
    key_display = api_key or "sk-antigravity-..."
    return DOCS_TEMPLATE.replace("{clean_url}", clean_url).replace("{key_display}", key_display)
