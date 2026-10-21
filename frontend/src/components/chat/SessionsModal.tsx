import React from 'react';
import { History, X, Trash2, ArrowRight, MessageSquare } from 'lucide-react';
import { ChatMessage } from '../../types';

export interface SavedSession {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: ChatMessage[];
}

interface SessionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: SavedSession[];
  currentSessionId: string;
  onSelectSession: (session: SavedSession) => void;
  onDeleteSession: (sessionId: string) => void;
}

export const SessionsModal: React.FC<SessionsModalProps> = ({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
}) => {
  if (!isOpen) return null;

  const sortedSessions = [...sessions].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0));

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full space-y-4 shadow-2xl flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">Lịch Sử Các Cuộc Trò Chuyện</h3>
              <p className="text-[11px] text-slate-400">Các phiên hội thoại được lưu an toàn trong trình duyệt của bạn</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 min-h-[220px]">
          {sortedSessions.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs flex flex-col items-center justify-center">
              <MessageSquare className="w-8 h-8 text-slate-600 mb-2 opacity-60" />
              <span>Chưa có phiên trò chuyện nào trong trình duyệt.</span>
            </div>
          ) : (
            sortedSessions.map((s) => {
              const isCurrent = s.id === currentSessionId;
              const timeStr = new Date(s.updated_at || s.created_at).toLocaleString('vi-VN');
              const msgs = s.messages || [];
              const lastMsg = msgs.length ? msgs[msgs.length - 1].content || '' : 'Chưa có tin nhắn';

              return (
                <div
                  key={s.id}
                  className={`bg-slate-950/80 border ${
                    isCurrent
                      ? 'border-blue-500/60 shadow-md shadow-blue-500/10'
                      : 'border-slate-800 hover:border-slate-700'
                  } rounded-xl p-3 flex items-center justify-between gap-3 transition`}
                >
                  <div
                    className="space-y-1 min-w-0 flex-1 cursor-pointer"
                    onClick={() => onSelectSession(s)}
                  >
                    <div className="flex items-center space-x-2">
                      <h4 className="font-bold text-sm text-slate-100 truncate">
                        {s.title || 'Cuộc trò chuyện'}
                      </h4>
                      {isCurrent && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                          HIỆN TẠI
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 truncate max-w-md">{lastMsg}</p>
                    <div className="flex items-center space-x-2 text-[10px] text-slate-500 font-mono">
                      <span>{timeStr}</span>
                      <span>•</span>
                      <span>{msgs.length} tin nhắn</span>
                      <span>•</span>
                      <span className="text-blue-400">{s.id}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1.5 shrink-0">
                    <button
                      onClick={() => onSelectSession(s)}
                      className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition flex items-center space-x-1"
                      title="Mở phiên này"
                    >
                      <span>Mở</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => onDeleteSession(s.id)}
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
                      title="Xóa phiên này"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end pt-2 border-t border-slate-800 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
