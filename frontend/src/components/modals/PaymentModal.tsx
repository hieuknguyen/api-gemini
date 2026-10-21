import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { paymentService, CheckOrderStatusResponse } from '../../services/paymentService';
import { TokenPackage, PaymentTransaction } from '../../types';
import {
  X,
  Coins,
  QrCode,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  History,
  Zap,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  RefreshCw
} from 'lucide-react';

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PaymentModal: React.FC<PaymentModalProps> = ({ isOpen, onClose }) => {
  const { user, refreshUser } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<'packages' | 'history'>('packages');
  const [packages, setPackages] = useState<TokenPackage[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string>('pkg_standard');
  const [isCustomAmount, setIsCustomAmount] = useState<boolean>(false);
  const [customAmount, setCustomAmount] = useState<string>('50000');
  const [loadingPackages, setLoadingPackages] = useState<boolean>(false);

  // Payment execution state
  const [creatingPayment, setCreatingPayment] = useState<boolean>(false);
  const [currentOrder, setCurrentOrder] = useState<{
    orderId: string;
    payUrl?: string;
    qrCodeUrl?: string;
    amount: number;
    tokens: number;
    packageName?: string;
  } | null>(null);

  // Polling state
  const [paymentStatus, setPaymentStatus] = useState<'pending' | 'success' | 'failed' | null>(null);
  const [pollingActive, setPollingActive] = useState<boolean>(false);
  const pollIntervalRef = useRef<any>(null);

  // History state
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Fetch packages on open
  useEffect(() => {
    if (isOpen) {
      fetchPackages();
      setCurrentOrder(null);
      setPaymentStatus(null);
      setPollingActive(false);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    } else {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [isOpen]);

  const fetchPackages = async () => {
    try {
      setLoadingPackages(true);
      const res = await paymentService.getPackages();
      if (res && res.packages) {
        setPackages(res.packages);
        const popular = res.packages.find((p) => p.popular);
        if (popular) {
          setSelectedPackageId(popular.id);
        } else if (res.packages.length > 0) {
          setSelectedPackageId(res.packages[0].id);
        }
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải danh sách gói nạp', 'error');
    } finally {
      setLoadingPackages(false);
    }
  };

  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const data = await paymentService.getMyTransactions();
      setTransactions(data || []);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải lịch sử nạp', 'error');
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab]);

  // Start polling order status
  const startPolling = (orderId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setPollingActive(true);

    let attempts = 0;
    const maxAttempts = 100; // ~5 mins at 3s intervals

    pollIntervalRef.current = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        setPollingActive(false);
        return;
      }

      try {
        const res: CheckOrderStatusResponse = await paymentService.checkOrderStatus(orderId);
        if (res && res.status === 'success') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setPaymentStatus('success');
          setPollingActive(false);
          refreshUser();
          showToast(`Thanh toán thành công! Đã cộng ${res.tokens_granted.toLocaleString('vi-VN')} tokens vào tài khoản.`, 'success');
        } else if (res && res.status === 'failed') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setPaymentStatus('failed');
          setPollingActive(false);
        }
      } catch (e) {
        // Continue polling silently
      }
    }, 3000);
  };

  const handleCreatePayment = async () => {
    setCreatingPayment(true);
    try {
      let pkgId: string | undefined = undefined;
      let amt: number | undefined = undefined;

      if (isCustomAmount) {
        const parsed = parseInt(customAmount.replace(/\D/g, ''), 10);
        if (isNaN(parsed) || parsed < 10000) {
          showToast('Số tiền nạp tối thiểu là 10.000 VNĐ!', 'warning');
          setCreatingPayment(false);
          return;
        }
        amt = parsed;
      } else {
        pkgId = selectedPackageId;
      }

      const res = await paymentService.createPayment(pkgId, amt);
      if (res && res.status === 'success') {
        setCurrentOrder({
          orderId: res.order_id,
          payUrl: res.pay_url,
          qrCodeUrl: res.qr_code_url,
          amount: res.amount,
          tokens: res.tokens,
          packageName: res.package_name,
        });
        setPaymentStatus('pending');
        startPolling(res.order_id);
      } else {
        showToast(res.message || 'Lỗi khởi tạo cổng MoMo', 'error');
      }
    } catch (err: any) {
      showToast(err.message || 'Không thể tạo đơn thanh toán', 'error');
    } finally {
      setCreatingPayment(false);
    }
  };

  const handleCancelOrder = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setCurrentOrder(null);
    setPaymentStatus(null);
    setPollingActive(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-3 sm:p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full shadow-2xl relative overflow-hidden backdrop-blur-xl flex flex-col max-h-[92vh]">
        {/* Top Accent Line */}
        <div className="h-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 shrink-0"></div>

        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-pink-500/10 border border-pink-500/30 text-pink-400 flex items-center justify-center shadow-inner">
              <Coins className="w-5 h-5 text-pink-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-bold text-base text-white">Nạp Token Antigravity</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-pink-500/10 text-pink-400 border border-pink-500/20">
                  MoMo QR Pay
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Thanh toán quét mã siêu tốc, hệ thống tự động cộng token ngay lập tức
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs Bar */}
        <div className="px-4 sm:px-5 pt-3 border-b border-slate-800 flex items-center space-x-2 shrink-0 bg-slate-950/40">
          <button
            onClick={() => {
              setActiveTab('packages');
              handleCancelOrder();
            }}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'packages'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>Gói Nạp Token</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'history'
                ? 'border-pink-500 text-pink-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Lịch Sử Giao Dịch</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 space-y-5">
          {/* User Current Balance Badge */}
          <div className="flex flex-wrap items-center justify-between p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">Tài khoản:</span>
              <span className="text-xs font-bold text-slate-200">{user?.name}</span>
              <span className="text-[10px] text-slate-500 font-mono">({user?.email})</span>
            </div>
            <div className="flex items-center space-x-2 mt-1 sm:mt-0">
              <span className="text-xs text-slate-400">Số dư hiện tại:</span>
              <span className="text-xs font-bold font-mono px-2 py-0.5 rounded-lg bg-pink-500/10 text-pink-400 border border-pink-500/20">
                {(user?.token_balance ?? 0).toLocaleString('vi-VN')} Tokens
              </span>
            </div>
          </div>

          {activeTab === 'packages' && (
            <>
              {!currentOrder ? (
                /* Step 1: Package Selection */
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {packages.map((pkg) => {
                      const isSelected = !isCustomAmount && selectedPackageId === pkg.id;
                      return (
                        <div
                          key={pkg.id}
                          onClick={() => {
                            setSelectedPackageId(pkg.id);
                            setIsCustomAmount(false);
                          }}
                          className={`relative p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                            isSelected
                              ? 'bg-gradient-to-b from-pink-950/40 to-slate-900 border-pink-500/80 shadow-lg shadow-pink-500/10'
                              : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60'
                          }`}
                        >
                          {pkg.badge && (
                            <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full text-[9px] font-bold bg-pink-500 text-white uppercase tracking-wider shadow">
                              {pkg.badge}
                            </div>
                          )}

                          <div>
                            <div className="font-bold text-sm text-white flex items-center space-x-1.5">
                              <span>{pkg.name}</span>
                            </div>
                            <div className="mt-1 flex items-baseline space-x-1.5">
                              <span className="text-lg font-black text-pink-400">
                                {pkg.price.toLocaleString('vi-VN')} đ
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 mt-1">{pkg.description}</p>
                          </div>

                          <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between">
                            <span className="text-xs font-bold text-emerald-400 font-mono">
                              +{pkg.tokens.toLocaleString('vi-VN')} Tokens
                            </span>
                            <div
                              className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                                isSelected ? 'border-pink-500 bg-pink-500 text-white' : 'border-slate-600'
                              }`}
                            >
                              {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white"></div>}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Custom Amount Option */}
                  <div
                    onClick={() => setIsCustomAmount(true)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition ${
                      isCustomAmount
                        ? 'bg-pink-950/30 border-pink-500/80'
                        : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Coins className="w-4 h-4 text-purple-400" />
                        <span className="text-xs font-bold text-slate-200">
                          Nạp số tiền tùy chọn (Tỉ giá: 10.000 đ = 1.000.000 tokens)
                        </span>
                      </div>
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                          isCustomAmount ? 'border-pink-500 bg-pink-500 text-white' : 'border-slate-600'
                        }`}
                      >
                        {isCustomAmount && <div className="w-1.5 h-1.5 rounded-full bg-white"></div>}
                      </div>
                    </div>

                    {isCustomAmount && (
                      <div className="mt-3 flex items-center space-x-3 pt-2 border-t border-slate-800">
                        <div className="relative flex-1">
                          <input
                            type="number"
                            step="5000"
                            min="10000"
                            value={customAmount}
                            onChange={(e) => setCustomAmount(e.target.value)}
                            placeholder="Nhập số tiền VNĐ (vd: 50000)"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-pink-500"
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">VNĐ</span>
                        </div>
                        <div className="text-xs text-emerald-400 font-mono font-bold shrink-0">
                          ≈ {((parseInt(customAmount || '0', 10) || 0) * 100).toLocaleString('vi-VN')} tokens
                        </div>
                      </div>
                    )}
                  </div>

                  {/* MoMo Action Button */}
                  <div className="pt-2">
                    <button
                      onClick={handleCreatePayment}
                      disabled={creatingPayment}
                      className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-pink-600 via-rose-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-lg shadow-pink-600/25 transition active:scale-[0.99] disabled:opacity-50"
                    >
                      {creatingPayment ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Đang kết nối cổng MoMo...</span>
                        </>
                      ) : (
                        <>
                          <QrCode className="w-4 h-4" />
                          <span>Tạo Mã QR MoMo & Thanh Toán Ngay</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                    <p className="text-[11px] text-center text-slate-500 mt-2 flex items-center justify-center space-x-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Xác thực thanh toán bảo mật bằng chữ ký HMAC-SHA256 chuẩn MoMo Gateway</span>
                    </p>
                  </div>
                </div>
              ) : (
                /* Step 2: Payment in progress / QR Code display */
                <div className="space-y-5 text-center">
                  {paymentStatus === 'success' ? (
                    <div className="p-6 rounded-2xl bg-emerald-950/40 border border-emerald-500/40 space-y-3">
                      <CheckCircle2 className="w-14 h-14 text-emerald-400 mx-auto animate-bounce" />
                      <h4 className="text-base font-bold text-white">Thanh Toán Hoàn Tất Thành Công!</h4>
                      <p className="text-xs text-slate-300">
                        Hệ thống đã tự động cộng{' '}
                        <b className="text-emerald-400 font-mono">+{currentOrder.tokens.toLocaleString('vi-VN')} Tokens</b>{' '}
                        vào tài khoản của bạn.
                      </p>
                      <div className="pt-2 flex justify-center space-x-3">
                        <button
                          onClick={() => {
                            handleCancelOrder();
                            onClose();
                          }}
                          className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-lg shadow-emerald-600/30"
                        >
                          Bắt đầu sử dụng ngay
                        </button>
                      </div>
                    </div>
                  ) : paymentStatus === 'failed' ? (
                    <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/40 space-y-3">
                      <AlertCircle className="w-12 h-12 text-rose-400 mx-auto" />
                      <h4 className="text-base font-bold text-white">Giao Dịch Thất Bại Hoặc Hết Hạn</h4>
                      <p className="text-xs text-slate-300">Đơn hàng chưa được thanh toán hoặc đã bị hủy.</p>
                      <button
                        onClick={handleCancelOrder}
                        className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold transition"
                      >
                        Thử Lại Gói Khác
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 inline-block mx-auto shadow-xl">
                        {currentOrder.qrCodeUrl ? (
                          <div className="relative group">
                            <img
                              src={currentOrder.qrCodeUrl}
                              alt="MoMo QR Code"
                              className="w-52 h-52 sm:w-60 sm:h-60 mx-auto rounded-lg bg-white p-2"
                            />
                            <div className="absolute inset-x-0 bottom-1 text-[10px] bg-black/60 text-white py-0.5 rounded">
                              Quét bằng MoMo
                            </div>
                          </div>
                        ) : (
                          <div className="w-52 h-52 flex flex-col items-center justify-center text-slate-400 space-y-2">
                            <QrCode className="w-12 h-12 text-pink-400" />
                            <span className="text-xs">Quét mã trong MoMo App</span>
                          </div>
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="text-xs text-slate-400">Số tiền cần thanh toán:</div>
                        <div className="text-2xl font-black text-pink-400">
                          {currentOrder.amount.toLocaleString('vi-VN')} đ
                        </div>
                        <div className="text-xs text-emerald-400 font-mono font-semibold">
                          +{currentOrder.tokens.toLocaleString('vi-VN')} Tokens
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          Mã đơn hàng: {currentOrder.orderId}
                        </div>
                      </div>

                      {/* Realtime Polling Badge */}
                      <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                        <span>Đang chờ bạn quét mã và xác nhận thanh toán trên MoMo...</span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                        {currentOrder.payUrl && (
                          <a
                            href={currentOrder.payUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center space-x-1.5 px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-pink-600/20"
                          >
                            <span>Mở Cổng MoMo (Web / App)</span>
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}

                        <button
                          onClick={handleCancelOrder}
                          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                        >
                          Hủy Đơn & Chọn Lại
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {activeTab === 'history' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400">Các giao dịch nạp token của bạn:</span>
                <button
                  onClick={fetchHistory}
                  disabled={loadingHistory}
                  className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded-lg transition"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingHistory ? 'animate-spin' : ''}`} />
                  <span>Làm mới</span>
                </button>
              </div>

              {loadingHistory ? (
                <div className="p-8 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Đang tải lịch sử giao dịch...</span>
                </div>
              ) : transactions.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs bg-slate-950/40 border border-slate-800 rounded-xl">
                  Bạn chưa có giao dịch nạp token nào.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                      <tr>
                        <th className="p-2.5">Thời Gian</th>
                        <th className="p-2.5">Gói Nạp</th>
                        <th className="p-2.5">Số Tiền</th>
                        <th className="p-2.5">Tokens Nhận</th>
                        <th className="p-2.5">Trạng Thái</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono text-[11px]">
                      {transactions.map((tx) => (
                        <tr key={tx.id} className="hover:bg-slate-900/40">
                          <td className="p-2.5 text-slate-400 font-sans">
                            {tx.created_at ? new Date(tx.created_at).toLocaleString('vi-VN') : '—'}
                          </td>
                          <td className="p-2.5 text-white font-sans font-semibold">
                            {tx.package_name || 'Tùy chọn'}
                          </td>
                          <td className="p-2.5 text-pink-300 font-bold">
                            {tx.amount.toLocaleString('vi-VN')} đ
                          </td>
                          <td className="p-2.5 text-emerald-400 font-bold">
                            +{tx.tokens_granted.toLocaleString('vi-VN')}
                          </td>
                          <td className="p-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase font-sans ${
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
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-end shrink-0 bg-slate-950/40">
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
