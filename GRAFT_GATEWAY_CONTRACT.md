# Graft và Antigravity Gateway

Phiên bản giao thức: `graft-gateway/1`; hai phía trao đổi `protocol_version`
và `request_id`. Nếu client yêu cầu phiên bản khác, proxy trả lỗi rõ ràng.

Graft gọi `POST /webhook/antigravity-chat` (các alias `/api/chat`, `/v1/chat`
cùng hợp đồng). Gateway xác thực Bearer key; Graft giữ công cụ và việc áp dụng
đề xuất ở máy chạy app. Gateway không được tự chạy công cụ trong project Graft.

## Yêu cầu

- `prompt`: lượt hiện tại và ngữ cảnh công việc.
- `custom_system_prompt`: hướng dẫn riêng của Graft; proxy giữ nguyên định dạng
  và không nối hướng dẫn Markdown mặc định vào đây.
- `messages`: chỉ lịch sử user/assistant, không chứa lại lượt hiện tại. Không đưa
  thông báo lỗi hoặc thẻ tiến trình của giao diện vào lịch sử trả lời của AI.
- `images`: ảnh của lượt hiện tại dạng Base64/Data URI. Ảnh lịch sử nằm trong
  `messages[].images`.
- `model`, `thinking`, `web_search`, `dual_ai_mode`, `evaluator_model`,
  `max_rounds`: các lựa chọn hiện có của app.
- `stream=true`: trả SSE. Batch JSON vẫn được Graft hỗ trợ.

## Sự kiện SSE

| Sự kiện | Nội dung | Cách Graft xử lý |
| --- | --- | --- |
| `chunk` | `text` là phần văn bản mới | Lọc khối công cụ, cập nhật luồng |
| `thought` | Phần suy luận từ model | Chỉ cập nhật trạng thái, không đưa thành câu trả lời |
| `activity` | `event_id`, `text`, `status`, `kind` | Thẻ hoạt động riêng, cập nhật cùng ID |
| `function_call` | Lời gọi hàm | Giữ lại đến khi nhận kết thúc hợp lệ |
| `done` | Snapshot `response`/`text`, model, usage, finish reason, function calls | Xác nhận hoàn tất và xử lý qua bộ công cụ cục bộ |
| `error` | `error`, `error_code`, `retryable`, request ID | Dừng luồng, giữ các hoạt động đã ghi nhận |

`done` chỉ xuất hiện khi upstream hoàn tất hợp lệ với văn bản hoặc lời gọi hàm
đầy đủ. Sau `error` không được phát `done` thành công. Kết nối kết thúc trước
`done` là `STREAM_INCOMPLETE`; nội dung từng nhận không trở thành đề xuất có thể
thực thi. Gateway có header `X-Graft-Protocol-Version` phải gửi `done`.
Graft cũng chấp nhận `[DONE]` từ stream OpenAI không có header giao thức riêng.

Native function calls được kiểm tra tên công cụ và JSON arguments, sau đó chuyển
vào cùng vòng công cụ có giới hạn như `TOOL_CALL`. Không thực thi giữa lúc streaming.
Quy tắc đọc trước khi sửa, chống ghi đè file vừa đổi và quyền áp dụng vẫn do runtime
cục bộ kiểm soát.

## Lỗi và số token

- `EMPTY_RESPONSE`: upstream kết thúc nhưng không có câu trả lời hay công cụ;
  Graft thử lại đúng một lần với cùng dữ liệu.
- `STREAM_INCOMPLETE`: thiếu kết thúc hợp lệ; chưa thực thi bản trả lời dở.
- `RESPONSE_TRUNCATED`: model hết giới hạn đầu ra; chưa thực thi bản bị cắt.
- `RESPONSE_BLOCKED`/`UPSTREAM_BLOCKED`/`UPSTREAM_ERROR`/`INVALID_RESPONSE`: giữ nguyên nguyên nhân
  từ proxy để phân biệt với phản hồi rỗng.
- `CANCELLED`: dừng yêu cầu của worker này, đóng transport, chặn retry và công cụ
  tiếp theo; không ảnh hưởng yêu cầu mới.

Proxy cung cấp `prompt_tokens`, `completion_tokens`, `total_tokens` trong
`tokens`/`usage`. Graft chuẩn hóa thêm `input_tokens`/`output_tokens` cho giao diện,
không cộng chúng vào tổng token lần thứ hai.

## Kiểm tra tích hợp

Các bài kiểm tra `test_gateway_contract.py`, `test_proxy_client_contract.py`,
`test_proxy_route_contract.py` và `test_request_cancellation.py` kiểm tra dữ liệu
gửi, stream theo byte, lỗi, kết thúc, công cụ và hủy yêu cầu. Kiểm tra proxy dùng
upstream giả để không thay đổi tài khoản, database hoặc hạn ngạch thực tế.
Đặt `GRAFT_PROXY_PROJECT` nếu proxy không nằm cạnh project Graft.

Sau khi thay source cần khởi động lại cả proxy và app để nạp code mới.
