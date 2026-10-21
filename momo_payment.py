"""
MoMo Payment Gateway Integration Module (API V2)
Hỗ trợ thanh toán MoMo cho Antigravity Gateway:
- Chuẩn giao thức MoMo All In One / Collection API v2
- Chữ ký số HMAC-SHA256 bảo mật
- Hỗ trợ chế độ Sandbox (Test) và Production
- Lưu trữ giao dịch vào MySQL (bảng `payment_transactions`)
- Tự động cộng tokens vào tài khoản người dùng khi nhận Webhook IPN
"""

import hmac
import hashlib
import json
import time
import uuid
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger("antigravity-momo")

# Cấu hình mặc định MoMo Sandbox / Test (dành cho thử nghiệm ngay)
DEFAULT_MOMO_CONFIG = {
    "environment": "sandbox",
    "partnerCode": "MOMO",
    "accessKey": "F8BBA842ECF85",
    "secretKey": "K951B6PE1waDMi640xX08PD3vg6EkVlz",
    "endpoint": "https://test-payment.momo.vn/v2/gateway/api/create",
    "query_endpoint": "https://test-payment.momo.vn/v2/gateway/api/query",
    "redirectUrl": "http://localhost:5678/payment/return",
    "ipnUrl": "http://localhost:5678/api/payment/momo/ipn",
    "partnerName": "Antigravity AI Gateway",
    "storeId": "AntigravityStore"
}

# Danh mục các gói Token tiêu chuẩn
TOKEN_PACKAGES = [
    {
        "id": "pkg_starter",
        "name": "Gói Khởi Động",
        "amount": 20000,
        "tokens": 2000000,
        "bonus_text": "Tiêu chuẩn",
        "badge": "2 Triệu Tokens",
        "description": "Thích hợp thử nghiệm và nhu cầu chat nhẹ hàng ngày"
    },
    {
        "id": "pkg_standard",
        "name": "Gói Tiêu Chuẩn",
        "amount": 50000,
        "tokens": 6000000,
        "bonus_text": "+20% Thưởng",
        "badge": "6 Triệu Tokens",
        "description": "Phù hợp cho lập trình viên cá nhân và học tập"
    },
    {
        "id": "pkg_pro",
        "name": "Gói Chuyên Nghiệp",
        "amount": 100000,
        "tokens": 15000000,
        "bonus_text": "+50% Thưởng",
        "badge": "15 Triệu Tokens",
        "popular": True,
        "description": "Khuyên dùng cho lập trình dự án lớn, phân tích code và file"
    },
    {
        "id": "pkg_vip",
        "name": "Gói Doanh Nghiệp",
        "amount": 200000,
        "tokens": 35000000,
        "bonus_text": "+75% Thưởng",
        "badge": "35 Triệu Tokens",
        "description": "Xử lý khối lượng công việc khổng lồ, gọi API liên tục"
    }
]


