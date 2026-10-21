import React, { useState, useEffect } from 'react';
import { Skill } from '../../types';
import { skillService } from '../../services/skillService';
import { useToast } from '../../context/ToastContext';
import { X, Sparkles, Key, Copy, Check, Save, Loader2 } from 'lucide-react';

interface SkillModalProps {
  isOpen: boolean;
  onClose: () => void;
  skill?: Skill | null;
  onSaved: () => void;
}

export const SkillModal: React.FC<SkillModalProps> = ({ isOpen, onClose, skill, onSaved }) => {
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (skill) {
      setName(skill.name || '');
      setPrompt(skill.system_prompt || '');
    } else {
      setName('');
      setPrompt('');
    }
  }, [skill, isOpen]);

  if (!isOpen) return null;

  const handleCopyId = () => {
    if (!skill?.id) return;
    navigator.clipboard.writeText(skill.id);
    setCopied(true);
    showToast('Đã sao chép Skill ID vào clipboard!', 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!skill) return;
    if (!name.trim()) {
      showToast('Vui lòng nhập tên kỹ năng!', 'error');
      return;
    }
    if (!prompt.trim()) {
      showToast('Vui lòng nhập chỉ dẫn hệ thống (System Prompt)!', 'error');
      return;
    }

    setLoading(true);
    try {
      await skillService.updateSkill(skill.id, prompt.trim());
      showToast('Đã cập nhật kỹ năng thành công!', 'success');
      onSaved();
      onClose();
    } catch (err: any) {
      showToast(err.message || 'Lỗi khi lưu kỹ năng', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-6 max-w-xl w-full space-y-4 shadow-2xl shadow-purple-950/30 relative overflow-hidden backdrop-blur-xl">
        {/* Top subtle gradient accent */}
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-purple-500 via-indigo-500 to-purple-500"></div>

        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3.5 border-b border-slate-800">
          <div className="flex items-center space-x-3 min-w-0 pr-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/25 text-purple-400 flex items-center justify-center shadow-inner shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="font-bold text-base text-white tracking-tight">
                {skill ? 'Chỉnh Sửa Kỹ Năng' : 'Tạo Kỹ Năng Mới'}
              </h3>
              <p className="text-xs text-slate-400 truncate">
                Thiết lập vai trò và chỉ dẫn hệ thống chuyên sâu cho AI
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="px-3.5 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-purple-600/25 transition active:scale-95 flex items-center space-x-1.5 whitespace-nowrap disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang lưu...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Lưu</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/80 transition"
              title="Đóng"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Skill ID Bar (Visible when editing) */}
        {skill?.id && (
          <div className="bg-slate-950/70 border border-purple-500/20 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-purple-300 flex items-center space-x-1.5">
                <Key className="w-3.5 h-3.5 text-purple-400" />
                <span>Mã Định Danh API (Skill ID):</span>
              </label>
              <button
                type="button"
                onClick={handleCopyId}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-600 text-purple-300 hover:text-white transition text-xs font-medium border border-purple-500/20 active:scale-95 shadow-sm"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Đã chép' : 'Sao chép ID'}</span>
              </button>
            </div>
            <input
              type="text"
              readOnly
              value={skill.id}
              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 font-mono text-xs text-purple-200 select-all cursor-text focus:outline-none focus:border-purple-500/50"
            />
            <p className="text-[11px] text-slate-400">
              Dùng mã này khi gọi API: <code className="px-1.5 py-0.5 rounded bg-slate-900 border border-purple-500/20 text-purple-300 font-mono text-[11px]">{`{"prompt": "...", "skill_id": "${skill.id}"}`}</code>
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          {/* Tên kỹ năng */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">
              Tên kỹ năng <span className="text-purple-400 font-bold">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              readOnly={Boolean(skill)}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Viết content, Chuyên gia Python, Biên dịch viên..."
              className="w-full bg-slate-950/80 border border-slate-700/80 focus:border-purple-500 focus:ring-1 focus:ring-purple-500/40 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none transition"
            />
          </div>

          {/* Chỉ dẫn hệ thống (System Prompt) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-medium text-slate-300">
                Chỉ dẫn hệ thống (System Prompt) <span className="text-purple-400 font-bold">*</span>
              </label>
              <span className="text-[11px] text-slate-500">Quy định nguyên tắc & phong cách AI</span>
            </div>
            <textarea
              rows={12}
              required
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Bạn là chuyên gia về... Luôn tuân thủ các nguyên tắc sau: 1... 2... 3..."
              className="w-full bg-slate-950/80 border border-slate-700/80 focus:border-purple-500 focus:ring-1 focus:ring-purple-500/40 rounded-xl p-3.5 font-mono text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none transition leading-relaxed resize-y min-h-[160px]"
            />
          </div>
        </form>
      </div>
    </div>
  );
};
