import React, { useState, useEffect } from 'react';
import { GoogleAccount, QuotaOverviewResponse, AccountQuotaData } from '../../types';
import { accountService } from '../../services/accountService';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { apiRequest } from '../../services/apiClient';
import {
  Users,
  Plus,
  Key,
  Trash2,
  Power,
  RefreshCw,
  Star,
  CheckCircle,
  AlertTriangle,
  Clock,
  Shuffle,
  BarChart3,
  Filter,
  Loader2,
  ExternalLink,
  X,
  ShieldAlert,
  Calendar,
  CalendarRange,
  CalendarDays,
  Gauge,
  Sparkles,
  Cpu,
  Zap,
  Activity
} from 'lucide-react';

export const AccountsTab: React.FC = () => {
  const { isAdmin, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [accounts, setAccounts] = useState<GoogleAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [strategy, setStrategy] = useState('failover');
  const [filterAccount, setFilterAccount] = useState('');
  const [quotaStats, setQuotaStats] = useState<any>(null);
  const [loadingQuota, setLoadingQuota] = useState(false);

  // Realtime Quota từ Google API
  const [quotaOverview, setQuotaOverview] = useState<QuotaOverviewResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(false);

  // Manual token modal
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualToken, setManualToken] = useState('');
  const [manualName, setManualName] = useState('');
  const [submittingManual, setSubmittingManual] = useState(false);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const data = await accountService.getAccounts();
      setAccounts(data);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải danh sách tài khoản Google', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchQuotaStats = async (accId?: string) => {
    if (!isAdmin) return;
    try {
      setLoadingQuota(true);
      const url = accId ? `/api/quota/stats?account_id=${encodeURIComponent(accId)}` : '/api/quota/stats';
      const res = await apiRequest<any>(url);
      setQuotaStats(res);
    } catch (err: any) {
      // ignore
    } finally {
      setLoadingQuota(false);
    }
  };

  const fetchSettings = async () => {
    if (!isAdmin) return;
    try {
      const res = await apiRequest<any>('/api/settings');
      if (res?.strategy) setStrategy(res.strategy);
    } catch (err) {
      // ignore
    }
  };

  const fetchRealtimeQuota = async (force: boolean = false) => {
    if (!isAdmin) return;
    try {
      setLoadingOverview(true);
      const res = await accountService.getQuotaOverview(force);
      setQuotaOverview(res);
      if (force) {
        showToast('Đã cập nhật hạn ngạch Google Antigravity mới nhất!', 'success');
      }
    } catch (err: any) {
      if (force) {
        showToast(err.message || 'Lỗi cập nhật hạn ngạch Google', 'error');
      }
    } finally {
      setLoadingOverview(false);
    }
  };

  const formatResetTime = (isoString?: string | null) => {
    if (!isoString) return null;
    try {
      const d = new Date(isoString);
      const now = new Date();
      const diffMs = d.getTime() - now.getTime();
      const diffMin = Math.round(diffMs / 60000);
      if (diffMin <= 0) return 'Đang reset...';
      if (diffMin < 60) return `Reset sau ~${diffMin}p`;
      const hours = Math.floor(diffMin / 60);
      const mins = diffMin % 60;
      return `Reset sau ~${hours}h${mins > 0 ? ` ${mins}p` : ''}`;
    } catch {
      return isoString;
    }
  };

  const getQuotaColor = (usedPercent: number) => {
    if (usedPercent >= 90) return { bar: 'bg-red-500', text: 'text-red-400', border: 'border-red-500/30', bg: 'bg-red-500/10' };
    if (usedPercent >= 70) return { bar: 'bg-amber-500', text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' };
    return { bar: 'bg-emerald-500', text: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' };
  };

  useEffect(() => {
    fetchAccounts();
    if (isAdmin) {
      fetchQuotaStats();
      fetchRealtimeQuota();
      fetchSettings();
    }
  }, [isAdmin]);

  const handleStrategyChange = async (newStrategy: string) => {
    setStrategy(newStrategy);
    try {
      await apiRequest('/api/settings', {
        method: 'POST',
        body: JSON.stringify({ strategy: newStrategy }),
      });
      showToast(`Đã lưu chiến lược: ${newStrategy === 'round_robin' ? 'Round-Robin' : 'Failover'}`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu chiến lược', 'error');
    }
  };

  const handleOAuthStart = async () => {
    try {
      const res = await accountService.startOAuth();
      const targetUrl = res?.url || (res as any)?.auth_url;
      if (targetUrl) {
        const w = window.open(targetUrl, '_blank', 'width=550,height=680');
        showToast('Đang mở trang đăng nhập Google... Sau khi cấp quyền xong hệ thống sẽ tự nạp tài khoản.', 'info');

        // Polling tự động làm mới danh sách tài khoản
        const pollTimer = setInterval(async () => {
          await fetchAccounts();
          if (w && w.closed) {
            clearInterval(pollTimer);
            await fetchAccounts();
          }
        }, 2000);

        // Giới hạn thời gian polling tối đa 2 phút
        setTimeout(() => clearInterval(pollTimer), 120000);
      } else {
        showToast('Không nhận được đường dẫn xác thực từ máy chủ', 'error');
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi khởi chạy Google OAuth', 'error');
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualToken.trim()) return;

    setSubmittingManual(true);
    try {
      await accountService.addManualAccount(manualToken.trim(), manualName.trim() || undefined);
      showToast('Đã thêm tài khoản Google thành công!', 'success');
      setIsManualModalOpen(false);
      setManualToken('');
      setManualName('');
      fetchAccounts();
    } catch (err: any) {
      showToast(err.message || 'Lỗi thêm tài khoản thủ công', 'error');
    } finally {
      setSubmittingManual(false);
    }
  };

  const handleToggle = async (account: GoogleAccount) => {
    try {
      await accountService.toggleAccount(account.id);
      showToast(`Đã ${account.is_active ? 'tắt' : 'bật'} tài khoản ${account.email}`, 'info');
      fetchAccounts();
    } catch (err: any) {
      showToast(err.message || 'Lỗi thay đổi trạng thái', 'error');
    }
  };

  const handleTest = async (id: string) => {
    try {
      showToast('Đang kiểm tra kết nối tài khoản...', 'info');
      const res = await accountService.testAccount(id);
      showToast(res.message || 'Tài khoản hoạt động rất tốt!', 'success');
      fetchAccounts();
    } catch (err: any) {
      showToast(err.message || 'Kiểm tra tài khoản thất bại', 'error');
    }
  };

  const handleSetPrimary = async (id: string) => {
    try {
      await accountService.setPrimary(id);
      showToast('Đã đặt làm tài khoản ưu tiên!', 'success');
      fetchAccounts();
    } catch (err: any) {
      showToast(err.message || 'Lỗi đặt tài khoản ưu tiên', 'error');
    }
  };

  const handleDelete = async (account: GoogleAccount) => {
    if (!window.confirm(`Bạn có chắc muốn gỡ tài khoản ${account.email}?`)) return;
    try {
      await accountService.deleteAccount(account.id);
      showToast(`Đã gỡ tài khoản ${account.email}`, 'success');
      fetchAccounts();
    } catch (err: any) {
      showToast(err.message || 'Lỗi gỡ tài khoản', 'error');
    }
  };

  const formatNumber = (num: number = 0) => {
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'k';
    return num.toLocaleString();
  };

  if (!isAdmin) {
    return null;
  }

  const readyCount = accounts.filter((a) => a.is_active).length;
  const limitedCount = accounts.filter((a) => (a as any).is_rate_limited).length;

  return (
    <div className="flex flex-col gap-6 overflow-y-auto pr-1 pb-8">
      {/* 1. Stats Cards (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tổng tài khoản */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase">Tổng Tài Khoản</span>
            <Users className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">{accounts.length}</div>
          <p className="text-xs text-slate-500 mt-1">Trong nhóm phân phối</p>
        </div>

        {/* Sẵn sàng */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase">Sẵn Sàng</span>
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">{readyCount}</div>
          <p className="text-xs text-slate-500 mt-1">Đang hoạt động & còn quota</p>
        </div>

        {/* Rate Limited */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase">Rate Limited</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{limitedCount}</div>
          <p className="text-xs text-slate-500 mt-1">Tạm chờ hồi phục quota</p>
        </div>

        {/* Chiến Lược */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase">Chiến Lược</span>
            <Shuffle className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-center space-x-2 mt-1">
            <select
              value={strategy}
              onChange={(e) => handleStrategyChange(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-xs rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none w-full cursor-pointer hover:border-indigo-500 transition font-medium"
            >
              <option value="failover">Failover (Ưu tiên dự phòng)</option>
              <option value="round_robin">Round-Robin (Chia đều tải)</option>
            </select>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {strategy === 'round_robin'
              ? 'Luân phiên chia đều lượt gọi giữa các tài khoản'
              : 'Ưu tiên tài khoản chính, tự đổi khi dính 429'}
          </p>
        </div>
      </div>

      {/* 2. Quota Usage Dashboard (Theo Giờ, Ngày, Tuần, Tháng) */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shadow-sm">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-base text-white">Tổng Số Quota Đã Dùng</h3>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                  Realtime
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Theo dõi chi tiết số lượt gọi (Requests) & Lượng Tokens đã tiêu thụ
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Account Filter */}
            <div className="flex items-center space-x-1.5 bg-slate-950 px-2.5 py-1.5 rounded-xl border border-slate-700 text-xs">
              <Filter className="w-3.5 h-3.5 text-blue-400" />
              <select
                value={filterAccount}
                onChange={(e) => {
                  setFilterAccount(e.target.value);
                  fetchQuotaStats(e.target.value);
                }}
                className="bg-slate-950 text-slate-100 font-medium focus:outline-none cursor-pointer pr-1"
              >
                <option value="">Toàn bộ tài khoản (Tất cả)</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name || a.email}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => fetchQuotaStats(filterAccount)}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs transition flex items-center space-x-1 px-2.5 border border-slate-700"
              title="Làm mới thống kê"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingQuota ? 'animate-spin text-blue-400' : ''}`} />
              <span className="hidden sm:inline">Làm mới</span>
            </button>
          </div>
        </div>

        {/* 4 Quota Cards Grid: Giờ, Ngày, Tuần, Tháng */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Theo Giờ */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 hover:border-slate-700 transition">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-sky-400" />
                <span>Theo Giờ</span>
              </span>
              <span className="px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 text-[10px] font-mono">1h qua</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-white font-mono">
                {(quotaStats?.hour?.requests || 0).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">requests</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 mt-2.5 pt-2 border-t border-slate-800/80">
              <span>Tokens:</span>
              <span className="font-semibold text-sky-400 font-mono">
                {formatNumber(quotaStats?.hour?.total_tokens || 0)}
              </span>
            </div>
          </div>

          {/* Theo Ngày */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 hover:border-slate-700 transition">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                <span>Theo Ngày</span>
              </span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono">24h qua</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-white font-mono">
                {(quotaStats?.day?.requests || 0).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">requests</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 mt-2.5 pt-2 border-t border-slate-800/80">
              <span>Tokens:</span>
              <span className="font-semibold text-emerald-400 font-mono">
                {formatNumber(quotaStats?.day?.total_tokens || 0)}
              </span>
            </div>
          </div>

          {/* Theo Tuần */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 hover:border-slate-700 transition">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                <CalendarRange className="w-3.5 h-3.5 text-purple-400" />
                <span>Theo Tuần</span>
              </span>
              <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 text-[10px] font-mono">7 ngày qua</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-white font-mono">
                {(quotaStats?.week?.requests || 0).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">requests</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 mt-2.5 pt-2 border-t border-slate-800/80">
              <span>Tokens:</span>
              <span className="font-semibold text-purple-400 font-mono">
                {formatNumber(quotaStats?.week?.total_tokens || 0)}
              </span>
            </div>
          </div>

          {/* Theo Tháng */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 hover:border-slate-700 transition">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                <CalendarDays className="w-3.5 h-3.5 text-amber-400" />
                <span>Theo Tháng</span>
              </span>
              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[10px] font-mono">30 ngày qua</span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-white font-mono">
                {(quotaStats?.month?.requests || 0).toLocaleString()}
              </span>
              <span className="text-xs text-slate-400">requests</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 mt-2.5 pt-2 border-t border-slate-800/80">
              <span>Tokens:</span>
              <span className="font-semibold text-amber-400 font-mono">
                {formatNumber(quotaStats?.month?.total_tokens || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2.5. Tổng Hạn Ngạch Google AI Toàn Hệ Thống (Aggregated Live Quota) */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center shadow-sm">
              <Gauge className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-base text-white">Tổng Hạn Ngạch Google AI Toàn Hệ Thống</h3>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>Live Quota</span>
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Tỷ lệ % hạn ngạch đã dùng và dung lượng khả dụng thời gian thực từ Google Cloud Code API
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => fetchRealtimeQuota(true)}
              disabled={loadingOverview}
              className="px-3.5 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-xl text-xs font-medium transition flex items-center space-x-1.5 disabled:opacity-50"
              title="Quét và cập nhật hạn ngạch tất cả tài khoản"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingOverview ? 'animate-spin text-indigo-400' : ''}`} />
              <span>{loadingOverview ? 'Đang quét...' : 'Làm mới Quota Realtime'}</span>
            </button>
          </div>
        </div>

        {/* 2 Big Quota Progress Meters: Gemini & Claude */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Gemini Overall Meter */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center border border-sky-500/20">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center space-x-1.5">
                    <span>Nhóm Gemini Models</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 font-mono">Flash / Pro</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Gemini 3.8 Flash, 3.1 Pro, 2.5 Pro</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-semibold text-slate-400">Đã sử dụng</div>
                <div className="text-xl font-bold font-mono text-sky-400">
                  {quotaOverview?.summary?.gemini?.avg_used_percent ?? 0}%
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="w-full bg-slate-800/80 rounded-full h-3 overflow-hidden p-0.5 border border-slate-700/50">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-sky-500 to-blue-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, quotaOverview?.summary?.gemini?.avg_used_percent ?? 0))}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Còn lại: <strong className="text-emerald-400">{quotaOverview?.summary?.gemini?.avg_remaining_percent ?? 100}%</strong></span>
                <span className="text-slate-500">Trung bình {accounts.length} tài khoản</span>
              </div>
            </div>
          </div>

          {/* Claude Overall Meter */}
          <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white flex items-center space-x-1.5">
                    <span>Nhóm Claude Models</span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">Sonnet / Opus</span>
                  </div>
                  <div className="text-[11px] text-slate-400">Claude Sonnet 4.6 Thinking, Opus 4.6</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-semibold text-slate-400">Đã sử dụng</div>
                <div className="text-xl font-bold font-mono text-purple-400">
                  {quotaOverview?.summary?.claude?.avg_used_percent ?? 0}%
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="w-full bg-slate-800/80 rounded-full h-3 overflow-hidden p-0.5 border border-slate-700/50">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, quotaOverview?.summary?.claude?.avg_used_percent ?? 0))}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Còn lại: <strong className="text-emerald-400">{quotaOverview?.summary?.claude?.avg_remaining_percent ?? 100}%</strong></span>
                <span className="text-slate-500">Trung bình {accounts.length} tài khoản</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60 text-xs">
          <div className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 flex items-center space-x-1.5 text-slate-300">
            <span className="text-slate-500">Tổng tài khoản:</span>
            <span className="font-bold text-white font-mono">{accounts.length}</span>
          </div>
          <div className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center space-x-1.5 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>Khỏe mạnh:</span>
            <span className="font-bold font-mono">{quotaOverview?.healthy_count ?? accounts.filter(a => a.is_active).length}</span>
          </div>
          {(quotaOverview?.exhausted_count || 0) > 0 && (
            <div className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center space-x-1.5 text-amber-400">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              <span>Cạn quota / 429:</span>
              <span className="font-bold font-mono">{quotaOverview?.exhausted_count}</span>
            </div>
          )}
        </div>
      </div>

      {/* 3. Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-4 border border-slate-800 rounded-2xl">
        <div>
          <h3 className="font-bold text-base text-white">Danh sách Google Antigravity Accounts</h3>
          <p className="text-xs text-slate-400">
            Hệ thống sẽ tự động chuyển tài khoản khác nếu gặp lỗi giới hạn (429 Rate Limit).
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleOAuthStart}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-blue-600/20 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Đăng nhập Google (1-Click OAuth)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsManualModalOpen(true)}
            className="flex items-center space-x-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-sm font-medium transition active:scale-95"
            title="Dán Refresh Token, Mã ủy quyền, hoặc Đường link Callback khi đăng nhập gặp sự cố mạng"
          >
            <Key className="w-4 h-4 text-slate-400" />
            <span>Dán Token / Link Callback</span>
          </button>
        </div>
      </div>

      {/* 4. Accounts Table / Cards List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      ) : accounts.length === 0 ? (
        <div className="text-center py-12 bg-slate-900/30 border border-slate-800/80 rounded-2xl text-slate-400 text-sm">
          Chưa có tài khoản Google nào trong hệ thống. Hãy bấm "Đăng nhập Google" để nạp tài khoản.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {accounts.map((a: any) => {
            const accQuota = quotaStats?.by_account?.[a.id] || {};
            const qHour = accQuota.hour?.requests || 0;
            const qDay = accQuota.day?.requests || 0;
            const qWeek = accQuota.week?.requests || 0;
            const qMonth = accQuota.month?.requests || 0;
            const qTokens = formatNumber(accQuota.all_time?.tokens || a.total_tokens || 0);

            return (
              <div
                key={a.id}
                className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between space-y-4 hover:border-slate-700 transition shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    {a.picture ? (
                      <img src={a.picture} className="w-10 h-10 rounded-full border border-slate-700 object-cover" alt="" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold">
                        {(a.name || 'G')[0]?.toUpperCase()}
                      </div>
                    )}
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <h4 className="font-bold text-sm text-white">{a.name || 'Google Account'}</h4>
                        {a.is_primary && (
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                            MẶC ĐỊNH
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 font-mono">{a.email}</p>
                    </div>
                  </div>

                  {/* Status Badge */}
                  {!a.is_active ? (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                      Đã tắt
                    </span>
                  ) : a.is_rate_limited ? (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center space-x-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
                      <span>Cooldown</span>
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                      <span>Sẵn sàng</span>
                    </span>
                  )}
                </div>

                {/* Google Real-time Quota Bars per Account */}
                {(() => {
                  const accQuotaRealtime = quotaOverview?.accounts?.[a.id];
                  const geminiInfo = accQuotaRealtime?.gemini || { used_percent: 0, remaining_percent: 100 };
                  const claudeInfo = accQuotaRealtime?.claude || { used_percent: 0, remaining_percent: 100 };
                  const gColor = getQuotaColor(geminiInfo.used_percent);
                  const cColor = getQuotaColor(claudeInfo.used_percent);

                  return (
                    <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/90 space-y-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                          <Gauge className="w-3.5 h-3.5 text-blue-400" />
                          <span>Hạn ngạch Google AI</span>
                        </span>
                        {accQuotaRealtime?.status === 'rate_limited' ? (
                          <span className="text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                            Hết Quota 429
                          </span>
                        ) : accQuotaRealtime?.status === 'error' ? (
                          <span className="text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                            Lỗi Token
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-500 flex items-center space-x-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>Live Quota</span>
                          </span>
                        )}
                      </div>

                      {/* Gemini Quota Bar */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-300 flex items-center space-x-1">
                            <Sparkles className="w-3 h-3 text-sky-400" />
                            <span className="font-medium">Gemini:</span>
                          </span>
                          <div className="flex items-center space-x-1.5 font-mono text-[11px]">
                            <span className={`font-semibold ${gColor.text}`}>
                              Đã dùng {geminiInfo.used_percent}%
                            </span>
                            <span className="text-slate-500">
                              (Còn {geminiInfo.remaining_percent}%)
                            </span>
                          </div>
                        </div>
                        <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${gColor.bar}`}
                            style={{ width: `${Math.min(100, Math.max(0, geminiInfo.used_percent))}%` }}
                          />
                        </div>
                        {geminiInfo.reset_time && (
                          <div className="text-[10px] text-slate-500 text-right font-mono">
                            {formatResetTime(geminiInfo.reset_time)}
                          </div>
                        )}
                      </div>

                      {/* Claude Quota Bar */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-slate-300 flex items-center space-x-1">
                            <Cpu className="w-3 h-3 text-purple-400" />
                            <span className="font-medium">Claude:</span>
                          </span>
                          <div className="flex items-center space-x-1.5 font-mono text-[11px]">
                            <span className={`font-semibold ${cColor.text}`}>
                              Đã dùng {claudeInfo.used_percent}%
                            </span>
                            <span className="text-slate-500">
                              (Còn {claudeInfo.remaining_percent}%)
                            </span>
                          </div>
                        </div>
                        <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${cColor.bar}`}
                            style={{ width: `${Math.min(100, Math.max(0, claudeInfo.used_percent))}%` }}
                          />
                        </div>
                        {claudeInfo.reset_time && (
                          <div className="text-[10px] text-slate-500 text-right font-mono">
                            {formatResetTime(claudeInfo.reset_time)}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* Quota Metrics Container per Account */}
                <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 space-y-2 font-mono text-xs">
                  <div className="flex items-center justify-between text-slate-400">
                    <div>
                      Project: <span className="text-slate-200">{a.project_id || 'aicode-consumers'}</span>
                    </div>
                    <div>
                      Tổng:{' '}
                      <span className="text-blue-400 font-bold">
                        {a.total_requests || a.requests_count || 0} reqs
                      </span>{' '}
                      <span className="text-slate-500">({qTokens} tok)</span>
                    </div>
                  </div>

                  {/* Mini breakdown quota per account */}
                  <div className="grid grid-cols-4 gap-1.5 text-center pt-2 border-t border-slate-800/80">
                    <div className="bg-slate-900/90 py-1.5 px-1 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500">Giờ</div>
                      <div className="font-bold text-sky-400 text-xs">{qHour}</div>
                    </div>
                    <div className="bg-slate-900/90 py-1.5 px-1 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500">Ngày</div>
                      <div className="font-bold text-emerald-400 text-xs">{qDay}</div>
                    </div>
                    <div className="bg-slate-900/90 py-1.5 px-1 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500">Tuần</div>
                      <div className="font-bold text-purple-400 text-xs">{qWeek}</div>
                    </div>
                    <div className="bg-slate-900/90 py-1.5 px-1 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500">Tháng</div>
                      <div className="font-bold text-amber-400 text-xs">{qMonth}</div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-800/60">
                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => handleToggle(a)}
                      className={`p-2 rounded-xl text-xs font-semibold border transition ${
                        a.is_active
                          ? 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                          : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      }`}
                      title={a.is_active ? 'Tắt tài khoản' : 'Bật tài khoản'}
                    >
                      <Power className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => handleTest(a.id)}
                      className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
                      title="Kiểm tra kết nối và quota"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>

                    {!a.is_primary && (
                      <button
                        onClick={() => handleSetPrimary(a.id)}
                        className="p-2 rounded-xl bg-slate-800 hover:bg-amber-500/20 text-slate-400 hover:text-amber-400 text-xs font-semibold border border-slate-700 transition"
                        title="Đặt làm tài khoản chính"
                      >
                        <Star className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  <button
                    onClick={() => handleDelete(a)}
                    className="p-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-xs font-semibold border border-slate-700 transition"
                    title="Gỡ tài khoản khỏi cụm"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Token Modal */}
      {isManualModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-base text-white flex items-center space-x-2">
                <Key className="w-4 h-4 text-blue-400" />
                <span>Thêm Tài Khoản Google (Token / Link Callback)</span>
              </h3>
              <button
                onClick={() => setIsManualModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs space-y-1.5">
              <div className="font-semibold flex items-center space-x-1.5 text-blue-300">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>Hỗ trợ tự động nhận diện thông minh:</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300 pl-1">
                <li>
                  <strong className="text-white">Đường link Callback:</strong> Khi cửa sổ đăng nhập hiện lỗi <em className="text-amber-300 not-italic">"can't reach this page" / "localhost refused to connect"</em>, bạn chỉ cần copy toàn bộ đường link trên thanh địa chỉ (ví dụ: <code className="text-blue-400 font-mono">http://localhost:51122/oauth-callback?code=...</code>) và dán vào đây.
                </li>
                <li>
                  <strong className="text-white">Mã ủy quyền (Auth Code):</strong> Dán mã bắt đầu bằng <code className="text-blue-400 font-mono">4/0A...</code>
                </li>
                <li>
                  <strong className="text-white">Refresh Token:</strong> Dán mã bắt đầu bằng <code className="text-blue-400 font-mono">1//04...</code>
                </li>
              </ul>
            </div>

            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Tên gợi nhớ (Tùy chọn):
                </label>
                <input
                  type="text"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="Ví dụ: Tài khoản Google phụ 1"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Dán Link Callback / Auth Code / Refresh Token (*):
                </label>
                <textarea
                  rows={4}
                  required
                  value={manualToken}
                  onChange={(e) => setManualToken(e.target.value)}
                  placeholder="Dán đường link (http://localhost:51122/oauth-callback?code=...), hoặc mã 4/0A..., hoặc Refresh Token 1//04... vào đây"
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsManualModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-medium transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={submittingManual || !manualToken.trim()}
                  className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-600/20 transition disabled:opacity-50 flex items-center space-x-1.5"
                >
                  {submittingManual && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Lưu Tài Khoản</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