class MoMoPaymentService:
    def __init__(self):
        pass

    def get_config(self) -> Dict[str, Any]:
        """Lấy cấu hình MoMo từ MySQL settings (nếu có), fallback về mặc định"""
        config = dict(DEFAULT_MOMO_CONFIG)
        try:
            import db
            row = db.fetch_one("SELECT setting_value FROM settings WHERE setting_key = 'momo_config'")
            if row and row.get("setting_value"):
                saved_conf = json.loads(row["setting_value"])
                config.update(saved_conf)
                # Cập nhật endpoint dựa theo environment nếu chưa gán cứng
                if config.get("environment") == "production":
                    config["endpoint"] = "https://payment.momo.vn/v2/gateway/api/create"
                    config["query_endpoint"] = "https://payment.momo.vn/v2/gateway/api/query"
                else:
                    config["endpoint"] = "https://test-payment.momo.vn/v2/gateway/api/create"
                    config["query_endpoint"] = "https://test-payment.momo.vn/v2/gateway/api/query"
        except Exception as e:
            logger.debug(f"Không thể đọc cấu hình MoMo từ DB: {e}")

        # Đồng bộ cả hai chuẩn đặt tên camelCase và snake_case
        config["partner_code"] = config.get("partnerCode", config.get("partner_code", ""))
        config["access_key"] = config.get("accessKey", config.get("access_key", ""))
        config["secret_key"] = config.get("secretKey", config.get("secret_key", ""))
        config["redirect_url"] = config.get("redirectUrl", config.get("redirect_url", ""))
        config["ipn_url"] = config.get("ipnUrl", config.get("ipn_url", ""))
        config["partnerCode"] = config["partner_code"]
        config["accessKey"] = config["access_key"]
        config["secretKey"] = config["secret_key"]
        config["redirectUrl"] = config["redirect_url"]
        config["ipnUrl"] = config["ipn_url"]
        return config

    @property
    def config(self) -> Dict[str, Any]:
        """Thuộc tính truy cập cấu hình tiện lợi"""
        return self.get_config()

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật cấu hình từ dict và lưu vào DB"""
        current = self.get_config()
        if "partner_code" in new_config:
            current["partnerCode"] = new_config["partner_code"]
        elif "partnerCode" in new_config:
            current["partnerCode"] = new_config["partnerCode"]

        if "access_key" in new_config:
            current["accessKey"] = new_config["access_key"]
        elif "accessKey" in new_config:
            current["accessKey"] = new_config["accessKey"]

        if "secret_key" in new_config and new_config["secret_key"]:
            current["secretKey"] = new_config["secret_key"]
        elif "secretKey" in new_config and new_config["secretKey"]:
            current["secretKey"] = new_config["secretKey"]

        if "redirect_url" in new_config:
            current["redirectUrl"] = new_config["redirect_url"]
        elif "redirectUrl" in new_config:
            current["redirectUrl"] = new_config["redirectUrl"]

        if "ipn_url" in new_config:
            current["ipnUrl"] = new_config["ipn_url"]
        elif "ipnUrl" in new_config:
            current["ipnUrl"] = new_config["ipnUrl"]

        if "environment" in new_config:
            current["environment"] = new_config["environment"].strip().lower()

        self.save_config(current)
        return self.get_config()

    def save_config(self, new_config: Dict[str, Any]) -> bool:
        """Lưu cấu hình MoMo vào MySQL settings"""
        try:
            import db
            cfg_to_save = {
                "environment": new_config.get("environment", "sandbox"),
                "partnerCode": (new_config.get("partnerCode") or new_config.get("partner_code") or "").strip(),
                "accessKey": (new_config.get("accessKey") or new_config.get("access_key") or "").strip(),
                "secretKey": (new_config.get("secretKey") or new_config.get("secret_key") or "").strip(),
                "redirectUrl": (new_config.get("redirectUrl") or new_config.get("redirect_url") or "").strip() or DEFAULT_MOMO_CONFIG["redirectUrl"],
                "ipnUrl": (new_config.get("ipnUrl") or new_config.get("ipn_url") or "").strip() or DEFAULT_MOMO_CONFIG["ipnUrl"]
            }
            db.execute("""
                INSERT INTO settings (setting_key, setting_value, updated_at)
                VALUES ('momo_config', %s, %s)
                ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value), updated_at=VALUES(updated_at)
            """, (json.dumps(cfg_to_save, ensure_ascii=False), time.time()))
            logger.info("Đã cập nhật cấu hình MoMo thành công.")
            return True
        except Exception as e:
            logger.error(f"Lỗi lưu cấu hình MoMo: {e}")
            return False

    def generate_signature(self, raw_data: str, secret_key: str) -> str:
        """Tạo chữ ký HMAC-SHA256 theo chuẩn MoMo"""
        return hmac.new(
            secret_key.encode("utf-8"),
            raw_data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def create_payment(
        self,
        user_id: str,
        amount: Optional[int] = None,
        tokens_granted: Optional[int] = None,
        package_name: str = "",
        user_email: str = "",
        client_redirect_url: Optional[str] = None,
        package_id: Optional[str] = None,
        custom_amount: Optional[int] = None,
        redirect_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo đơn hàng thanh toán MoMo và gọi API MoMo v2 lấy URL / QR thanh toán
        """
        config = self.get_config()

        # Tự động phân giải gói nạp nếu có package_id
        if package_id:
            pkg = next((p for p in TOKEN_PACKAGES if p["id"] == package_id), None)
            if pkg:
                amount = pkg["amount"]
                tokens_granted = pkg["tokens"]
                package_name = pkg["name"]

        # Xử lý nạp tùy chỉnh nếu có custom_amount
        if custom_amount:
            amount = int(custom_amount)
            tokens_granted = int(amount * 100)
            package_name = f"Nạp tùy chọn {amount:,} VNĐ"

        if not amount or amount < 1000:
            amount = 20000
        if not tokens_granted:
            tokens_granted = int(amount * 100)

        order_id = f"MOMO_ORD_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        request_id = str(uuid.uuid4().hex)
        order_info = f"Nap {tokens_granted:,} Tokens AI - {package_name or 'Tuy chon'} (User: {user_id})"

        final_redirect_url = client_redirect_url or redirect_url or config.get("redirectUrl") or DEFAULT_MOMO_CONFIG["redirectUrl"]
        ipn_url = config.get("ipnUrl") or DEFAULT_MOMO_CONFIG["ipnUrl"]
        request_type = "captureWallet"
        extra_data = json.dumps({"user_id": user_id, "tokens": tokens_granted}, ensure_ascii=False)

        # 1. Tạo chuỗi raw signature theo đúng thứ tự tài liệu MoMo v2
        raw_signature = (
            f"accessKey={config['accessKey']}"
            f"&amount={amount}"
            f"&extraData={extra_data}"
            f"&ipnUrl={ipn_url}"
            f"&orderId={order_id}"
            f"&orderInfo={order_info}"
            f"&partnerCode={config['partnerCode']}"
            f"&redirectUrl={final_redirect_url}"
            f"&requestId={request_id}"
            f"&requestType={request_type}"
        )
        signature = self.generate_signature(raw_signature, config["secretKey"])

        payload = {
            "partnerCode": config["partnerCode"],
            "partnerName": config.get("partnerName", "Antigravity AI"),
            "storeId": config.get("storeId", "AntigravityStore"),
            "requestId": request_id,
            "amount": int(amount),
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": final_redirect_url,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "extraData": extra_data,
            "requestType": request_type,
            "signature": signature
        }

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"

        # 2. Gọi API MoMo
        pay_url = ""
        qr_code_url = ""
        deeplink = ""
        message = ""

        try:
            logger.info(f"Đang gửi yêu cầu thanh toán tới MoMo ({config['endpoint']}) cho đơn {order_id} ({amount:,} VND)...")
            res = requests.post(config["endpoint"], json=payload, timeout=20)
            res_data = res.json()
            logger.info(f"MoMo phản hồi: {json.dumps(res_data, ensure_ascii=False)}")

            if res_data.get("resultCode") == 0:
                pay_url = res_data.get("payUrl", "")
                qr_code_url = res_data.get("qrCodeUrl", "")
                deeplink = res_data.get("deeplink", "")
                message = res_data.get("message", "Khởi tạo thành công")
            else:
                message = res_data.get("message", f"MoMo từ chối: resultCode {res_data.get('resultCode')}")
                logger.warning(f"Tạo đơn MoMo không thành công: {message}")
        except Exception as e:
            logger.error(f"Lỗi kết nối tới MoMo API: {e}")
            message = f"Lỗi kết nối cổng MoMo: {str(e)}"

        # 3. Lưu giao dịch vào MySQL
        try:
            import db
            db.execute("""
                INSERT INTO payment_transactions (
                    id, user_id, order_id, request_id, amount, tokens_granted,
                    package_name, status, payment_url, qr_code_url, deeplink,
                    message, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                tx_id, user_id, order_id, request_id, int(amount), int(tokens_granted),
                package_name, "pending", pay_url, qr_code_url, deeplink,
                message, now_str, now_str
            ))
        except Exception as e:
            logger.error(f"Lỗi lưu transaction vào DB: {e}")

        return {
            "status": "ok" if pay_url else "error",
            "order_id": order_id,
            "request_id": request_id,
            "amount": amount,
            "tokens": tokens_granted,
            "tokens_granted": tokens_granted,
            "package_name": package_name,
            "pay_url": pay_url,
            "qr_code_url": qr_code_url,
            "deeplink": deeplink,
            "message": message,
            "environment": config.get("environment", "sandbox")
        }

    def verify_ipn(self, data: Dict[str, Any]) -> bool:
        """Xác thực tính hợp lệ của chữ ký Webhook IPN từ MoMo"""
        config = self.get_config()
        secret_key = config["secretKey"]
        received_signature = data.get("signature", "")

        # Raw data thứ tự theo chuẩn IPN MoMo v2
        raw_signature = (
            f"accessKey={config['accessKey']}"
            f"&amount={data.get('amount')}"
            f"&extraData={data.get('extraData', '')}"
            f"&message={data.get('message', '')}"
            f"&orderId={data.get('orderId')}"
            f"&orderInfo={data.get('orderInfo')}"
            f"&orderType={data.get('orderType', '')}"
            f"&partnerCode={data.get('partnerCode')}"
            f"&payType={data.get('payType', '')}"
            f"&requestId={data.get('requestId')}"
            f"&responseTime={data.get('responseTime')}"
            f"&resultCode={data.get('resultCode')}"
            f"&transId={data.get('transId', '')}"
        )
        calculated_signature = self.generate_signature(raw_signature, secret_key)
        is_valid = (received_signature == calculated_signature)
        if not is_valid:
            logger.warning(f"Chữ ký IPN MoMo không hợp lệ! Nhận: {received_signature} != Tính: {calculated_signature}")
        return is_valid

    def handle_ipn(self, ipn_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Xử lý khi MoMo gọi IPN Callback:
        - Xác minh chữ ký
        - Cập nhật giao dịch sang 'success' hoặc 'failed'
        - Cộng token vào tài khoản người dùng
        """
        if not self.verify_ipn(ipn_data):
            return {"status": "error", "message": "Invalid signature"}

        order_id = ipn_data.get("orderId")
        result_code = ipn_data.get("resultCode")
        trans_id = str(ipn_data.get("transId") or "")
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            import db
            from user_manager import user_manager

            tx = db.fetch_one("SELECT * FROM payment_transactions WHERE order_id = %s", (order_id,))
            if not tx:
                logger.error(f"IPN: Không tìm thấy đơn hàng {order_id}")
                return {"status": "error", "message": "Order not found"}

            # Nếu đơn hàng đã hoàn tất trước đó (Idempotency)
            if tx.get("status") == "success":
                logger.info(f"Đơn hàng {order_id} đã được xử lý thành công trước đó.")
                return {"status": "ok", "message": "Order already completed"}

            if str(result_code) == "0":
                # Thanh toán thành công!
                tokens_to_add = int(tx.get("tokens_granted") or 0)
                amount = float(tx.get("amount") or 0)
                user_id = tx["user_id"]

                # 1. Cập nhật transaction
                db.execute("""
                    UPDATE payment_transactions
                    SET status = 'success',
                        momo_trans_id = %s,
                        message = 'Giao dịch thành công',
                        updated_at = %s
                    WHERE order_id = %s
                """, (trans_id, now_str, order_id))

                # 2. Cộng token cho user
                user_manager.add_user_tokens(user_id, tokens=tokens_to_add, amount=amount)
                logger.info(f"Hoàn tất xử lý IPN: Đã cộng {tokens_to_add:,} tokens cho user {user_id} (Đơn: {order_id})")
                return {"status": "ok", "message": "Payment processed successfully"}
            else:
                # Thanh toán thất bại hoặc bị hủy
                db.execute("""
                    UPDATE payment_transactions
                    SET status = 'failed',
                        momo_trans_id = %s,
                        message = %s,
                        updated_at = %s
                    WHERE order_id = %s
                """, (trans_id, ipn_data.get("message", "Thanh toán thất bại"), now_str, order_id))
                logger.warning(f"Đơn hàng {order_id} thanh toán thất bại: {ipn_data.get('message')}")
                return {"status": "ok", "message": "Transaction marked as failed"}
        except Exception as e:
            logger.error(f"Lỗi khi xử lý IPN MoMo: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def check_transaction_status(self, order_id: str) -> Dict[str, Any]:
        """Kiểm tra trạng thái đơn hàng trong DB (dành cho frontend polling)"""
        try:
            import db
            tx = db.fetch_one("SELECT * FROM payment_transactions WHERE order_id = %s", (order_id,))
            if tx:
                return {
                    "status": "ok",
                    "transaction": {
                        "id": tx["id"],
                        "order_id": tx["order_id"],
                        "amount": tx["amount"],
                        "tokens_granted": tx["tokens_granted"],
                        "package_name": tx.get("package_name"),
                        "payment_status": tx["status"],
                        "momo_trans_id": tx.get("momo_trans_id"),
                        "created_at": tx["created_at"],
                        "updated_at": tx["updated_at"]
                    }
                }
            return {"status": "error", "message": "Không tìm thấy đơn hàng"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_user_transactions(self, user_id: str) -> List[Dict[str, Any]]:
        """Lấy danh sách lịch sử nạp tiền của một user"""
        try:
            import db
            rows = db.fetch_all("""
                SELECT id, order_id, amount, tokens_granted, package_name,
                       status, momo_trans_id, created_at, updated_at
                FROM payment_transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
            return rows or []
        except Exception as e:
            logger.error(f"Lỗi lấy lịch sử giao dịch user {user_id}: {e}")
            return []

    def get_all_transactions(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ lịch sử giao dịch (cho Admin) kèm tên user"""
        try:
            import db
            rows = db.fetch_all("""
                SELECT pt.id, pt.user_id, pt.order_id, pt.amount, pt.tokens_granted,
                       pt.package_name, pt.status, pt.momo_trans_id, pt.created_at, pt.updated_at,
                       u.name as user_name, u.email as user_email
                FROM payment_transactions pt
                LEFT JOIN users u ON pt.user_id = u.id
                ORDER BY pt.created_at DESC
                LIMIT 100
            """)
            return rows or []
        except Exception as e:
            logger.error(f"Lỗi lấy toàn bộ giao dịch cho admin: {e}")
            return []


# Singleton
momo_service = MoMoPaymentService()
