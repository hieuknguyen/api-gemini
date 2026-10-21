import React, { useState, useEffect } from 'react';
import { SystemSettings, PaymentTransaction, MoMoConfig } from '../../types';
import { settingsService } from '../../services/settingsService';
import { paymentService } from '../../services/paymentService';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import {
  Settings as SettingsIcon,
  Sliders,
  Cpu,
  Key,
  Save,
  RefreshCw,
  Shield,
  Loader2,
  Coins,
  QrCode,
  CreditCard,
  Globe,
  History,
  Lock,
  CheckCircle2,
  Trash2
} from 'lucide-react';

const STRATEGIES = [
  { id: 'round_robin', name: 'Xoay Tua Đều (Round Robin - Khuyên Dùng)', desc: 'Phân bổ tuần tự đều đặn các yêu cầu giữa tất cả các tài khoản hoạt động.' },
  { id: 'priority', name: 'Tài Khoản Ưu Tiên (Priority First)', desc: 'Luôn ưu tiên gọi tài khoản đánh dấu Primary, chỉ chuyển khi hết hạn mức.' },
  { id: 'fallback', name: 'Dự Phòng Khi Lỗi (Fallback)', desc: 'Chỉ chuyển sang tài khoản khác nếu tài khoản hiện tại gặp lỗi hoặc rate-limit.' },
  { id: 'least_used', name: 'Ưu Tiên Tài Khoản Dùng Ít Nhất (Least Used)', desc: 'Tự động chọn tài khoản có tổng số lượt gọi thấp nhất để cân bằng.' },
];

