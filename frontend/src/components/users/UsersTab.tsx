import React, { useState, useEffect } from 'react';
import { User, ApiKey } from '../../types';
import { userService } from '../../services/userService';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import {
  UserCheck,
  Plus,
  Key,
  Trash2,
  Power,
  Copy,
  Check,
  Shield,
  Loader2,
  X,
  User as UserIcon,
  Mail,
  Lock,
  Shuffle,
  Edit3,
  Eye,
  EyeOff,
  Coins
} from 'lucide-react';
import { paymentService } from '../../services/paymentService';

export const UsersTab: React.FC = () => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // User modal
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [note, setNote] = useState('');
  const [submittingUser, setSubmittingUser] = useState(false);

  // Single Key manager modal
  const [selectedUserForKeys, setSelectedUserForKeys] = useState<User | null>(null);
  const [userKeys, setUserKeys] = useState<ApiKey[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [showKeyVal, setShowKeyVal] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [isCustomKeyOpen, setIsCustomKeyOpen] = useState(false);
  const [customKeyInput, setCustomKeyInput] = useState('');
  const [rotatingKey, setRotatingKey] = useState(false);
  
  // Adjust Token modal state
  const [selectedUserForToken, setSelectedUserForToken] = useState<User | null>(null);
  const [tokenDelta, setTokenDelta] = useState<number>(100000);
  const [submittingToken, setSubmittingToken] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await userService.getUsers();
      setUsers(data);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải danh sách người dùng', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;

    setSubmittingUser(true);
    try {
      await userService.createUser({
        name: name.trim(),
        email: email.trim(),
        password: password.trim() || undefined,
        role,
        note: note.trim() || undefined,
      });
      showToast('Đã tạo người dùng mới thành công!', 'success');
      setIsUserModalOpen(false);
      setName('');
      setEmail('');
      setPassword('');
      setNote('');
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi tạo người dùng', 'error');
    } finally {
      setSubmittingUser(false);
    }
  };

  const handleToggleUser = async (u: User) => {
    try {
      await userService.updateUser(u.id, { is_active: !u.is_active });
      showToast(`Đã ${u.is_active ? 'vô hiệu hóa' : 'kích hoạt'} tài khoản ${u.name}`, 'info');
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi cập nhật trạng thái', 'error');
    }
  };

  const handleDeleteUser = async (u: User) => {
    if (!window.confirm(`Bạn có chắc muốn xóa vĩnh viễn tài khoản "${u.name}" và toàn bộ API Key liên kết?`)) return;
    try {
      await userService.deleteUser(u.id);
      showToast(`Đã xóa tài khoản ${u.name}`, 'success');
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi xóa tài khoản', 'error');
    }
  };

  const handleOpenKeys = async (u: User) => {
    setSelectedUserForKeys(u);
    setLoadingKeys(true);
    setShowKeyVal(false);
    setIsCustomKeyOpen(false);
    setCustomKeyInput('');
    try {
      const keys = await userService.getUserKeys(u.id);
      setUserKeys(keys);
    } catch (err: any) {
      showToast(err.message || 'Lỗi tải API key', 'error');
    } finally {
      setLoadingKeys(false);
    }
  };

  const handleRotateRandomKey = async () => {
    if (!selectedUserForKeys) return;
    setRotatingKey(true);
    try {
      await userService.createApiKey(selectedUserForKeys.id, `Key - ${selectedUserForKeys.name}`);
      showToast(`Đã đổi API Key ngẫu nhiên mới duy nhất cho ${selectedUserForKeys.name}!`, 'success');
      const keys = await userService.getUserKeys(selectedUserForKeys.id);
      setUserKeys(keys);
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi tạo API Key ngẫu nhiên', 'error');
    } finally {
      setRotatingKey(false);
    }
  };

  const handleSaveCustomKey = async () => {
    if (!selectedUserForKeys || !customKeyInput.trim()) return;
    setRotatingKey(true);
    try {
      await userService.createApiKey(
        selectedUserForKeys.id,
        `Key - ${selectedUserForKeys.name}`,
        customKeyInput.trim()
      );
      showToast(`Đã cập nhật API Key tùy chỉnh duy nhất cho ${selectedUserForKeys.name}!`, 'success');
      setIsCustomKeyOpen(false);
      setCustomKeyInput('');
      const keys = await userService.getUserKeys(selectedUserForKeys.id);
      setUserKeys(keys);
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi lưu API Key tùy chỉnh', 'error');
    } finally {
      setRotatingKey(false);
    }
  };

  const handleCopyKey = (keyVal: string) => {
    navigator.clipboard.writeText(keyVal);
    setCopiedKey(true);
    showToast('Đã sao chép API Key vào clipboard!', 'success');
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleToggleKey = async (keyId: string) => {
    try {
      await userService.toggleApiKey(keyId);
      if (selectedUserForKeys) {
        const keys = await userService.getUserKeys(selectedUserForKeys.id);
        setUserKeys(keys);
        fetchUsers();
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi đổi trạng thái key', 'error');
    }
  };

  const handleOpenAdjustToken = (u: User) => {
    setSelectedUserForToken(u);
    setTokenDelta(100000);
  };

  const handleAdjustToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserForToken) return;
    if (!tokenDelta || isNaN(tokenDelta)) {
      showToast('Vui lòng nhập số lượng tokens hợp lệ!', 'warning');
      return;
    }

    setSubmittingToken(true);
    try {
      await paymentService.adjustUserTokensAdmin(selectedUserForToken.id, Number(tokenDelta));
      showToast(`Đã điều chỉnh ${Number(tokenDelta) > 0 ? '+' : ''}${Number(tokenDelta).toLocaleString()} tokens cho ${selectedUserForToken.name}!`, 'success');
      setSelectedUserForToken(null);
      fetchUsers();
    } catch (err: any) {
      showToast(err.message || 'Lỗi cập nhật token', 'error');
    } finally {
      setSubmittingToken(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl">
        <Shield className="w-12 h-12 text-purple-400 mx-auto mb-3" />
        <h3 className="text-base font-bold text-white">Quyền Truy Cập Bị Giới Hạn</h3>
        <p className="text-xs text-slate-400 mt-1">Chỉ quản trị viên (Admin) mới có quyền quản lý người dùng và cấp phát API Key.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/60 border border-slate-800 p-5 rounded-2xl">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <UserCheck className="w-5 h-5 text-purple-400" />
            <span>Quản Lý Người Dùng & API Keys Riêng Biệt</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Quản lý tài khoản gọi Gateway, phân quyền và cấp mã API Key độc lập cho từng dự án.
          </p>
        </div>

        <button
          onClick={() => setIsUserModalOpen(true)}
          className="flex items-center space-x-1.5 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-purple-600/20 transition active:scale-95 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Người Dùng</span>
        </button>
      </div>

      {/* Users Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800 text-[11px]">
              <tr>
                <th className="p-3.5">Người dùng</th>
                <th className="p-3.5">Email</th>
                <th className="p-3.5">Vai trò</th>
                <th className="p-3.5">Số dư Token</th>
                <th className="p-3.5">Trạng thái</th>
                <th className="p-3.5 text-right">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-800/30 transition">
                  <td className="p-3.5 font-bold flex items-center space-x-2">
                    <div className="w-7 h-7 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
                      <UserIcon className="w-3.5 h-3.5" />
                    </div>
                    <span>{u.name}</span>
                  </td>
                  <td className="p-3.5 text-slate-400 font-mono">{u.email || '—'}</td>
                  <td className="p-3.5">
                    <span
                      className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] border ${
                        u.role === 'admin'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="p-3.5">
                    {u.role === 'admin' ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        <span>∞</span>
                        <span className="text-[9px] text-amber-400/80">(Vô hạn)</span>
                      </span>
                    ) : (
                      <div className="flex items-center space-x-1.5 font-mono">
                        <Coins className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span
                          className={`font-bold text-xs ${
                            (u.token_balance ?? 0) <= 0
                              ? 'text-rose-400'
                              : (u.token_balance ?? 0) < 50000
                              ? 'text-yellow-400'
                              : 'text-emerald-400'
                          }`}
                        >
                          {(u.token_balance ?? 0).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="p-3.5">
                    <span
                      className={`px-2 py-0.5 rounded font-semibold text-[10px] border ${
                        u.is_active
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                      }`}
                    >
                      {u.is_active ? 'Hoạt động' : 'Khóa'}
                    </span>
                  </td>
                  <td className="p-3.5 text-right space-x-1.5">
                    <button
                      onClick={() => handleOpenAdjustToken(u)}
                      className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-600 text-amber-300 hover:text-white transition text-xs font-semibold border border-amber-500/20"
                      title="Nạp hoặc điều chỉnh số dư Token"
                    >
                      <Coins className="w-3 h-3 inline-block mr-1" />
                      <span>Token</span>
                    </button>

                    <button
                      onClick={() => handleOpenKeys(u)}
                      className="px-2.5 py-1 rounded-lg bg-purple-500/10 hover:bg-purple-600 text-purple-300 hover:text-white transition text-xs font-semibold border border-purple-500/20"
                    >
                      <Key className="w-3 h-3 inline-block mr-1" />
                      <span>API Key (1)</span>
                    </button>

                    <button
                      onClick={() => handleToggleUser(u)}
                      className={`p-1.5 rounded-lg border transition ${
                        u.is_active
                          ? 'hover:bg-amber-500/10 text-slate-400 hover:text-amber-400 border-slate-800'
                          : 'hover:bg-emerald-500/10 text-slate-400 hover:text-emerald-400 border-slate-800'
                      }`}
                      title={u.is_active ? 'Khóa tài khoản' : 'Mở khóa'}
                    >
                      <Power className="w-3.5 h-3.5" />
                    </button>

                    <button
                      onClick={() => handleDeleteUser(u)}
                      className="p-1.5 hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 rounded-lg transition"
                      title="Xóa tài khoản"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* User Create Modal */}
      {isUserModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-6 max-w-md w-full shadow-2xl relative overflow-hidden backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <UserIcon className="w-5 h-5 text-purple-400" />
                <h3 className="font-bold text-base text-white">Thêm Tài Khoản Mới</h3>
              </div>
              <button
                onClick={() => setIsUserModalOpen(false)}
                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Tên hiển thị / Dự án:</label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ví dụ: App Chatbot, Web Nhận Diện,..."
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Email:</label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Mật khẩu:</label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Để trống nếu không đặt mật khẩu..."
                    className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl pl-9 pr-3 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Vai trò:</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl px-3 py-2 text-slate-100 focus:outline-none"
                >
                  <option value="user">User (Người dùng thường)</option>
                  <option value="admin">Admin (Quản trị viên)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Ghi chú (Tùy chọn):</label>
                <input
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Ghi chú về tài khoản này..."
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-purple-500 rounded-xl px-3 py-2 text-slate-100 placeholder:text-slate-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={submittingUser}
                className="w-full py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white rounded-xl text-xs font-bold shadow transition active:scale-95 disabled:opacity-50 mt-2"
              >
                {submittingUser ? 'Đang tạo...' : 'Tạo Tài Khoản & Cấp Key'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* User API Key Modal (1 Account = 1 Single Key) */}
      {selectedUserForKeys && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-6 max-w-lg w-full shadow-2xl relative overflow-hidden backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
              <div className="flex items-center space-x-2">
                <div className="w-9 h-9 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-base text-white">Quản Lý API Key: {selectedUserForKeys.name}</h3>
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      1 Tài khoản • 1 Key duy nhất
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">Mã khóa truy cập Gateway duy nhất của tài khoản này</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedUserForKeys(null)}
                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {loadingKeys ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-7 h-7 text-purple-500 animate-spin" />
              </div>
            ) : userKeys.length === 0 ? (
              <div className="text-center py-8 space-y-3">
                <p className="text-slate-400 text-xs">Tài khoản này chưa có API Key nào được kích hoạt.</p>
                <button
                  onClick={handleRotateRandomKey}
                  disabled={rotatingKey}
                  className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white rounded-xl text-xs font-bold transition shadow"
                >
                  <Shuffle className="w-3.5 h-3.5 inline mr-1.5" />
                  <span>🎲 Cấp API Key Ngẫu Nhiên Ngay</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {(() => {
                  const currentKey = userKeys[0];
                  return (
                    <>
                      {/* Key Status & Actions Header */}
                      <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="font-bold text-xs text-white">{currentKey.name || `Key ${selectedUserForKeys.name}`}</span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                currentKey.is_active
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                  : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                              }`}
                            >
                              {currentKey.is_active ? 'Hoạt động' : 'Đã tắt'}
                            </span>
                          </div>
                          <button
                            onClick={() => handleToggleKey(currentKey.id)}
                            className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition flex items-center space-x-1 ${
                              currentKey.is_active
                                ? 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border-amber-500/30'
                                : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                            }`}
                            title={currentKey.is_active ? 'Tạm dừng key này' : 'Kích hoạt lại key'}
                          >
                            <Power className="w-3.5 h-3.5" />
                            <span>{currentKey.is_active ? 'Tắt Key' : 'Bật Key'}</span>
                          </button>
                        </div>

                        {/* Key Value Display */}
                        <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 font-mono text-xs text-purple-300">
                          <span className="truncate select-all mr-2">
                            {showKeyVal ? currentKey.key_value : (currentKey.key_value.length > 14 ? currentKey.key_value.slice(0, 14) + '••••••••••••••••' : '••••••••••••••••')}
                          </span>
                          <div className="flex items-center space-x-1.5 shrink-0">
                            <button
                              onClick={() => setShowKeyVal(!showKeyVal)}
                              className="p-1 hover:text-white rounded transition text-slate-400"
                              title={showKeyVal ? 'Ẩn Key' : 'Hiện Key'}
                            >
                              {showKeyVal ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              onClick={() => handleCopyKey(currentKey.key_value)}
                              className="p-1 hover:text-white rounded transition text-slate-400"
                              title="Sao chép"
                            >
                              {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
                          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
                            <span className="text-slate-500 block text-[10px]">Lượt gọi:</span>
                            <span className="font-bold text-slate-200">{currentKey.requests_count || 0}</span>
                          </div>
                          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
                            <span className="text-slate-500 block text-[10px]">Tokens:</span>
                            <span className="font-bold text-purple-300">{(currentKey.total_tokens || 0).toLocaleString()}</span>
                          </div>
                          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
                            <span className="text-slate-500 block text-[10px]">Khởi tạo:</span>
                            <span className="text-slate-300 truncate block">{currentKey.created_at ? currentKey.created_at.slice(0, 10) : '—'}</span>
                          </div>
                          <div className="bg-slate-900/60 p-2 rounded-lg border border-slate-800/60">
                            <span className="text-slate-500 block text-[10px]">Dùng gần nhất:</span>
                            <span className="text-slate-300 truncate block">{currentKey.last_used_at ? currentKey.last_used_at.slice(0, 10) : 'Chưa dùng'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Management Action Buttons */}
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          onClick={handleRotateRandomKey}
                          disabled={rotatingKey}
                          className="flex items-center space-x-1.5 px-3.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 text-white rounded-xl text-xs font-bold transition shadow active:scale-95 disabled:opacity-50"
                          title="Tạo lại API Key ngẫu nhiên mới duy nhất cho tài khoản này"
                        >
                          <Shuffle className="w-3.5 h-3.5" />
                          <span>🎲 Đổi Key Ngẫu Nhiên</span>
                        </button>
                        <button
                          onClick={() => setIsCustomKeyOpen(!isCustomKeyOpen)}
                          className="flex items-center space-x-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-medium transition active:scale-95"
                          title="Tự đặt mã Key tùy chỉnh cho người dùng"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          <span>Tự Đặt Key Tùy Chỉnh</span>
                        </button>
                      </div>

                      {/* Inline Custom Key Input */}
                      {isCustomKeyOpen && (
                        <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2 text-xs">
                          <label className="block text-slate-300 font-semibold text-[11px]">
                            Nhập mã Key mới cho tài khoản {selectedUserForKeys.name}:
                          </label>
                          <div className="flex items-center space-x-2">
                            <input
                              type="text"
                              value={customKeyInput}
                              onChange={(e) => setCustomKeyInput(e.target.value)}
                              placeholder="Nhập key tùy chỉnh (ví dụ: my_user_secret_key)..."
                              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-purple-500"
                            />
                            <button
                              onClick={handleSaveCustomKey}
                              disabled={rotatingKey}
                              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition active:scale-95 disabled:opacity-50"
                            >
                              Lưu
                            </button>
                            <button
                              onClick={() => setIsCustomKeyOpen(false)}
                              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg transition"
                            >
                              Hủy
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Adjust Token Modal */}
      {selectedUserForToken && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-slate-900/95 border border-slate-700/80 rounded-2xl p-6 max-w-md w-full shadow-2xl relative overflow-hidden backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
                  <Coins className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-white">Cộng / Trừ Token</h3>
                  <p className="text-xs text-slate-400">{selectedUserForToken.name} ({selectedUserForToken.email || 'No email'})</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedUserForToken(null)}
                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Current Balance Card */}
            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-between">
              <span className="text-xs text-slate-400">Số dư hiện tại:</span>
              <span className="text-sm font-mono font-bold text-amber-400">
                {(selectedUserForToken.token_balance ?? 0).toLocaleString()} <span className="text-[11px] text-slate-500">tokens</span>
              </span>
            </div>

            <form onSubmit={handleAdjustToken} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Số lượng Token điều chỉnh (Dương = Cộng, Âm = Trừ):
                </label>
                <input
                  type="number"
                  step="1000"
                  required
                  value={tokenDelta}
                  onChange={(e) => setTokenDelta(parseInt(e.target.value) || 0)}
                  className="w-full bg-slate-950/80 border border-slate-800 focus:border-amber-500 rounded-xl px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none"
                />
              </div>

              {/* Quick Presets */}
              <div>
                <span className="block text-slate-400 text-[11px] mb-1.5">Chọn nhanh số lượng:</span>
                <div className="grid grid-cols-3 gap-1.5">
                  {[50000, 100000, 500000, 1000000, -50000, -100000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setTokenDelta(val)}
                      className={`px-2 py-1.5 rounded-lg border text-[11px] font-mono font-semibold transition ${
                        tokenDelta === val
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : val > 0
                          ? 'bg-slate-800/40 hover:bg-slate-800 text-emerald-400 border-slate-800'
                          : 'bg-slate-800/40 hover:bg-slate-800 text-rose-400 border-slate-800'
                      }`}
                    >
                      {val > 0 ? `+${val.toLocaleString()}` : val.toLocaleString()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preview Result */}
              <div className="p-3 bg-purple-950/20 border border-purple-800/30 rounded-xl flex items-center justify-between">
                <span className="text-xs text-purple-300">Dự kiến sau khi đổi:</span>
                <span className="text-sm font-mono font-bold text-white">
                  {Math.max(0, (selectedUserForToken.token_balance ?? 0) + (Number(tokenDelta) || 0)).toLocaleString()}{' '}
                  <span className="text-[11px] text-purple-400">tokens</span>
                </span>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedUserForToken(null)}
                  className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition"
                >
                  Đóng
                </button>
                <button
                  type="submit"
                  disabled={submittingToken || tokenDelta === 0}
                  className="flex-1 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white rounded-xl font-bold shadow-lg shadow-amber-600/20 transition active:scale-95 disabled:opacity-50 flex items-center justify-center space-x-1.5"
                >
                  {submittingToken ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span>Xác Nhận Cập Nhật</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
