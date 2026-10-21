import re
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
import config
from client import antigravity_client
from response_parser import parse_response_to_blocks

logger = logging.getLogger("dual-ai-orchestrator")

EVALUATOR_SYSTEM_PROMPT = """Bạn là AI Giám Khảo & Phản Biện Chất Lượng Tối Cao (Quality Assurance & Expert Critic AI).
Nhiệm vụ của bạn là kiểm tra, đánh giá khắt khe và phản biện bản nháp do AI Thực Thi tạo ra dựa trên yêu cầu của người dùng và các quy định của Kỹ năng (Skill).

TIÊU CHÍ ĐÁNH GIÁ NGHIÊM NGẶT & CHECKLIST BẮT BUỘC:
1. ĐỘ DÀI & TÍNH TOÀN VẸN (QUAN TRỌNG HÀNG ĐẦU):
   - Nếu Kỹ năng hoặc Yêu cầu quy định độ dài (ví dụ: bài 1000 từ trở lên), bài viết PHẢI đạt đủ số từ theo quy định. Nếu bài viết ngắn dưới 1000 từ hoặc nội dung mỏng -> BẮT BUỘC ghi VERDICT: [NEEDS_REVISION].
   - Kiểm tra câu cuối cùng của bài viết: Tuyệt đối không được đứt cụt lửng lơ giữa câu hoặc dừng đột ngột. Bài viết PHẢI hoàn thành trọn vẹn đến hết mục Lời Kết. Nếu bị đứt câu hoặc thiếu Lời Kết -> BẮT BUỘC ghi VERDICT: [NEEDS_REVISION].
2. SỐ LƯỢNG & ĐỊNH DẠNG HÌNH ẢNH:
   - Nếu Kỹ năng quy định số lượng ảnh (ví dụ: 1 ảnh đại diện + 3 ảnh nội dung = 4 ảnh), bản nháp PHẢI có đủ chính xác số vị trí ảnh kèm kích thước (800x400), dung lượng (<100kb), và chú thích in nghiêng căn giữa có chứa từ khóa. Nếu thiếu bất kỳ ảnh nào -> BẮT BUỘC ghi VERDICT: [NEEDS_REVISION].
3. BẢNG BIỂU DỮ LIỆU (MARKDOWN TABLE):
   - Nếu Kỹ năng yêu cầu bảng biểu thống kê/so sánh, bài viết PHẢI có ít nhất 1 bảng Markdown Table (| Cột 1 | Cột 2 |) chỉn chu, ít nhất 3-4 dòng dữ liệu. Nếu thiếu bảng -> BẮT BUỘC ghi VERDICT: [NEEDS_REVISION].
4. CẤU TRÚC MỞ BÀI, THẺ HEADING & LỜI KẾT:
   - Phải có Meta Description (150-160 ký tự) chuẩn mực ở đầu.
   - Mở bài (Sapo) và Kết bài: Mỗi phần phải đủ 4-5 dòng, in đậm key chính + tên brand. Kết bài phải có lời kêu gọi hành động (CTA).
   - Các thẻ Heading H1, H2, H3 phân bổ mạch lạc, có câu dẫn dắt tự nhiên giữa các thẻ.
5. KHÔNG CHẤP NHẬN TÓM TẮT DỞ DANG:
   - Triển khai đầy đủ chi tiết mọi phân mục (vũ khí, sảnh chơi, mẹo săn boss, FAQ, kết bài). Tuyệt đối không được viết tắt, bỏ qua mục nào.

QUY TẮC ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC TUÂN THỦ CHÍNH XÁC):
Ở dòng đầu tiên của phản hồi, bạn BẮT BUỘC phải ghi:
VERDICT: [PASSED]
(CHỈ KHI bản nháp đã thực sự xuất sắc, đầy đủ 100% dữ liệu, thỏa mãn toàn bộ checklist trên và không thiếu bất kỳ chi tiết nào)
HOẶC
VERDICT: [NEEDS_REVISION]
(Nếu bản nháp vi phạm bất kỳ tiêu chí nào trong checklist: thiếu từ, đứt câu, thiếu ảnh, thiếu bảng biểu, thiếu FAQ hoặc thiếu Lời Kết)

Tiếp theo, hãy trình bày ngắn gọn và sắc bén:
SCORE: [Điểm số từ 1 đến 10]/10
CRITIQUE:
- Điểm đã làm tốt: ...
- Điểm còn thiếu sót hoặc vi phạm checklist: ...
IMPROVEMENT_GUIDE:
- Chỉ dẫn cụ thể từng điểm AI Thực Thi cần viết tiếp, bổ sung hoặc sửa đổi để đạt chuẩn: ...
"""

