import React, { useState, useEffect } from 'react';
import { QuotaStats, RequestLog } from '../../types';
import { quotaService } from '../../services/quotaService';
import { useToast } from '../../context/ToastContext';
import {
  Activity,
  BarChart3,
  Trash2,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle2,
  Clock,
  Loader2
} from 'lucide-react';

export const QuotaTab: React.FC = () => {
  const { showToast } = useToast();

  const [stats, setStats] = useState<QuotaStats | null>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      const [s, l] = await Promise.all([
        quotaService.getStats(),
        quotaService.getLogs(50),
      ]);
      setStats(s);
      setLogs(l);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải dữ liệu thống kê quota', 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleClearLogs = async () => {
    if (!window.confirm('Bạn có chắc muốn xóa sạch toàn bộ lịch sử quota requests log?')) return;
    try {
      await quotaService.clearLogs();
      showToast('Đã xóa toàn bộ dữ liệu log!', 'success');
      fetchData();
    } catch (err: any) {
      showToast(err.message || 'Lỗi xóa logs', 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-5 rounded-2xl">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <Activity className="w-5 h-5 text-purple-400" />
            <span>Thống Kê Tiêu Thụ & Nhật Ký Lượt Gọi (Analytics)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Theo dõi thời gian thực lưu lượng request, tổng số token xử lý và hiệu suất tài khoản.
          </p>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-purple-400' : ''}`} />
            <span>Làm mới</span>
          </button>

          <button
            onClick={handleClearLogs}
            className="flex items-center space-x-1.5 px-3.5 py-2 bg-rose-500/10 hover:bg-rose-600 text-rose-300 hover:text-white rounded-xl text-xs font-semibold border border-rose-500/20 transition active:scale-95"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Xóa lịch sử log</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
        </div>
      ) : (
        <>
          {/* KPI Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Tổng lượt gọi API</span>
                <Layers className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-black text-white font-mono">
                {(stats?.total_requests || 0).toLocaleString()}
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Tổng tokens xử lý</span>
                <BarChart3 className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-black text-purple-300 font-mono">
                {(stats?.total_tokens || 0).toLocaleString()}
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Tài khoản sẵn sàng</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-black text-emerald-300 font-mono">
                {stats?.active_accounts || 0}
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-slate-400 text-xs">
                <span>Tỉ lệ thành công</span>
                <Clock className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-black text-blue-300 font-mono">100%</div>
            </div>
          </div>

          {/* Model Breakdown */}
          {stats?.models_usage && Object.keys(stats.models_usage).length > 0 && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span>Phân Bổ Lượng Gọi Theo Từng Model</span>
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 text-xs">
                {Object.entries(stats.models_usage).map(([m, count]) => (
                  <div key={m} className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                    <div className="text-slate-400 truncate">{m}</div>
                    <div className="font-bold text-white font-mono text-sm">{count.toLocaleString()} lượt</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Requests Log Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800 text-sm font-bold text-white">
              50 Lượt Gọi Gần Nhất
            </div>
            {logs.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">Chưa có nhật ký lượt gọi nào.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800 text-[11px]">
                    <tr>
                      <th className="p-3">Thời gian</th>
                      <th className="p-3">Tài khoản Google</th>
                      <th className="p-3">Model</th>
                      <th className="p-3 text-right">Prompt Tokens</th>
                      <th className="p-3 text-right">Output Tokens</th>
                      <th className="p-3 text-right">Tổng Tokens</th>
                      <th className="p-3 text-center">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-800/30 transition">
                        <td className="p-3 font-sans text-slate-400 text-[11px]">
                          {new Date(log.timestamp * 1000).toLocaleTimeString()}
                        </td>
                        <td className="p-3 text-purple-300 font-sans">{log.account_email}</td>
                        <td className="p-3 text-slate-200">{log.model}</td>
                        <td className="p-3 text-right text-slate-400">{log.prompt_tokens}</td>
                        <td className="p-3 text-right text-slate-400">{log.completion_tokens}</td>
                        <td className="p-3 text-right font-bold text-white">{log.total_tokens}</td>
                        <td className="p-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-sans font-bold border uppercase ${
                              log.status === 'success'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
