import time
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from client import antigravity_client

logger = logging.getLogger("antigravity-quota-fetcher")

# Cache lưu trữ quota của từng account: account_id -> (data, expire_timestamp)
_QUOTA_CACHE: Dict[str, Tuple[Dict[str, Any], float]] = {}
CACHE_TTL = 90  # 90 giây


def fetch_account_quota(account: Dict[str, Any], force_refresh: bool = False) -> Dict[str, Any]:
    acc_id = account.get("id", "")
    acc_email = account.get("email", "unknown")
    now = time.time()

    # Kiểm tra cache
    if not force_refresh and acc_id in _QUOTA_CACHE:
        cached_data, expire_at = _QUOTA_CACHE[acc_id]
        if now < expire_at:
            return cached_data

    # Cấu trúc mặc định
    result: Dict[str, Any] = {
        "account_id": acc_id,
        "email": acc_email,
        "name": account.get("name") or acc_email.split("@")[0],
        "picture": account.get("picture"),
        "is_active": account.get("is_active", True),
        "is_primary": account.get("is_primary", False),
        "gemini": {
            "used_percent": 0.0,
            "remaining_percent": 100.0,
            "remaining_fraction": 1.0,
            "reset_time": None
        },
        "claude": {
            "used_percent": 0.0,
            "remaining_percent": 100.0,
            "remaining_fraction": 1.0,
            "reset_time": None
        },
        "status": "ok",
        "error": None,
        "last_updated": now
    }

    if not account.get("is_active", True):
        result["status"] = "inactive"
        return result

    try:
        token = antigravity_client.get_token_for_account(account)
    except Exception as e:
        logger.warning(f"Không thể lấy token cho {acc_email}: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result

    project_id = account.get("project_id") or "aicode-consumers"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        **config.ANTIGRAVITY_HEADERS
    }
    payload = {"project": project_id}

    response_data = None
    last_err = None

    for endpoint in config.ENDPOINTS:
        try:
            res = requests.post(
                f"{endpoint}/v1internal:fetchAvailableModels",
                headers=headers,
                json=payload,
                timeout=12
            )
            if res.status_code == 200:
                response_data = res.json()
                break
            elif res.status_code == 429:
                result["status"] = "rate_limited"
                result["error"] = "Google Quota 429 Rate Limited"
                last_err = "429 Rate Limited"
            else:
                last_err = f"{res.status_code}: {res.text[:150]}"
        except Exception as ex:
            last_err = str(ex)

    if not response_data:
        if result["status"] == "ok":
            result["status"] = "error"
            result["error"] = last_err or "Không thể kết nối đến Google Antigravity API"
        return result

    models = response_data.get("models", {})

    # 1. Tìm hạn ngạch Gemini (ưu tiên gemini-3.8-flash-tiered, sau đó bất kỳ gemini-* nào có quotaInfo)
    gemini_quota_raw = None
    if "gemini-3.8-flash-tiered" in models and models["gemini-3.8-flash-tiered"].get("quotaInfo"):
        gemini_quota_raw = models["gemini-3.8-flash-tiered"]["quotaInfo"]
    else:
        for m_name, m_info in models.items():
            if m_name.startswith("gemini-") and m_info.get("quotaInfo"):
                gemini_quota_raw = m_info["quotaInfo"]
                break

    if gemini_quota_raw:
        rem_frac = float(gemini_quota_raw.get("remainingFraction", 1.0))
        rem_frac = max(0.0, min(1.0, rem_frac))
        used_frac = max(0.0, 1.0 - rem_frac)
        result["gemini"] = {
            "used_percent": round(used_frac * 100, 1),
            "remaining_percent": round(rem_frac * 100, 1),
            "remaining_fraction": rem_frac,
            "reset_time": gemini_quota_raw.get("resetTime")
        }

    # 2. Tìm hạn ngạch Claude (ưu tiên claude-sonnet-4-6, sau đó bất kỳ claude-* nào có quotaInfo)
    claude_quota_raw = None
    if "claude-sonnet-4-6" in models and models["claude-sonnet-4-6"].get("quotaInfo"):
        claude_quota_raw = models["claude-sonnet-4-6"]["quotaInfo"]
    else:
        for m_name, m_info in models.items():
            if m_name.startswith("claude-") and m_info.get("quotaInfo"):
                claude_quota_raw = m_info["quotaInfo"]
                break

    if claude_quota_raw:
        rem_frac = float(claude_quota_raw.get("remainingFraction", 1.0))
        rem_frac = max(0.0, min(1.0, rem_frac))
        used_frac = max(0.0, 1.0 - rem_frac)
        result["claude"] = {
            "used_percent": round(used_frac * 100, 1),
            "remaining_percent": round(rem_frac * 100, 1),
            "remaining_fraction": rem_frac,
            "reset_time": claude_quota_raw.get("resetTime")
        }

    # Lưu vào cache
    _QUOTA_CACHE[acc_id] = (result, now + CACHE_TTL)
    return result


