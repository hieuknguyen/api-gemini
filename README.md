# Antigravity FastAPI Gateway

Gateway AI hiệu năng cao viết bằng FastAPI kết nối trực tiếp Google Antigravity & Cloud Code API (hỗ trợ Claude 3.7 Sonnet, Gemini 3.8 Flash, 3.0 Flash, 2.5 Flash, Imagen 3, Web Search và Quota Tracking).

---

## Deploy VPS bằng GitHub Actions

Workflow `Deploy VPS` tự chạy khi có push lên `main`. Nó đồng bộ source vào thư mục ứng dụng trên VPS, giữ nguyên `.env` và các file tài khoản/database, chỉ build/recreate `antigravity-gateway`, rồi kiểm tra `/health`. VPS cần có SSH, `rsync`, Docker Compose, network `alan` và thư mục ứng dụng đã cấu hình sẵn. Dùng IP VPS hoặc DNS chỉ dành cho SSH; hostname đi qua proxy Cloudflare thường không chuyển tiếp cổng SSH.

Chạy `bash scripts/setup-vps-cicd.sh` từ Git Bash, WSL hoặc Linux tại thư mục gốc repo. Wizard tạo GitHub Actions variables và SSH key secret, hướng dẫn cài public key và xác minh fingerprint của VPS. Sau khi workflow được commit và push, vào **Actions → Deploy VPS → Run workflow** để deploy lần đầu; các push tiếp theo lên `main` sẽ tự deploy.

Workflow không gửi `.env` hay dữ liệu runtime từ runner lên VPS, không xóa file trên VPS và không restart MySQL/Traefik.

---

## 🐳 1. Khởi động bằng Docker (Khuyên Dùng)

Ứng dụng đã được Docker hóa hoàn chỉnh, tự động mount các file dữ liệu (accounts, skills, settings, quota, .env) để không bị mất khi restart container:

### Cách 1: Click đúp file script (Windows)
- **Bật Server:** Click đúp docker-start.bat
- **Tắt Server:** Click đúp docker-stop.bat

### Cách 2: Dùng lệnh Docker Compose
`ash
# Khởi chạy ngầm & tự động build
docker compose up -d --build

# Xem log thời gian thực
docker compose logs -f

# Dừng server
docker compose down
`

- **Dashboard Web:** [http://localhost:5678/](http://localhost:5678/)
- **API Base:** http://localhost:5678/v1 & http://localhost:5678/webhook/antigravity-chat
- **Port Callback OAuth:** 51121

---

## 💻 2. Khởi động không dùng Docker (Local Python)
`ash
# Cài đặt thư viện
pip install -r requirements.txt

# Chạy server
run.bat
# Hoặc:
py -m uvicorn main:app --host 0.0.0.0 --port 5678 --reload
`

---

## 🔑 3. Xác thực Header X-API-Key
Tất cả các request gọi API đều yêu cầu header:
`http
X-API-Key: <API_KEY_CỦA_BẠN>
`
> Có thể lấy và tạo ngẫu nhiên API key mới từ Dashboard Web hoặc gọi POST /api/settings/generate-key.

---

## 💬 4. Cơ chế Stateless Conversation (Client Tự Lưu Trữ)
Máy chủ tuân thủ nguyên tắc Stateless: **Không lưu trữ nội dung chat trên server**. Client tự quản lý mảng lịch sử messages và gửi kèm trong mỗi request.

Ví dụ gọi POST /webhook/antigravity-chat:
`json
{
  "messages": [
    {"role": "user", "content": "Tôi tên là Hoàng, bác sĩ ở Huế."},
    {"role": "assistant", "content": "Chào bác sĩ Hoàng! Rất vui được gặp anh."},
    {"role": "user", "content": "Tôi làm nghề gì và ở đâu?"}
  ],
  "model": "gemini-3.8-flash-tiered",
  "thinking": false
}
`

---

## 🎨 5. Tính năng Nổi bật
1. **Typography chuẩn hóa:** Tự động đính kèm định dạng Markdown phong phú (In đậm, In nghiêng, Gạch chân <u>, Header #, Danh sách, Blockquote).
2. **Sinh ảnh tự động (Imagen 3 & Pollinations):** Hỗ trợ image_generation: true hoặc prompt yêu cầu vẽ ảnh tả thực Photorealistic 8K.
3. **Skill Custom:** Tự động gắn skill qua skill_id kèm theo request.
4. **Multi-Account Failover & Quota Tracking:** Tự động chuyển tài khoản khi cạn quota, giám sát hạn ngạch qua SQLite quota.db.
"# api-gemini" 
