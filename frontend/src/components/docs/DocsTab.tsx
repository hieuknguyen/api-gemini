import React, { useState } from 'react';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import {
  BookOpen,
  Code2,
  Copy,
  Check,
  FileDown,
  Terminal,
  ExternalLink,
  Cpu
} from 'lucide-react';

export const DocsTab: React.FC = () => {
  const { showToast } = useToast();
  const { token } = useAuth();
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const activeKey = token || 'sk-antigravity-your-api-key';

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedSection(id);
    showToast('Đã sao chép đoạn code vào clipboard!', 'success');
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const pythonExample = `import requests

url = "http://localhost:5678/webhook/antigravity-chat"
headers = {
    "Authorization": "Bearer ${activeKey}",
    "Content-Type": "application/json"
}
payload = {
    "prompt": "Viết bài phân tích chuyên sâu về thị trường AI năm 2026",
    "model": "gemini-2.5-flash",
    "web_search": True,
    "thinking": False
}

response = requests.post(url, headers=headers, json=payload)
data = response.json()
print("AI Response:", data.get("response"))
print("Skill Activated:", data.get("skill_used"))`;

  const curlExample = `curl -X POST "http://localhost:5678/webhook/antigravity-chat" \\
  -H "Authorization: Bearer ${activeKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "prompt": "Xin chào, hãy giới thiệu ngắn gọn về năng lực của bạn",
    "model": "gemini-2.5-flash",
    "web_search": true
  }'`;

  const jsExample = `const res = await fetch("http://localhost:5678/webhook/antigravity-chat", {
  method: "POST",
  headers: {
    "Authorization": "Bearer ${activeKey}",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    prompt: "Tối ưu đoạn mã sau chuẩn clean code...",
    model: "gemini-2.5-flash",
  })
});

const data = await res.json();
console.log(data.response);`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-5 rounded-2xl">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-purple-400" />
            <span>Tài Liệu Kỹ Thuật & Tích Hợp API Gateway</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Kết nối mọi ứng dụng, chatbot, AI agent hoặc hệ thống ngoài tới cụm Antigravity Gateway.
          </p>
        </div>

        <a
          href="/api/docs/markdown"
          target="_blank"
          rel="noreferrer"
          className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-purple-600/20 transition active:scale-95 shrink-0"
        >
          <FileDown className="w-4 h-4" />
          <span>Tải Tài Liệu Markdown (.md)</span>
        </a>
      </div>

      {/* Endpoints overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-bold text-sm text-white">
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px]">
              POST
            </span>
            <code className="text-purple-300">/webhook/antigravity-chat</code>
          </div>
          <p className="text-slate-400 leading-relaxed">
            Endpoint cốt lõi tương thích webhook, nhận prompt, lịch sử hội thoại, ảnh base64, file đính kèm và mã Skill ID.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2 text-xs">
          <div className="flex items-center space-x-2 font-bold text-sm text-white">
            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono text-[10px]">
              POST
            </span>
            <code className="text-purple-300">/api/image/generate</code>
          </div>
          <p className="text-slate-400 leading-relaxed">
            Sinh ảnh nghệ thuật chất lượng cao theo prompt, phong cách (anime, cyberpunk, 3d...), tỉ lệ khung hình (1:1, 16:9...).
          </p>
        </div>
      </div>

      {/* Code Examples */}
      <div className="space-y-4">
        {/* Python */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
          <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs font-semibold text-slate-300">
            <div className="flex items-center space-x-2">
              <Code2 className="w-4 h-4 text-purple-400" />
              <span>Python (requests)</span>
            </div>
            <button
              onClick={() => copyCode(pythonExample, 'py')}
              className="flex items-center space-x-1 text-slate-400 hover:text-white transition"
            >
              {copiedSection === 'py' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedSection === 'py' ? 'Đã sao chép' : 'Sao chép'}</span>
            </button>
          </div>
          <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed bg-slate-950/60">
            {pythonExample}
          </pre>
        </div>

        {/* cURL */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
          <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs font-semibold text-slate-300">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-purple-400" />
              <span>cURL (Terminal / Bash)</span>
            </div>
            <button
              onClick={() => copyCode(curlExample, 'curl')}
              className="flex items-center space-x-1 text-slate-400 hover:text-white transition"
            >
              {copiedSection === 'curl' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedSection === 'curl' ? 'Đã sao chép' : 'Sao chép'}</span>
            </button>
          </div>
          <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed bg-slate-950/60">
            {curlExample}
          </pre>
        </div>

        {/* JavaScript */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
          <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 text-xs font-semibold text-slate-300">
            <div className="flex items-center space-x-2">
              <Code2 className="w-4 h-4 text-purple-400" />
              <span>JavaScript / Node.js (fetch)</span>
            </div>
            <button
              onClick={() => copyCode(jsExample, 'js')}
              className="flex items-center space-x-1 text-slate-400 hover:text-white transition"
            >
              {copiedSection === 'js' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedSection === 'js' ? 'Đã sao chép' : 'Sao chép'}</span>
            </button>
          </div>
          <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed bg-slate-950/60">
            {jsExample}
          </pre>
        </div>
      </div>
    </div>
  );
};