def fetch_all_accounts_quota(accounts: List[Dict[str, Any]], force_refresh: bool = False) -> Dict[str, Any]:
    """Quét song song toàn bộ tài khoản để lấy hạn ngạch Google Antigravity và tính toán tổng hợp."""
    accounts_quota: Dict[str, Dict[str, Any]] = {}
    active_accounts = [a for a in accounts if a.get("is_active", True)]

    # Chạy song song qua ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(12, max(2, len(active_accounts)))) as executor:
        future_to_acc = {
            executor.submit(fetch_account_quota, acc, force_refresh): acc
            for acc in accounts
        }
        for future in as_completed(future_to_acc):
            acc = future_to_acc[future]
            try:
                data = future.result()
                accounts_quota[acc["id"]] = data
            except Exception as e:
                logger.error(f"Lỗi fetch quota cho {acc.get('email')}: {e}")
                accounts_quota[acc["id"]] = {
                    "account_id": acc["id"],
                    "email": acc.get("email", ""),
                    "status": "error",
                    "error": str(e),
                    "gemini": {"used_percent": 0.0, "remaining_percent": 0.0, "reset_time": None},
                    "claude": {"used_percent": 0.0, "remaining_percent": 0.0, "reset_time": None},
                }

    # Tính toán chỉ số tổng hợp (Aggregation)
    valid_gemini_rem = []
    valid_claude_rem = []
    healthy_count = 0
    exhausted_count = 0

    for acc_id, q in accounts_quota.items():
        if q.get("status") in ("ok", "rate_limited"):
            gem = q.get("gemini", {})
            cld = q.get("claude", {})
            g_rem = gem.get("remaining_percent", 100.0)
            c_rem = cld.get("remaining_percent", 100.0)

            valid_gemini_rem.append(g_rem)
            valid_claude_rem.append(c_rem)

            if g_rem <= 2.0 or c_rem <= 2.0 or q.get("status") == "rate_limited":
                exhausted_count += 1
            else:
                healthy_count += 1

    total_valid = len(valid_gemini_rem)
    gemini_avg_remaining = round(sum(valid_gemini_rem) / total_valid, 1) if total_valid > 0 else 100.0
    gemini_avg_used = round(100.0 - gemini_avg_remaining, 1)

    claude_avg_remaining = round(sum(valid_claude_rem) / total_valid, 1) if total_valid > 0 else 100.0
    claude_avg_used = round(100.0 - claude_avg_remaining, 1)

    return {
        "timestamp": time.time(),
        "total_accounts": len(accounts),
        "active_accounts": len(active_accounts),
        "healthy_count": healthy_count,
        "exhausted_count": exhausted_count,
        "summary": {
            "gemini": {
                "avg_used_percent": gemini_avg_used,
                "avg_remaining_percent": gemini_avg_remaining,
            },
            "claude": {
                "avg_used_percent": claude_avg_used,
                "avg_remaining_percent": claude_avg_remaining,
            }
        },
        "accounts": accounts_quota
    }