export const SettingsTab: React.FC = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();

  const [settings, setSettings] = useState<SystemSettings>({});
  const [strategy, setStrategy] = useState('round_robin');
  const [defaultModel, setDefaultModel] = useState('gemini-2.5-flash');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generatingKey, setGeneratingKey] = useState(false);
  const [googleOAuthClientId, setGoogleOAuthClientId] = useState('');
  const [googleOAuthClientSecret, setGoogleOAuthClientSecret] = useState('');
  const [googleOAuthSecretConfigured, setGoogleOAuthSecretConfigured] = useState(false);
  const [savingGoogleOAuth, setSavingGoogleOAuth] = useState(false);
  const [deletingGoogleOAuth, setDeletingGoogleOAuth] = useState(false);

  // MoMo Config state
  const [momoPartnerCode, setMomoPartnerCode] = useState('');
  const [momoAccessKey, setMomoAccessKey] = useState('');
  const [momoSecretKey, setMomoSecretKey] = useState('');
  const [momoEnvironment, setMomoEnvironment] = useState<'sandbox' | 'production'>('sandbox');
  const [momoIpnUrl, setMomoIpnUrl] = useState('');
  const [momoRedirectUrl, setMomoRedirectUrl] = useState('');
  const [savingMoMo, setSavingMoMo] = useState(false);

  // MoMo Admin Transactions state
  const [adminTransactions, setAdminTransactions] = useState<PaymentTransaction[]>([]);
  const [loadingTransactions, setLoadingTransactions] = useState(false);

  useEffect(() => {
    if (isAdmin) {
      fetchSettings();
      fetchMoMoConfig();
      fetchAdminTransactions();
    }
  }, [isAdmin]);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsService.getSettings();
      setSettings(data);
      if (data.strategy) setStrategy(data.strategy);
      if (data.default_model) setDefaultModel(data.default_model);
      if (data.api_key) setApiKey(data.api_key);
      setGoogleOAuthClientId(data.google_oauth_client_id || '');
      setGoogleOAuthSecretConfigured(Boolean(data.google_oauth_secret_configured));
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải cấu hình hệ thống', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchMoMoConfig = async () => {
    try {
      const cfg = await paymentService.getMoMoConfigAdmin();
      if (cfg) {
        setMomoPartnerCode(cfg.partner_code || '');
        setMomoAccessKey(cfg.access_key || '');
        setMomoEnvironment(cfg.environment || 'sandbox');
        setMomoIpnUrl(cfg.ipn_url || '');
        setMomoRedirectUrl(cfg.redirect_url || '');
      }
    } catch (err: any) {
      console.warn('Chưa tải được cấu hình MoMo:', err);
    }
  };

  const fetchAdminTransactions = async () => {
    try {
      setLoadingTransactions(true);
      const txs = await paymentService.getAllTransactionsAdmin();
      setAdminTransactions(txs || []);
    } catch (err: any) {
      console.warn('Lỗi tải giao dịch MoMo admin:', err);
    } finally {
      setLoadingTransactions(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await settingsService.updateSettings({
        strategy,
        default_model: defaultModel,
        api_key: apiKey || undefined,
      });
      showToast('Đã lưu cấu hình hệ thống thành công!', 'success');
      fetchSettings();
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu cấu hình', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveMoMoConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingMoMo(true);
    try {
      const payload: Partial<MoMoConfig> = {
        partner_code: momoPartnerCode,
        access_key: momoAccessKey,
        environment: momoEnvironment,
        ipn_url: momoIpnUrl,
        redirect_url: momoRedirectUrl,
      };
      if (momoSecretKey.trim()) {
        (payload as any).secret_key = momoSecretKey.trim();
      }
      await paymentService.updateMoMoConfigAdmin(payload);
      showToast('Đã lưu cấu hình cổng thanh toán MoMo thành công!', 'success');
      setMomoSecretKey('');
      fetchMoMoConfig();
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu cấu hình MoMo', 'error');
    } finally {
      setSavingMoMo(false);
    }
  };

  const handleGenerateKey = async () => {
    setGeneratingKey(true);
    try {
      const res = await settingsService.generateKey();
      setApiKey(res.api_key);
      showToast('Đã tạo API Key ngẫu nhiên mới!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi tạo key', 'error');
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleSaveGoogleOAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingGoogleOAuth(true);
    try {
      const result = await settingsService.saveGoogleOAuth(
        googleOAuthClientId.trim(),
        googleOAuthClientSecret.trim() || undefined,
      );
      setGoogleOAuthClientId(result.google_oauth_client_id || googleOAuthClientId.trim());
      setGoogleOAuthSecretConfigured(Boolean(result.google_oauth_secret_configured));
      setGoogleOAuthClientSecret('');
      showToast('Đã lưu cấu hình Google OAuth vào database.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu cấu hình Google OAuth', 'error');
    } finally {
      setSavingGoogleOAuth(false);
    }
  };

  const handleDeleteGoogleOAuth = async () => {
    if (!window.confirm('Xóa Client ID và Client Secret Google OAuth khỏi hệ thống?')) return;
    setDeletingGoogleOAuth(true);
    try {
      await settingsService.deleteGoogleOAuth();
      setGoogleOAuthClientId('');
      setGoogleOAuthClientSecret('');
      setGoogleOAuthSecretConfigured(false);
      showToast('Đã xóa cấu hình Google OAuth.', 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi xóa cấu hình Google OAuth', 'error');
    } finally {
      setDeletingGoogleOAuth(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl">
        <Shield className="w-12 h-12 text-purple-400 mx-auto mb-3" />
        <h3 className="text-base font-bold text-white">Chỉ Dành Cho Quản Trị Viên (Admin)</h3>
        <p className="text-xs text-slate-400 mt-1">Cấu hình điều phối tài khoản, cổng MoMo và thiết lập lõi Gateway.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* 1. Header */}
      <div className="bg-slate-900/60 border border-slate-800 p-5 rounded-2xl">
        <h2 className="text-lg font-bold text-white flex items-center space-x-2">
          <SettingsIcon className="w-5 h-5 text-purple-400" />
          <span>Cấu Hình Hệ Thống & Quản Trị Cổng MoMo</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Thiết lập chiến lược xoay vòng tài khoản, cổng thanh toán MoMo QR Pay và các tham số vận hành AI Gateway.
        </p>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Đang tải cài đặt hệ thống...</span>
        </div>
      ) : (
        <div className="space-y-6">
          {/* 2. Form Gateway Core Settings */}
          <form onSubmit={handleSaveSettings} className="space-y-6">
            {/* Chiến lược phân phối tài khoản */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
              <div className="flex items-center space-x-2">
                <Sliders className="w-5 h-5 text-blue-400" />
                <h3 className="text-sm font-bold text-white">Chiến Lược Phân Phối Tài Khoản Google</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {STRATEGIES.map((s) => (
                  <label
                    key={s.id}
                    className={`p-4 rounded-xl border cursor-pointer transition flex items-start space-x-3 ${
                      strategy === s.id
                        ? 'bg-blue-600/10 border-blue-500 text-white shadow-lg shadow-blue-500/10'
                        : 'bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="strategy"
                      value={s.id}
                      checked={strategy === s.id}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="mt-0.5 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="space-y-1">
                      <div className="font-bold">{s.name}</div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">{s.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Model & Global Key Section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl text-xs">
              <div className="flex items-center space-x-2">
                <Cpu className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-bold text-white">Tham Số Mặc Định & Khóa Gateway</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-medium">Model Gemini Mặc Định:</label>
                  <select
                    value={defaultModel}
                    onChange={(e) => setDefaultModel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 rounded-xl px-3.5 py-2.5 text-slate-100 focus:outline-none cursor-pointer"
                  >
                    <option value="gemini-4-argon">Gemini 4 Argon (Suy luận nâng cao)</option>
                    <option value="gemini-3.8-flash-tiered">Gemini 3.8 Flash (Tiered - Khuyên dùng)</option>
                    <option value="gemini-2.5-flash">Gemini 2.5 Flash (Tiết kiệm quota)</option>
                    <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="text-slate-300 font-medium">Global Master API Key:</label>
                    <button
                      type="button"
                      onClick={handleGenerateKey}
                      disabled={generatingKey}
                      className="text-purple-400 hover:underline flex items-center space-x-1"
                    >
                      <RefreshCw className={`w-3 h-3 ${generatingKey ? 'animate-spin' : ''}`} />
                      <span>Tạo ngẫu nhiên</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-antigravity-..."
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl px-3.5 py-2.5 font-mono text-xs text-purple-300 placeholder:text-slate-600 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-purple-600/30 transition active:scale-95 disabled:opacity-50 flex items-center space-x-2"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>{saving ? 'Đang lưu...' : 'Lưu Thay Đổi Cấu Hình Gateway'}</span>
              </button>
            </div>
          </form>

          {/* Google OAuth credentials are stored in MySQL and managed by admins. */}
          <form onSubmit={handleSaveGoogleOAuth} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl text-xs">
            <div className="flex items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2">
                <Key className="w-5 h-5 text-blue-400" />
                <div>
                  <h3 className="text-sm font-bold text-white">Google OAuth</h3>
                  <p className="text-[11px] text-slate-400 mt-1">Lưu Client ID và Client Secret trong database để dùng cho đăng nhập Google.</p>
                </div>
              </div>
              <span className={`px-2 py-1 rounded-full text-[10px] font-semibold border ${googleOAuthSecretConfigured ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-amber-500/10 border-amber-500/30 text-amber-300'}`}>
                {googleOAuthSecretConfigured ? 'Đã cấu hình' : 'Chưa cấu hình'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Client ID:</label>
                <input
                  type="text"
                  value={googleOAuthClientId}
                  onChange={(e) => setGoogleOAuthClientId(e.target.value)}
                  placeholder="...apps.googleusercontent.com"
                  autoComplete="off"
                  required
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium flex items-center justify-between">
                  <span>Client Secret:</span>
                  <span className="text-[10px] text-slate-500 font-normal">Không hiển thị lại sau khi lưu</span>
                </label>
                <input
                  type="password"
                  value={googleOAuthClientSecret}
                  onChange={(e) => setGoogleOAuthClientSecret(e.target.value)}
                  placeholder={googleOAuthSecretConfigured ? 'Đã lưu — để trống để giữ nguyên' : 'Nhập Client Secret'}
                  autoComplete="new-password"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-blue-500 rounded-xl px-3.5 py-2.5 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-[11px] text-slate-500">Client Secret được giữ kín; để trống khi lưu nếu muốn giữ secret hiện tại.</p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDeleteGoogleOAuth}
                  disabled={deletingGoogleOAuth || (!googleOAuthClientId && !googleOAuthSecretConfigured)}
                  className="px-4 py-2.5 bg-rose-600/15 hover:bg-rose-600/25 border border-rose-500/30 text-rose-300 rounded-xl text-xs font-semibold transition disabled:opacity-40 flex items-center space-x-2"
                >
                  {deletingGoogleOAuth ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  <span>Xóa cấu hình</span>
                </button>
                <button
                  type="submit"
                  disabled={savingGoogleOAuth}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-600/20 transition disabled:opacity-50 flex items-center space-x-2"
                >
                  {savingGoogleOAuth ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  <span>{savingGoogleOAuth ? 'Đang lưu...' : 'Lưu Google OAuth'}</span>
                </button>
              </div>
            </div>
          </form>

          {/* 3. MoMo Payment Gateway Configuration Card */}
          <form onSubmit={handleSaveMoMoConfig} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-pink-500/10 border border-pink-500/30 text-pink-400 flex items-center justify-center">
                  <CreditCard className="w-4 h-4 text-pink-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <span>Cấu Hình Tích Hợp Cổng Thanh Toán MoMo</span>
                    <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-pink-500/10 text-pink-400 border border-pink-500/20 uppercase">
                      MoMo API v2
                    </span>
                  </h3>
                  <p className="text-slate-400 text-[11px]">
                    Quản lý thông tin kết nối Partner Code, Access Key, Secret Key và môi trường MoMo
                  </p>
                </div>
              </div>

              {/* Environment Toggle */}
              <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800">
                <button
                  type="button"
                  onClick={() => setMomoEnvironment('sandbox')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    momoEnvironment === 'sandbox'
                      ? 'bg-amber-500 text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🧪 Sandbox (Thử nghiệm)
                </button>
                <button
                  type="button"
                  onClick={() => setMomoEnvironment('production')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                    momoEnvironment === 'production'
                      ? 'bg-pink-600 text-white font-bold shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  🚀 Production (Thật)
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Partner Code:</label>
                <input
                  type="text"
                  value={momoPartnerCode}
                  onChange={(e) => setMomoPartnerCode(e.target.value)}
                  placeholder="MOMO..."
                  className="w-full bg-slate-950 border border-slate-800 focus:border-pink-500 rounded-xl px-3.5 py-2 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">Access Key:</label>
                <input
                  type="text"
                  value={momoAccessKey}
                  onChange={(e) => setMomoAccessKey(e.target.value)}
                  placeholder="Access Key..."
                  className="w-full bg-slate-950 border border-slate-800 focus:border-pink-500 rounded-xl px-3.5 py-2 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium flex items-center justify-between">
                  <span>Secret Key (Bảo mật HMAC-SHA256):</span>
                  <span className="text-[10px] text-slate-500 font-normal">Để trống nếu không đổi</span>
                </label>
                <input
                  type="password"
                  value={momoSecretKey}
                  onChange={(e) => setMomoSecretKey(e.target.value)}
                  placeholder="••••••••••••••••••••••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-pink-500 rounded-xl px-3.5 py-2 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-medium">IPN Webhook Callback URL:</label>
                <input
                  type="text"
                  value={momoIpnUrl}
                  onChange={(e) => setMomoIpnUrl(e.target.value)}
                  placeholder="https://your-domain.com/api/payment/momo/ipn"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-pink-500 rounded-xl px-3.5 py-2 text-slate-100 font-mono text-xs focus:outline-none"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <button
                type="submit"
                disabled={savingMoMo}
                className="px-6 py-2.5 bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-pink-600/25 transition active:scale-95 disabled:opacity-50 flex items-center space-x-2"
              >
                {savingMoMo ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>{savingMoMo ? 'Đang lưu...' : 'Lưu Cấu Hình MoMo Gateway'}</span>
              </button>
              <span className="text-[11px] text-slate-500">
                Mặc định tích hợp sẵn tài khoản MoMo Sandbox công khai dùng được ngay
              </span>
            </div>
          </form>

          {/* 4. MoMo Transactions History (Admin Table) */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <History className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Toàn Bộ Lịch Sử Giao Dịch MoMo (Admin)</h3>
              </div>
              <button
                type="button"
                onClick={fetchAdminTransactions}
                disabled={loadingTransactions}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl text-xs transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingTransactions ? 'animate-spin' : ''}`} />
                <span>Làm mới</span>
              </button>
            </div>

            {loadingTransactions ? (
              <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang tải danh sách giao dịch...</span>
              </div>
            ) : adminTransactions.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs bg-slate-950/40 border border-slate-800 rounded-xl">
                Chưa có giao dịch nạp MoMo nào trên hệ thống.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                    <tr>
                      <th className="p-3">Mã Đơn (Order ID)</th>
                      <th className="p-3">User ID</th>
                      <th className="p-3">Gói Nạp</th>
                      <th className="p-3">Số Tiền (VNĐ)</th>
                      <th className="p-3">Tokens Cộng</th>
                      <th className="p-3">Trạng Thái</th>
                      <th className="p-3">Thời Gian</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono text-[11px]">
                    {adminTransactions.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-900/40">
                        <td className="p-3 text-purple-300 font-bold">{tx.order_id}</td>
                        <td className="p-3 text-slate-400 truncate max-w-[120px]">{tx.request_id || '—'}</td>
                        <td className="p-3 text-white font-sans">{tx.package_name || 'Tùy chọn'}</td>
                        <td className="p-3 text-pink-300 font-bold">{tx.amount.toLocaleString('vi-VN')} đ</td>
                        <td className="p-3 text-emerald-400 font-bold">+{tx.tokens_granted.toLocaleString('vi-VN')}</td>
                        <td className="p-3 font-sans">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              tx.status === 'success'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                : tx.status === 'pending'
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {tx.status === 'success' ? 'Thành công' : tx.status === 'pending' ? 'Chờ quét' : 'Thất bại'}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400 font-sans">
                          {tx.created_at ? new Date(tx.created_at).toLocaleString('vi-VN') : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
