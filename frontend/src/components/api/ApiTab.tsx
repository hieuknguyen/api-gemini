import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { apiRequest } from '../../services/apiClient';
import { userService } from '../../services/userService';
import { UsersTab } from '../users/UsersTab';
import { SettingsTab } from '../settings/SettingsTab';
import {
  KeyRound,
  FileDown,
  Shuffle,
  Edit3,
  Eye,
  EyeOff,
  Copy,
  Check,
  Code2,
  Terminal,
  BookOpen,
  Send,
  Layers,
  Sparkles,
  HelpCircle,
  ExternalLink,
  Lock
} from 'lucide-react';

export const ApiTab: React.FC = () => {
  const { user, isAdmin, token, updateToken, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [apiKey, setApiKey] = useState(token || '');
  const [showKey, setShowKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [isCustomKeyOpen, setIsCustomKeyOpen] = useState(false);
  const [customKeyInput, setCustomKeyInput] = useState('');
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  // Tải hoặc đồng bộ API Key duy nhất của tài khoản đăng nhập
  const fetchUserKey = async () => {
    if (!user) {
      setApiKey('');
      return;
    }
    try {
      const keys = await userService.getUserKeys(user.id);
      if (keys && keys.length > 0) {
        const k = keys[0].key_value;
        setApiKey(k);
        if (k !== token) {
          updateToken(k);
        }
      } else if (token) {
        setApiKey(token);
      }
    } catch {
      if (token) setApiKey(token);
    }
  };

  useEffect(() => {
    if (user) {
      fetchUserKey();
    } else {
      setApiKey('');
    }
  }, [user?.id, token]);

  const handleGenerateRandomKey = async () => {
    if (!user) {
      openAuthModal('login');
      return;
    }
    try {
      const res = await userService.createApiKey(user.id, `Key - ${user.name}`);
      if (res?.key_value) {
        setApiKey(res.key_value);
        updateToken(res.key_value);
        showToast('Đã tạo API Key ngẫu nhiên mới duy nhất cho tài khoản của bạn!', 'success');
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi tạo API Key', 'error');
    }
  };

  const handleSaveCustomKey = async () => {
    if (!user) {
      openAuthModal('login');
      return;
    }
    if (!customKeyInput.trim()) return;
    const newKey = customKeyInput.trim();
    try {
      const res = await userService.createApiKey(user.id, `Key - ${user.name}`, newKey);
      if (res?.key_value) {
        setApiKey(res.key_value);
        updateToken(res.key_value);
        setIsCustomKeyOpen(false);
        setCustomKeyInput('');
        showToast('Đã lưu API Key tùy chỉnh duy nhất cho tài khoản!', 'success');
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu API Key', 'error');
    }
  };

  const currentEffectiveKey = user ? (apiKey || token || '') : '';

  const handleCopyKey = () => {
    if (!user) {
      openAuthModal('login');
      return;
    }
    if (!currentEffectiveKey) return;
    navigator.clipboard.writeText(currentEffectiveKey);
    setCopiedKey(true);
    showToast('Đã sao chép API Key vào clipboard!', 'success');
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleDownloadDocsMarkdown = () => {
    window.open('/api/docs/markdown', '_blank');
  };

  const copyCode = (codeText: string, id: string, label = 'code') => {
    navigator.clipboard.writeText(codeText);
    setCopiedCodeId(id);
    showToast(`Đã sao chép ${label} vào clipboard!`, 'success');
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const displayKey = user && currentEffectiveKey ? currentEffectiveKey : 'sk-antigravity-YOUR-KEY-HERE';

  const fullJsonTemplate = `{
  "prompt": "Viết bài chuẩn SEO giới thiệu các tính năng Antigravity AI Gateway",
  "model": "gemini-3.8-flash-tiered",
  "messages": [
    { "role": "user", "content": "Xin chào, tôi là lập trình viên." },
    { "role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì cho dự án của bạn?" },
    { "role": "user", "content": "Viết bài chuẩn SEO giới thiệu các tính năng Antigravity AI Gateway" }
  ],
  "web_search": true,
  "thinking": false,
  "temperature": 0.7,
  "stream": false
}`;

  const pythonSkillExample = `import requests

url = "http://localhost:5678/webhook/antigravity-chat"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "${displayKey}"  # Dùng API Key đã tạo trong tài khoản của bạn
}

payload = {
    "prompt": "Viết bài chia sẻ về xu hướng AI trong năm 2026",
    "thinking": False,             # Tắt thinking để tốc độ phản hồi nhanh hơn
    "web_search": True             # Cho phép tra cứu Google cập nhật số liệu mới
}

res = requests.post(url, json=payload, headers=headers)
data = res.json()

print("Kỹ năng đã kích hoạt:", data.get("skill_used"))
print("Mã Skill ID:", data.get("skill_id"))
print("Nội dung AI trả lời:\n", data.get("response"))`;

  const curlSkillExample = `curl -X POST "http://localhost:5678/webhook/antigravity-chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${displayKey}" \
  -d '{
    "prompt": "Viết bài chuẩn SEO theo các nguyên tắc đã cấu hình",
  }'`;

  const pythonSessionExample = `import os
import json
import requests

URL = "http://localhost:5678/webhook/antigravity-chat"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": "${displayKey}"  # Thay bằng API Key của bạn
}
HISTORY_FILE = "chat_history.json"

def load_history():
    """1. ĐỌC LỊCH SỬ TỪ FILE JSON RA"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(messages):
    """2. LƯU LỊCH SỬ CẬP NHẬT VÀO FILE JSON"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def chat(user_message):
    # Bước 1: Lấy toàn bộ đoạn hội thoại cũ từ file JSON
    messages = load_history()

    # Bước 2: Thêm tin nhắn mới của người dùng vào danh sách
    messages.append({
        "role": "user",
        "content": user_message
    })

    # Bước 3: Gửi toàn bộ danh sách messages lên API Gateway
    payload = {
        "messages": messages,
        "model": "gemini-3.8-flash-tiered",
        "web_search": True
    }
    response = requests.post(URL, json=payload, headers=HEADERS).json()

    ai_reply = response.get("response", "")
    print("AI:", ai_reply)

    # Bước 4: Lưu câu trả lời của AI vào danh sách
    messages.append({
        "role": "assistant",
        "content": ai_reply
    })

    # Bước 5: Ghi đè file JSON để bảo lưu ngữ cảnh cho các lần trò chuyện sau
    save_history(messages)

# --- VÍ DỤ SỬ DỤNG ---
# Lần 1: Giới thiệu thông tin
chat("Tên tôi là Hiếu, tôi là lập trình viên backend.")

# Lần 2: Hỏi lại - AI sẽ đọc file JSON và nhớ chính xác bạn là ai!
chat("Tên tôi là gì và tôi làm nghề gì?")`;

  const pythonVisionExample = `import requests, base64

url = "http://localhost:5678/webhook/antigravity-chat"
headers = {"X-API-Key": "${displayKey}"}

with open("sample.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

data = {
    "prompt": "Bức ảnh này có nội dung gì?",
    "image": img_b64,
    "thinking": False
}

res = requests.post(url, json=data, headers=headers)
print("AI Trả lời:", res.json().get("response"))`;

  return (
    <div className="flex flex-col gap-6 overflow-y-auto pr-1 pb-8">
      {/* 1. API Key Card */}
      {!user ? (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-4 shadow-sm text-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto shadow-inner">
            <Lock className="w-7 h-7" />
          </div>
          <div className="max-w-lg mx-auto space-y-2">
            <div className="flex items-center justify-center space-x-2">
              <h3 className="font-bold text-lg text-white">Yêu Cầu Đăng Nhập Để Tạo & Xem API Key</h3>
              <span className="px-2.5 py-0.5 text-[10px] font-semibold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                1 Tài khoản • 1 Key duy nhất
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Chỉ có tài khoản đã đăng nhập mới được tạo, xem và quản trị API Key. Mỗi tài khoản chỉ được sở hữu đúng 1 API Key duy nhất để kết nối ứng dụng với AI Gateway. Vui lòng đăng nhập để bắt đầu!
            </p>
          </div>
          <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
            <button
              onClick={() => openAuthModal('login')}
              className="flex items-center space-x-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-blue-600/20 active:scale-95"
            >
              <KeyRound className="w-4 h-4" />
              <span>Đăng Nhập Ngay</span>
            </button>
            <button
              onClick={() => openAuthModal('register')}
              className="flex items-center space-x-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold transition active:scale-95"
            >
              <span>Đăng Ký Tài Khoản</span>
            </button>
            <button
              onClick={handleDownloadDocsMarkdown}
              className="flex items-center space-x-2 px-4 py-2.5 bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-semibold transition active:scale-95"
            >
              <FileDown className="w-4 h-4 text-emerald-400" />
              <span>Tải Docs Markdown</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shadow">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-base text-white">
                    API Key Của Bạn (<span className="text-blue-400 font-mono">X-API-Key</span>)
                  </h3>
                  <span className="px-2.5 py-0.5 text-[10px] font-semibold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    1 Tài khoản • 1 Key duy nhất
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    Hoạt động
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Mỗi tài khoản được cấp đúng 1 API Key duy nhất. Gửi key này qua header <code className="text-blue-400 font-semibold">X-API-Key</code> trong các request từ ứng dụng của bạn.
                </p>
              </div>
            </div>

            {/* Quick Action Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleDownloadDocsMarkdown}
                className="flex items-center space-x-2 px-3.5 py-2 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-600/20 border border-emerald-500/30 active:scale-95"
                title="Tải toàn bộ tài liệu đặc tả API chi tiết nhất dạng file Markdown (.md) cho AI / Cursor / Developers đọc"
              >
                <FileDown className="w-4 h-4" />
                <span>📥 Tải Docs .MD Cho AI</span>
              </button>
              <button
                onClick={handleGenerateRandomKey}
                className="flex items-center space-x-2 px-3.5 py-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-blue-600/20 active:scale-95"
                title="Tạo ngẫu nhiên API Key mới duy nhất cho tài khoản này"
              >
                <Shuffle className="w-3.5 h-3.5" />
                <span>🎲 Đổi Key Ngẫu Nhiên</span>
              </button>
              <button
                onClick={() => setIsCustomKeyOpen(!isCustomKeyOpen)}
                className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-medium transition active:scale-95"
                title="Tự nhập key tùy ý cho tài khoản của bạn"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>Tự nhập</span>
              </button>
            </div>
          </div>

          {/* Key Display Box */}
          <div className="flex items-center space-x-2.5 max-w-2xl">
            <div className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs font-mono text-slate-200 flex items-center justify-between shadow-inner">
              <div className="flex items-center space-x-2 overflow-hidden w-full">
                <span className="text-slate-500 select-none shrink-0">X-API-Key:</span>
                <span className="text-blue-300 font-bold tracking-wide truncate">
                  {showKey ? displayKey : (displayKey.length > 14 ? displayKey.slice(0, 14) + '••••••••••••••••' : '••••••••••••••••')}
                </span>
              </div>
              <button
                onClick={() => setShowKey(!showKey)}
                className="text-slate-400 hover:text-slate-200 text-xs px-2 py-0.5 rounded transition shrink-0"
                title={showKey ? 'Ẩn Key' : 'Hiện Key'}
              >
                {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <button
              onClick={handleCopyKey}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-medium flex items-center space-x-1.5 transition shadow-lg shadow-blue-600/20 shrink-0 active:scale-95"
            >
              {copiedKey ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
              <span>{copiedKey ? 'Đã chép' : 'Sao chép Key'}</span>
            </button>
          </div>

          {/* Custom Manual Key Input Box */}
          {isCustomKeyOpen && (
            <div className="max-w-2xl bg-slate-950/90 border border-slate-800 rounded-xl p-3.5 space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Nhập API Key thủ công theo ý muốn (sẽ cập nhật key duy nhất của bạn):
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={customKeyInput}
                  onChange={(e) => setCustomKeyInput(e.target.value)}
                  placeholder="Nhập key tùy chỉnh (ví dụ: my_secret_token_123)..."
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleSaveCustomKey}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition"
                >
                  Lưu Key
                </button>
                <button
                  onClick={() => setIsCustomKeyOpen(false)}
                  className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg text-xs transition"
                >
                  Hủy
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. Quản Lý Người Dùng & API Keys Riêng Biệt (Admin Only) */}
      {isAdmin && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
          <UsersTab />
        </div>
      )}

      {/* 3. Danh Sách Endpoints */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <h3 className="font-bold text-base text-white">Danh sách Endpoints</h3>
        <div className="space-y-3">
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 text-xs font-bold rounded bg-blue-500/20 text-blue-400">POST</span>
                <code className="text-sm font-semibold text-slate-200">/webhook/antigravity-chat</code>
                <span className="text-xs text-emerald-400 font-medium">(Endpoint Tiêu Chuẩn)</span>
              </div>
              <p className="text-xs text-slate-400">
                Nhận diện ảnh + chat văn bản với Header <code className="text-slate-300">X-API-Key</code>
              </p>
            </div>
            <button
              onClick={() => copyCode('http://localhost:5678/webhook/antigravity-chat', 'ep-chat', 'URL')}
              className="text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1 bg-slate-800 rounded-lg"
            >
              Copy URL
            </button>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 text-xs font-bold rounded bg-blue-500/20 text-blue-400">POST</span>
                <code className="text-sm font-semibold text-slate-200">/v1/chat</code>
                <span className="text-xs text-slate-400">(Endpoint chuẩn REST)</span>
              </div>
              <p className="text-xs text-slate-400">
                Hỗ trợ đầy đủ tham số model, prompt, image, thinking, temperature...
              </p>
            </div>
            <button
              onClick={() => copyCode('http://localhost:5678/v1/chat', 'ep-v1', 'URL')}
              className="text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1 bg-slate-800 rounded-lg"
            >
              Copy URL
            </button>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 text-xs font-bold rounded bg-pink-500/20 text-pink-400">POST</span>
                <code className="text-sm font-semibold text-slate-200">/api/image/generate</code>
                <span className="text-xs text-pink-400 font-medium">(Tạo Ảnh Nghệ Thuật AI)</span>
              </div>
              <p className="text-xs text-slate-400">
                Tạo ảnh AI từ văn bản prompt, tỉ lệ khung hình (1:1, 16:9...), phong cách anime, cyberpunk...
              </p>
            </div>
            <button
              onClick={() => copyCode('http://localhost:5678/api/image/generate', 'ep-img', 'URL')}
              className="text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1 bg-slate-800 rounded-lg"
            >
              Copy URL
            </button>
          </div>
        </div>
      </div>

      {/* 4. Hướng Dẫn Chi Tiết Toàn Bộ Tham Số API (Docs v2.0) - Matches index.html lines 1064-1380 */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shadow">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white flex items-center space-x-2">
                <span>Hướng Dẫn Chi Tiết Toàn Bộ Tham Số API</span>
                <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Docs v2.0
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Bảng tra cứu đầy đủ kiểu dữ liệu, giá trị mặc định và cách sử dụng từng tham số gửi vào <code className="text-blue-400 font-mono">/webhook/antigravity-chat</code> hoặc <code className="text-blue-400 font-mono">/v1/chat</code>
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleDownloadDocsMarkdown}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-emerald-600/20 border border-emerald-500/30 active:scale-95"
              title="Tải toàn bộ tài liệu Markdown cho AI"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>📥 Tải Docs .MD Cho AI</span>
            </button>
            <button
              onClick={() => copyCode(fullJsonTemplate, 'full-json', 'JSON Template')}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition shadow-lg shadow-indigo-600/20 active:scale-95"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>📋 Copy JSON Mẫu Đầy Đủ</span>
            </button>
          </div>
        </div>

        {/* 1. HTTP REQUEST HEADERS */}
        <div className="space-y-2.5">
          <div className="flex items-center space-x-2 text-xs font-bold text-blue-400 uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            <span>1. HTTP Request Headers (Bắt buộc)</span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4 w-44">Tên Header</th>
                  <th className="py-2.5 px-3 w-28">Trạng thái</th>
                  <th className="py-2.5 px-4 w-52">Giá trị mẫu</th>
                  <th className="py-2.5 px-4">Ý nghĩa & Hướng dẫn sử dụng</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-blue-400 font-bold">Content-Type</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-[10px] font-bold">
                      Bắt buộc
                    </span>
                  </td>
                  <td className="py-2.5 px-4 font-mono text-slate-300 text-[11px]">application/json</td>
                  <td className="py-2.5 px-4 text-slate-400">Định dạng nội dung gửi lên bắt buộc là JSON payload.</td>
                </tr>
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-purple-300 font-bold">X-API-Key</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-[10px] font-bold">
                      Bắt buộc
                    </span>
                  </td>
                  <td className="py-2.5 px-4 font-mono text-amber-300 text-[11px] truncate max-w-[200px]">sk-antigravity-...</td>
                  <td className="py-2.5 px-4 text-slate-400">
                    Khóa bí mật dùng để xác thực quyền truy cập API Gateway (hoặc gửi qua header <code className="text-slate-200 font-mono">Authorization: Bearer &lt;key&gt;</code>).
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 2. JSON BODY PARAMETERS TABLE */}
        <div className="space-y-2.5">
          <div className="flex items-center space-x-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>2. Danh Sách Tham Số Body (JSON Payload)</span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 w-44">Tham số</th>
                  <th className="py-3 px-3 w-28">Kiểu dữ liệu</th>
                  <th className="py-3 px-3 w-36">Mặc định</th>
                  <th className="py-3 px-4">Mô tả chi tiết & Ví dụ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                {/* prompt */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">prompt</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px] font-mono">string</span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 italic">null</td>
                  <td className="py-3 px-4 space-y-1">
                    <div className="text-slate-200 font-medium">Câu hỏi, lệnh hoặc chỉ dẫn trực tiếp cho AI.</div>
                    <div className="text-[11px] text-slate-400">
                      Ví dụ: <code className="text-slate-200 bg-slate-900 px-1.5 py-0.5 rounded font-mono">"Phân tích tài liệu này và tóm tắt thành 3 ý chính"</code>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      Ghi chú: Có thể bỏ qua nếu bạn đã gửi kèm toàn bộ tin nhắn trong mảng <code className="text-slate-300 font-mono">messages</code>.
                    </div>
                  </td>
                </tr>

                {/* model */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">model</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px] font-mono">string</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-300">gemini-3.8-flash-tiered</td>
                  <td className="py-3 px-4 space-y-1.5">
                    <div className="text-slate-200 font-medium">Lựa chọn mô hình AI xử lý:</div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-1 text-[11px] font-mono text-slate-300">
                      <div>• <code className="text-fuchsia-300">gemini-4-argon</code> (Suy luận nâng cao)</div>
                      <div>• <code className="text-blue-300">gemini-3.8-flash-tiered</code> (Nhanh & Mới Nhất)</div>
                      <div>• <code className="text-blue-300">gemini-3.7-flash</code>, <code className="text-blue-300">gemini-3.6-flash</code></div>
                      <div>• <code className="text-blue-300">gemini-3.1-pro-high</code> (Tư duy sâu)</div>
                      <div>• <code className="text-purple-300">claude-sonnet-4-6</code>, <code className="text-purple-300">claude-opus-4-6-thinking</code></div>
                      <div>• <code className="text-emerald-300">gpt-oss-120b</code> (Mã nguồn mở)</div>
                      <div>• <code className="text-pink-300">flux-image-generator</code> (Vẽ ảnh nghệ thuật)</div>
                    </div>
                  </td>
                </tr>

                {/* messages */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">messages</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[10px] font-mono">array[obj]</span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 italic">[]</td>
                  <td className="py-3 px-4 space-y-1">
                    <div className="text-slate-200 font-medium">Mảng các lượt hội thoại lịch sử giúp AI nhớ ngữ cảnh trò chuyện:</div>
                    <div className="text-[11px] text-slate-400 font-mono bg-slate-900/80 p-2 rounded-lg border border-slate-800">
                      [&#123; "role": "user", "content": "..." &#125;, &#123; "role": "assistant", "content": "..." &#125;]
                    </div>
                  </td>
                </tr>

                {/* skill_id */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-purple-400">skill_id</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px] font-mono">string</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-300">không bắt buộc</td>
                  <td className="py-3 px-4 space-y-1">
                    <div className="text-slate-200 font-medium">Skill ID của kỹ năng Viết content riêng tư:</div>
                    <div className="text-[11px] text-slate-400">
                      Tài khoản sở hữu có thể truyền Skill ID riêng tư của mình; tài khoản khác không thể sử dụng ID đó.
                    </div>
                  </td>
                </tr>

                {/* web_search */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">web_search</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 text-[10px] font-mono">boolean</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-emerald-400">true</td>
                  <td className="py-3 px-4 text-slate-400">
                    Bật/tắt tính năng Google Search Grounding để tra cứu thông tin thời gian thực mới nhất trên internet.
                  </td>
                </tr>

                {/* thinking */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-amber-400">thinking</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 text-[10px] font-mono">boolean</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-400">false</td>
                  <td className="py-3 px-4 text-slate-400">
                    Bật/tắt chế độ suy luận mở rộng (Thinking mode) cho Claude & Gemini để giải quyết bài toán phức tạp hoặc lập trình chuyên sâu.
                  </td>
                </tr>

                {/* image */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-pink-400">image</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px] font-mono">string</span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 italic">null</td>
                  <td className="py-3 px-4 text-slate-400">
                    Dữ liệu hình ảnh Base64 (hoặc URL công khai) để AI nhận diện và phân tích thị giác đa phương thức (Multimodal Vision).
                  </td>
                </tr>

                {/* files */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">files</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 text-[10px] font-mono">array[obj]</span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 italic">[]</td>
                  <td className="py-3 px-4 text-slate-400">
                    Mảng các tài liệu đính kèm dạng <code className="text-slate-200 font-mono bg-slate-900 px-1 rounded">[&#123; "filename": "doc.txt", "data": "base64..." &#125;]</code>.
                  </td>
                </tr>

                {/* temperature */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">temperature</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 text-[10px] font-mono">number</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-300">0.7</td>
                  <td className="py-3 px-4 text-slate-400">
                    Độ ngẫu nhiên/sáng tạo của phản hồi (từ <code className="text-slate-200 font-mono">0.0</code> chính xác nhất đến <code className="text-slate-200 font-mono">2.0</code> sáng tạo nhất).
                  </td>
                </tr>

                {/* stream */}
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-3 px-4 font-mono font-bold text-blue-400">stream</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 text-[10px] font-mono">boolean</span>
                  </td>
                  <td className="py-3 px-3 font-mono text-[11px] text-slate-400">false</td>
                  <td className="py-3 px-4 text-slate-400">
                    Bật truyền dữ liệu Server-Sent Events (SSE) để nhận từng token trả lời theo thời gian thực.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 3. JSON RESPONSE STRUCTURE */}
        <div className="space-y-2.5">
          <div className="flex items-center space-x-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            <span>3. Cấu Trúc Dữ Liệu Phản Hồi (JSON Response Payload)</span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-4 w-44">Trường dữ liệu</th>
                  <th className="py-2.5 px-3 w-28">Kiểu dữ liệu</th>
                  <th className="py-2.5 px-4">Ý nghĩa & Hướng dẫn sử dụng</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70 text-slate-300">
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-emerald-400 font-bold">response / text</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-blue-300">string</td>
                  <td className="py-2.5 px-4 text-slate-400">Nội dung câu trả lời đầy đủ của AI định dạng Markdown phong phú.</td>
                </tr>
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-blue-400 font-bold">model</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-blue-300">string</td>
                  <td className="py-2.5 px-4 text-slate-400">Tên mô hình AI thực tế đã sinh phản hồi (ví dụ: gemini-3.8-flash-tiered).</td>
                </tr>
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-purple-400 font-bold">skill_used</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-blue-300">string | null</td>
                  <td className="py-2.5 px-4 text-slate-400">Tên kỹ năng đã kích hoạt trong request (nếu có truyền <code className="font-mono text-purple-300">skill_id</code>).</td>
                </tr>
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-indigo-400 font-bold">account_used</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-blue-300">string</td>
                  <td className="py-2.5 px-4 text-slate-400">Email tài khoản Google Antigravity đã nhận và phục vụ request này.</td>
                </tr>
                <tr className="hover:bg-slate-900/40 transition">
                  <td className="py-2.5 px-4 font-mono text-amber-400 font-bold">blocks</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-emerald-300">array[obj] | null</td>
                  <td className="py-2.5 px-4 text-slate-400">
                    Mảng các khối nội dung cấu trúc (Text, Code, Table, Quote, Alert, Math, Steps, Chart...) dùng cho render giao diện nâng cao.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 5. Code Mẫu Gọi API Áp Dụng Bộ Kỹ Năng (Skill ID) - Matches index.html lines 1382-1555 */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-5">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
            <Code2 className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-base text-white">Code mẫu gọi API với skill Viết content riêng tư</h3>
            <p className="text-xs text-slate-400">
              Chỉ tài khoản sở hữu mới có thể truyền Skill ID riêng tư để áp dụng kỹ năng này.
            </p>
          </div>
        </div>

        {/* Python Skill ID Example */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
              <span>🐍</span>
              <span>Python (requests)</span>
            </span>
            <button
              onClick={() => copyCode(pythonSkillExample, 'py-skill', 'Python code')}
              className="text-slate-400 hover:text-white flex items-center space-x-1 px-2 py-1 bg-slate-800 rounded-lg transition"
            >
              {copiedCodeId === 'py-skill' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>Copy code</span>
            </button>
          </div>
          <pre className="bg-slate-950 p-4 rounded-xl text-xs text-slate-300 font-mono overflow-x-auto border border-slate-800 leading-relaxed">
            {pythonSkillExample}
          </pre>
        </div>

        {/* cURL Skill ID Example */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
              <span>⚡</span>
              <span>cURL (Terminal / Bash)</span>
            </span>
            <button
              onClick={() => copyCode(curlSkillExample, 'curl-skill', 'cURL command')}
              className="text-slate-400 hover:text-white flex items-center space-x-1 px-2 py-1 bg-slate-800 rounded-lg transition"
            >
              {copiedCodeId === 'curl-skill' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>Copy code</span>
            </button>
          </div>
          <pre className="bg-slate-950 p-4 rounded-xl text-xs text-slate-300 font-mono overflow-x-auto border border-slate-800 leading-relaxed">
            {curlSkillExample}
          </pre>
        </div>

        {/* Multi-turn Context Session Example */}
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
              <span>🧠</span>
              <span className="text-blue-300 font-bold">Code Mẫu Python Hội Thoại Đa Lượt (Stateless - Gửi Kèm Messages)</span>
            </span>
            <button
              onClick={() => copyCode(pythonSessionExample, 'py-sess', 'Python Session code')}
              className="text-slate-400 hover:text-white flex items-center space-x-1 px-2 py-1 bg-slate-800 rounded-lg transition"
            >
              {copiedCodeId === 'py-sess' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>Copy code</span>
            </button>
          </div>
          <p className="text-xs text-slate-400">
            Máy chủ tuân thủ chuẩn <b>Stateless</b> (không lưu trữ tin nhắn trên server nhằm đảm bảo quyền riêng tư). Client lưu lịch sử vào file <code className="text-blue-300 font-mono">chat_history.json</code> trên máy mình, đọc ra và gửi kèm trong mỗi request để AI nhớ ngữ cảnh:
          </p>
          <pre className="bg-slate-950 p-4 rounded-xl text-xs text-slate-300 font-mono overflow-x-auto border border-slate-800 leading-relaxed">
            {pythonSessionExample}
          </pre>
        </div>

        {/* Multimodal Vision Example */}
        <div className="space-y-2 pt-2 border-t border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
              <span>👁️</span>
              <span className="text-pink-300 font-bold">Code Mẫu Python Phân Tích Hình Ảnh (Multimodal Vision)</span>
            </span>
            <button
              onClick={() => copyCode(pythonVisionExample, 'py-vision', 'Python Vision code')}
              className="text-slate-400 hover:text-white flex items-center space-x-1 px-2 py-1 bg-slate-800 rounded-lg transition"
            >
              {copiedCodeId === 'py-vision' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>Copy code</span>
            </button>
          </div>
          <pre className="bg-slate-950 p-4 rounded-xl text-xs text-slate-300 font-mono overflow-x-auto border border-slate-800 leading-relaxed">
            {pythonVisionExample}
          </pre>
        </div>
      </div>

      {/* 6. Cài Đặt Hệ Thống (Nếu là Admin) */}
      {isAdmin && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 space-y-4">
          <SettingsTab />
        </div>
      )}
    </div>
  );
};
