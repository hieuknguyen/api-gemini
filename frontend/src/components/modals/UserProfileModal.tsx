import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { X, User, Key, LogOut, Copy, Check, Shield, Coins, CreditCard } from 'lucide-react';

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenPayment?: () => void;
}

export const UserProfileModal: React.FC<UserProfileModalProps> = ({ isOpen, onClose, onOpenPayment }) => {
  const { user, token, logout } = useAuth();
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);

  if (!isOpen || !user) return null;

  const handleCopyKey = () => {
    if (!token) return;
    navigator.clipboard.writeText(token);
    setCopied(true);
    showToast('Đã sao chép API Key vào clipboard!', 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleLogout = () => {
    logout();
    onClose();
    showToast('Đã đăng xuất tài khoản!', 'info');
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-6 max-w-md w-full shadow-2xl relative overflow-hidden backdrop-blur-xl space-y-5">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-purple-500 via-indigo-500 to-purple-500"></div>

        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/25 text-purple-400 flex items-center justify-center">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">{user.name}</h3>
              <p className="text-xs text-slate-400">{user.email || 'Tài khoản hệ thống'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800">
            <span className="text-slate-400">Vai trò tài khoản:</span>
            <span className={`px-2 py-0.5 rounded font-bold border uppercase text-[10px] ${
              user.role === 'admin'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
            }`}>
              <Shield className="w-3 h-3 inline-block mr-1" />
              {user.role}
            </span>
          </div>

          {/* Token Balance & Top-up Card */}
          <div className="p-3.5 rounded-xl bg-gradient-to-br from-pink-950/30 via-slate-950/70 to-purple-950/30 border border-pink-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Coins className="w-4 h-4 text-pink-400" />
                <span className="font-bold text-slate-200">Số Dư Token AI</span>
              </div>
              <span className="font-mono font-bold text-pink-300 text-sm">
                {user.role === 'admin' ? 'Không giới hạn (Admin)' : `${(user.token_balance ?? 0).toLocaleString('vi-VN')} tokens`}
              </span>
            </div>

            {user.role !== 'admin' && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  if (onOpenPayment) onOpenPayment();
                }}
                className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-pink-600 via-rose-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white font-bold text-xs flex items-center justify-center space-x-1.5 shadow-md shadow-pink-600/20 transition active:scale-95"
              >
                <CreditCard className="w-3.5 h-3.5" />
                <span>Nạp Thêm Token Qua MoMo (Quét Mã QR)</span>
              </button>
            )}
          </div>

          <div className="space-y-1.5 p-3.5 rounded-xl bg-slate-950/70 border border-purple-500/20">
            <div className="flex items-center justify-between">
              <label className="text-purple-300 font-medium flex items-center space-x-1.5">
                <Key className="w-3.5 h-3.5 text-purple-400" />
                <span>API Key hiện tại của bạn:</span>
              </label>
              <button
                type="button"
                onClick={handleCopyKey}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-600 text-purple-300 hover:text-white transition text-xs font-medium border border-purple-500/20 active:scale-95"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
              </button>
            </div>
            <input
              type="text"
              readOnly
              value={token || ''}
              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 font-mono text-xs text-purple-200 select-all cursor-text focus:outline-none"
            />
            <p className="text-[11px] text-slate-400">
              Gửi header: <code className="text-purple-300 font-mono">Authorization: Bearer sk-antigravity-...</code>
            </p>
          </div>
        </div>

        <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-600 text-rose-300 hover:text-white transition text-xs font-semibold border border-rose-500/20 active:scale-95"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Đăng xuất</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
