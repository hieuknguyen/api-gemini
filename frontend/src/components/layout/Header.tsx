import React from 'react';
import { TabType } from '../../types';
import { useAuth } from '../../context/AuthContext';
import {
  MessageSquare,
  Palette,
  Sparkles,
  Users,
  Code2,
  LogIn,
  LogOut,
  ExternalLink,
  Shield,
  Coins
} from 'lucide-react';

interface HeaderProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  skillsCount: number;
  accountsCount: number;
  onOpenProfile: () => void;
  onOpenPayment: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  skillsCount,
  accountsCount,
  onOpenProfile,
  onOpenPayment,
}) => {
  const { user, isAuthenticated, isAdmin, openAuthModal, logout } = useAuth();

  const navItems = [
    { id: 'chat' as TabType, label: 'Chat & Vision', icon: MessageSquare, iconColor: 'text-blue-400' },
    { id: 'images' as TabType, label: 'Tạo Ảnh AI', icon: Palette, iconColor: 'text-pink-400' },
    { id: 'skills' as TabType, label: 'Bộ Kỹ Năng', icon: Sparkles, iconColor: 'text-purple-400', count: skillsCount },
    ...(isAdmin ? [{
      id: 'accounts' as TabType,
      label: 'Tài Khoản',
      icon: Users,
      iconColor: 'text-blue-400',
      count: accountsCount,
      adminBadge: true
    }] : []),
    { id: 'api' as TabType, label: 'API & Cài Đặt', icon: Code2, iconColor: 'text-slate-400' },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur shrink-0 z-40 px-4 lg:px-6 py-2.5 flex items-center justify-between">
      {/* Brand Logo */}
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="font-bold text-lg tracking-tight text-white">Antigravity Gateway</h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              FastAPI
            </span>
          </div>
          <p className="text-xs text-slate-400">Gemini 3.8 / 3.0 / 2.5 Multimodal Proxy</p>
        </div>
      </div>

      {/* Tabs */}
      <nav className="flex items-center space-x-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800 text-sm">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg font-medium transition ${
                isActive
                  ? 'text-white bg-blue-600 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-white' : item.iconColor}`} />
              <span>{item.label}</span>
              {item.count !== undefined && item.count > 0 && (
                <span className="px-1.5 py-0.2 bg-slate-800 rounded-full text-xs text-purple-400 font-bold">
                  {item.count}
                </span>
              )}
              {item.adminBadge && (
                <span className="px-1.5 py-0.2 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-[10px] font-bold">
                  Admin
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Actions & Badges */}
      <div className="flex items-center space-x-2 sm:space-x-3">
        {isAuthenticated && user ? (
          <>
            {user.role === 'user' ? (
              <button
                onClick={onOpenPayment}
                className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-gradient-to-r from-pink-600/20 to-purple-600/20 hover:from-pink-600/30 hover:to-purple-600/30 text-pink-300 border border-pink-500/30 rounded-xl text-xs font-semibold transition shadow-sm active:scale-95"
                title="Nạp thêm Token qua MoMo"
              >
                <Coins className="w-3.5 h-3.5 text-pink-400" />
                <span className="font-mono">{(user.token_balance ?? 0).toLocaleString('vi-VN')}</span>
                <span className="bg-pink-500 text-white rounded px-1 py-0.2 text-[9px] font-bold uppercase">Nạp</span>
              </button>
            ) : (
              <button
                onClick={onOpenPayment}
                className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 rounded-xl text-xs text-amber-300 font-medium transition"
                title="Quản lý giao dịch nạp MoMo"
              >
                <Coins className="w-3.5 h-3.5 text-amber-400" />
                <span className="font-bold">Tokens: ∞</span>
              </button>
            )}

            <button
              onClick={onOpenProfile}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold shadow-sm bg-slate-800/60 border border-slate-700 hover:border-slate-600 text-slate-200"
            >
              <span className="text-sm">👤</span>
              <span className="truncate max-w-[120px]">{user.name}</span>
              {user.role === 'admin' && (
                <span className="px-1 py-0.2 bg-amber-500/20 text-amber-300 rounded text-[9px] font-bold">
                  ADMIN
                </span>
              )}
            </button>

            <button
              onClick={logout}
              className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 rounded-xl text-xs font-medium transition shadow-sm"
              title="Đăng xuất khỏi tài khoản"
            >
              <LogOut className="w-3.5 h-3.5 text-rose-400" />
              <span className="hidden sm:inline">Đăng xuất</span>
            </button>
          </>
        ) : (
          <button
            onClick={() => openAuthModal('login')}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-xl text-xs font-semibold transition shadow-sm"
            title="Đăng nhập tài khoản"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Đăng nhập</span>
          </button>
        )}

        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="hidden md:flex text-xs text-slate-400 hover:text-slate-200 items-center space-x-1 border border-slate-800 px-2.5 py-1.5 rounded-xl bg-slate-900"
        >
          <span>Docs</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </header>
  );
};