def parse_evaluator_verdict(feedback: str) -> Tuple[bool, Optional[str]]:
    """Phân tích quyết định của AI Đánh Giá (PASSED hay NEEDS_REVISION)"""
    if not feedback:
        return False, None
    verdict_match = re.search(r"VERDICT:\s*\[(PASSED|NEEDS_REVISION)\]", feedback, re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).upper()
        return verdict == "PASSED", verdict
    # Fallback kiểm tra từ khóa
    if "[PASSED]" in feedback.upper() or "VERDICT: PASSED" in feedback.upper():
        return True, "PASSED"
    if "[NEEDS_REVISION]" in feedback.upper() or "VERDICT: NEEDS_REVISION" in feedback.upper():
        return False, "NEEDS_REVISION"
    # Mặc định cần cải thiện nếu chưa rõ ràng
    return False, "NEEDS_REVISION"

def extract_score(feedback: str) -> Optional[str]:
    match = re.search(r"SCORE:\s*(\d+(\.\d+)?\s*/\s*10)", feedback, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def execute_dual_ai_discussion(
    prompt: str,
    worker_model: Optional[str] = None,
    evaluator_model: Optional[str] = None,
    skill_prompt: Optional[str] = None,
    skill_name: Optional[str] = None,
    max_rounds: int = 3,
    image: Optional[str] = None,
    images: Optional[List[str]] = None,
    web_search: bool = True,
    thinking: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    contents: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """
    Thực thi vòng lặp thảo luận & phản biện giữa 2 AI:
    - AI 1 (Worker): Tạo và sửa bản nháp theo yêu cầu và Skill.
    - AI 2 (Critic/Evaluator): Đánh giá, chấm điểm và chỉ ra điểm cần sửa.
    
    Returns:
        (final_response, account_used, discussion_history, blocks, total_est_tokens)
    """
    selected_worker_model = worker_model or config.DEFAULT_MODEL
    if not evaluator_model or evaluator_model in ("gemini-3.1-pro-high", "gemini-3.1-pro", "gemini-2.5-pro", "gpt-oss-120b"):
        selected_evaluator_model = "claude-sonnet-4-6"
    else:
        selected_evaluator_model = evaluator_model
    max_rounds = max(1, min(5, max_rounds or 3))

    logger.info(f"Bắt đầu quy trình Thảo Luận 2 AI (Max {max_rounds} vòng) | Worker: {selected_worker_model} | Evaluator: {selected_evaluator_model}")

    discussion_history: List[Dict[str, Any]] = []
    total_est_tokens = 0
    account_used = "Antigravity Multi-Agent"

    current_draft = ""
    total_prompt_tokens = 0
    total_completion_tokens = 0
    last_feedback = ""
    is_passed = False

    for round_num in range(1, max_rounds + 1):
        logger.info(f"--- THẢO LUẬN 2 AI: VÒNG {round_num}/{max_rounds} ---")

        if round_num > 1:
            time.sleep(1.5)  # Nghỉ 1.5s giữa các vòng để hạ nhiệt rate limit

        # 1. AI 1 (Worker / Executor) Thực hiện công việc
        if round_num == 1:
            worker_prompt = prompt
            worker_sys_prompt = skill_prompt
        else:
            worker_prompt = (
                f"YÊU CẦU GỐC CỦA NGƯỜI DÙNG:\n{prompt}\n\n"
                f"---\n"
                f"BẢN DỰ THẢO TRƯỚC ĐÓ CỦA BẠN (VÒNG {round_num - 1}):\n{current_draft}\n\n"
                f"---\n"
                f"NHẬN XÉT & CHỈ DẪN KHẮC PHỤC TỪ AI ĐÁNH GIÁ (GIÁM KHẢO):\n{last_feedback}\n\n"
                f"---\n"
                f"NHIỆM VỤ CỦA BẠN: Hãy tiếp thu nghiêm túc mọi góp ý của AI Đánh Giá ở trên, khắc phục triệt để các điểm thiếu sót, "
                f"và viết lại phiên bản hoàn chỉnh, chất lượng cao nhất, tuân thủ đúng yêu cầu kỹ năng ({skill_name or 'Mặc định'})."
            )
            worker_sys_prompt = skill_prompt

        draft_reply, draft_acc, _, worker_usage = antigravity_client.generate(
            prompt=worker_prompt,
            image=image if round_num == 1 else None,
            images=images if round_num == 1 else None,
            model=selected_worker_model,
            thinking=thinking,
            web_search=web_search if round_num == 1 else False,
            system_prompt=worker_sys_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            contents=contents if round_num == 1 else None,
            return_blocks=True,
            return_usage=True
        )
        current_draft = draft_reply.strip()
        account_used = draft_acc

        w_p = worker_usage.get("prompt_tokens") or worker_usage.get("prompt") or 0
        w_c = worker_usage.get("completion_tokens") or worker_usage.get("completion") or 0
        w_t = worker_usage.get("total_tokens") or worker_usage.get("total") or 0
        if w_p == 0 and w_t > w_c:
            w_p = w_t - w_c
        if w_p == 0:
            w_p = max(1, len(worker_prompt) // 4)
        if w_c == 0:
            w_c = max(1, len(current_draft) // 4)

        total_prompt_tokens += w_p
        total_completion_tokens += w_c
        total_est_tokens += w_p + w_c

        # 2. AI 2 (Critic / Evaluator) Đánh giá và phản biện bản nháp
        time.sleep(1.5)  # Tránh Google API burst rate limit giữa AI 1 và AI 2
        evaluator_user_content = (
            f"YÊU CẦU GỐC TỪ NGƯỜI DÙNG:\n{prompt}\n\n"
            f"---\n"
            f"QUY ĐỊNH KỸ NĂNG (SKILL - {skill_name or 'Mặc định'}):\n{skill_prompt or 'Không có chỉ thị đặc biệt, áp dụng chuẩn chất lượng cao nhất.'}\n\n"
            f"---\n"
            f"BẢN DỰ THẢO CỦA AI THỰC THI (VÒNG {round_num}):\n{current_draft}\n\n"
            f"---\n"
            f"Hãy đối chiếu khắt khe bản dự thảo trên với Yêu Cầu và Kỹ Năng. Đưa ra VERDICT: [PASSED] hoặc VERDICT: [NEEDS_REVISION] kèm nhận xét chi tiết."
        )

        eval_reply, eval_acc, _, eval_usage = antigravity_client.generate(
            prompt=evaluator_user_content,
            model=selected_evaluator_model,
            thinking=True,  # Bật thinking cho evaluator để suy luận sâu
            web_search=False,
            system_prompt=EVALUATOR_SYSTEM_PROMPT,
            temperature=0.2,  # Thấp để đánh giá khách quan, nhất quán
            max_tokens=2048,
            return_blocks=True,
            return_usage=True
        )
        last_feedback = eval_reply.strip()

        e_p = eval_usage.get("prompt_tokens") or eval_usage.get("prompt") or 0
        e_c = eval_usage.get("completion_tokens") or eval_usage.get("completion") or 0
        e_t = eval_usage.get("total_tokens") or eval_usage.get("total") or 0
        if e_p == 0 and e_t > e_c:
            e_p = e_t - e_c
        if e_p == 0:
            e_p = max(1, len(evaluator_user_content) // 4)
        if e_c == 0:
            e_c = max(1, len(last_feedback) // 4)

        total_prompt_tokens += e_p
        total_completion_tokens += e_c
        total_est_tokens += e_p + e_c

        is_passed, verdict_str = parse_evaluator_verdict(last_feedback)
        score_str = extract_score(last_feedback) or ("10/10" if is_passed else "7/10")

        # Ghi nhận vào lịch sử thảo luận
        round_record = {
            "round": round_num,
            "worker_model": selected_worker_model,
            "worker_draft": current_draft,
            "evaluator_model": selected_evaluator_model,
            "evaluator_feedback": last_feedback,
            "verdict": "PASSED" if is_passed else "NEEDS_REVISION",
            "score": score_str
        }
        discussion_history.append(round_record)
        logger.info(f"Kết quả Vòng {round_num}: Verdict={round_record['verdict']} | Score={score_str}")

        if is_passed:
            logger.info(f"AI Đánh Giá đã chấp thuận (PASSED) ở vòng {round_num}! Kết thúc sớm vòng lặp.")
            break

    # 3. Tổng hợp kết quả và dựng các khối nội dung Blocks chuyên biệt
    rounds_done = len(discussion_history)

    # Tạo khối Callout thông báo kết quả thảo luận
    summary_callout = {
        "type": "callout",
        "variant": "success" if is_passed else "info",
        "title": f"👥 Thảo Luận 2 AI Hoàn Tất ({rounds_done}/{max_rounds} Vòng)",
        "content": (
            f"**Cơ chế phản biện song song (Actor-Critic):**\n"
            f"- 🤖 **AI Thực Thi**: `{selected_worker_model}` | Kỹ năng: `{skill_name or 'Tiêu chuẩn'}`\n"
            f"- 🧐 **AI Đánh Giá**: `{selected_evaluator_model}`\n"
            f"- 🏁 **Kết luận cuối cùng**: **{'Đạt chuẩn xuất sắc [PASSED]' if is_passed else 'Đã qua các vòng cải thiện tối ưu'}** (Điểm: `{discussion_history[-1].get('score', '9/10')}`)\n"
            f"- Đã duyệt qua `{rounds_done}` lần phản biện và tự động hiệu chỉnh."
        )
    }

    # Phân giải câu trả lời cuối cùng thành các Blocks phong phú
    response_blocks = parse_response_to_blocks(current_draft)

    # Đưa khối thông báo thảo luận lên đầu danh sách blocks
    final_blocks = [summary_callout] + response_blocks

    total_tokens = total_prompt_tokens + total_completion_tokens
    usage_dict = {
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "prompt": total_prompt_tokens,
        "completion": total_completion_tokens,
        "total": total_tokens
    }

    return current_draft, account_used, discussion_history, final_blocks, total_est_tokens, usage_dict
