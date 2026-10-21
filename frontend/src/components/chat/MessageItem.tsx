import React, { useState } from 'react';
import { ChatMessage, DiscussionRound } from '../../types';
import { chatService } from '../../services/chatService';
import { useToast } from '../../context/ToastContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Bot,
  User,
  Copy,
  Check,
  FileDown,
  Cpu,
  Sparkles,
  Loader2,
  FileText,
  Users,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  RefreshCw,
  ArrowUpRight,
  ArrowDownLeft
} from 'lucide-react';

import { BlockRenderer } from './BlockRenderer';

interface MessageItemProps {
  message: ChatMessage;
  onSuggestionClick?: (text: string) => void;
  onFetchFile?: (filePath: string) => void;
}

const DiscussionHistoryAccordion: React.FC<{
  history: DiscussionRound[];
  roundsCount?: number;
}> = ({ history, roundsCount }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeRoundTab, setActiveRoundTab] = useState(0);

  if (!history || history.length === 0) return null;

  const lastRound = history[history.length - 1];
  const isAllPassed = lastRound.verdict === 'PASSED';

  return (
    <div className="border border-indigo-500/30 bg-slate-950/80 rounded-xl overflow-hidden shadow-md my-2 w-full">
      {/* Header bar */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2.5 sm:p-3 bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-900/50 hover:bg-slate-800/80 border-b border-indigo-500/20 text-left transition cursor-pointer"
      >
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="w-6 h-6 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
            <Users className="w-3.5 h-3.5" />
          </div>
          <div className="truncate">
            <div className="text-xs font-bold text-indigo-200 flex items-center space-x-2">
              <span>Biên Bản Thảo Luận & Phản Biện 2 AI</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">
                {roundsCount || history.length} Vòng
              </span>
            </div>
            <div className="text-[10px] text-slate-400 truncate">
              Cơ chế Actor-Critic: AI Thực Thi sửa bản nháp theo góp ý của AI Phản Biện
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0 ml-2">
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex items-center space-x-1 ${
              isAllPassed
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}
          >
            {isAllPassed ? (
              <>
                <CheckCircle2 className="w-3 h-3" />
                <span>Đạt Chuẩn (PASSED)</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-3 h-3" />
                <span>Hoàn tất ({lastRound.score})</span>
              </>
            )}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </div>
      </button>

      {/* Accordion Content */}
      {isOpen && (
        <div className="p-3 space-y-3 bg-slate-900/60">
          {/* Tabs for rounds */}
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 border-b border-slate-800">
            {history.map((r, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setActiveRoundTab(idx)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition cursor-pointer shrink-0 ${
                  activeRoundTab === idx
                    ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-750'
                }`}
              >
                Vòng {r.round} {r.verdict === 'PASSED' ? '✓' : `(${r.score})`}
              </button>
            ))}
          </div>

          {/* Active Round Details */}
          {history[activeRoundTab] && (() => {
            const currentRound = history[activeRoundTab];
            return (
              <div className="space-y-2.5 text-xs">
                {/* AI 1: Worker Draft */}
                <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-2.5 space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-blue-300 font-semibold border-b border-slate-800 pb-1">
                    <span>🤖 AI Thực Thi ({currentRound.worker_model})</span>
                    <span className="text-[10px] text-slate-400">Bản dự thảo Vòng {currentRound.round}</span>
                  </div>
                  <div className="max-h-48 overflow-y-auto font-mono text-[11px] text-slate-300 whitespace-pre-wrap bg-black/30 p-2 rounded border border-white/5">
                    {currentRound.worker_draft}
                  </div>
                </div>

                {/* AI 2: Critic Feedback */}
                <div
                  className={`border rounded-lg p-2.5 space-y-1 ${
                    currentRound.verdict === 'PASSED'
                      ? 'bg-emerald-950/20 border-emerald-800/40'
                      : 'bg-amber-950/20 border-amber-800/40'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-semibold border-b border-slate-800/50 pb-1">
                    <span className={currentRound.verdict === 'PASSED' ? 'text-emerald-300' : 'text-amber-300'}>
                      🔍 AI Phản Biện ({currentRound.evaluator_model})
                    </span>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <span className="text-slate-400">Điểm:</span>
                      <span className="font-bold text-white bg-slate-800 px-1.5 py-0.2 rounded font-mono">
                        {currentRound.score}
                      </span>
                      <span
                        className={`font-bold px-1.5 py-0.2 rounded ${
                          currentRound.verdict === 'PASSED'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-amber-500/20 text-amber-400'
                        }`}
                      >
                        {currentRound.verdict}
                      </span>
                    </div>
                  </div>
                  <div className="max-h-48 overflow-y-auto text-[11px] text-slate-300 whitespace-pre-wrap bg-black/30 p-2 rounded border border-white/5">
                    {currentRound.evaluator_feedback}
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  onSuggestionClick,
  onFetchFile,
}) => {
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [exportingDocx, setExportingDocx] = useState(false);

  const isUser = message.role === 'user';
  const fetchFileMatches = !isUser && message.content ? [...message.content.matchAll(/\[(?:FETCH_FILE|READ_FILE):\s*([^\]]+)\]/gi)] : [];
  const requestedFiles = Array.from(new Set(fetchFileMatches.map((m) => m[1].trim())));

  const handleCopyText = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    showToast('Đã sao chép nội dung tin nhắn!', 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportDocx = async () => {
    setExportingDocx(true);
    try {
      // Clean title from first heading if exists
      const match = message.content.match(/^#\s+(.+)$/m);
      const filename = match ? `${match[1].trim().replace(/[\\/:*?"<>|]/g, '_')}.docx` : 'Antigravity_Bai_Viet.docx';

      const blob = await chatService.exportToDocx(message.content, filename);
      chatService.downloadBlob(blob, filename);
      showToast(`Đã xuất file Word: ${filename}`, 'success');
    } catch (err: any) {
      showToast(err.message || 'Lỗi xuất file Word', 'error');
    } finally {
      setExportingDocx(false);
    }
  };

  return (
    <div className={`flex items-start space-x-3 w-full ${isUser ? 'justify-end ml-auto' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shrink-0 shadow-md">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div
        className={`rounded-2xl p-4 text-sm shadow-md space-y-2 overflow-hidden ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm max-w-2xl'
            : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-sm flex-1'
        }`}
      >
        {/* Attached files / images previews if any */}
        {message.images && message.images.length > 0 && (
          <div className="flex flex-wrap gap-2 pb-2">
            {message.images.map((img, idx) => (
              <img
                key={idx}
                src={img}
                alt="Upload preview"
                className="max-h-48 rounded-xl border border-white/20 object-cover shadow"
              />
            ))}
          </div>
        )}

        {message.files && message.files.length > 0 && (
          <div className="flex flex-wrap gap-2 pb-2">
            {message.files.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-black/20 text-xs text-white/90 border border-white/10"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>{file.name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Dual AI Discussion History (Accordion) */}
        {!isUser && message.discussion_history && message.discussion_history.length > 0 && (
          <DiscussionHistoryAccordion
            history={message.discussion_history}
            roundsCount={message.rounds_count}
          />
        )}

        {/* Message Content */}
        {isUser ? (
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
        ) : message.blocks && message.blocks.length > 0 ? (
          <BlockRenderer blocks={message.blocks} onSuggestionClick={onSuggestionClick} />
        ) : (
          <div className="prose-dark overflow-x-auto">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* On-Demand File Requests from AI */}
        {!isUser && requestedFiles.length > 0 && onFetchFile && (
          <div className="my-2.5 p-3 rounded-xl bg-indigo-950/50 border border-indigo-500/40 text-indigo-200 shadow-sm">
            <div className="text-xs font-semibold flex items-center space-x-1.5 mb-2 text-indigo-300">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>AI yêu cầu xem nội dung tệp tin để phân tích tiếp:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {requestedFiles.map((fp) => (
                <button
                  key={fp}
                  type="button"
                  onClick={() => onFetchFile(fp)}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow transition active:scale-95 cursor-pointer"
                  title={`Bấm để nạp nội dung file ${fp} cho AI`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Nạp tệp: {fp}</span>
                  <ArrowUpRight className="w-3 h-3 ml-0.5 opacity-80" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Footer meta for Assistant */}
        {!isUser && (
          <div className="flex items-center justify-between pt-2.5 border-t border-slate-800/80 text-xs text-slate-400">
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              {message.model && (
                <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800 text-[10px]">
                  <Cpu className="w-3 h-3 text-purple-400" />
                  <span>{message.model}</span>
                </span>
              )}
              {message.skill_used && (
                <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 text-[10px]">
                  <Sparkles className="w-3 h-3 text-purple-400" />
                  <span>{message.skill_used}</span>
                </span>
              )}

              {/* Thống kê Token đã gửi và Token đã nhận */}
              {message.tokens && (() => {
                const rawP = message.tokens.prompt_tokens ?? message.tokens.prompt ?? 0;
                const rawC = message.tokens.completion_tokens ?? message.tokens.completion ?? 0;
                let tot = message.tokens.total_tokens ?? message.tokens.total ?? 0;
                let p = rawP;
                let c = rawC;

                if (p === 0 && tot > c) {
                  p = tot - c;
                }
                if (c === 0 && tot > p) {
                  c = tot - p;
                }
                if (tot === 0) {
                  tot = p + c;
                }

                return (
                  <>
                    <span
                      className="flex items-center space-x-1 px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/25 text-[10px] font-mono shadow-sm"
                      title="Số lượng Token đầu vào (Input / Prompt Tokens)"
                    >
                      <ArrowUpRight className="w-3 h-3 text-sky-400 shrink-0" />
                      <span>Input: {p.toLocaleString()} tok</span>
                    </span>

                    <span
                      className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-[10px] font-mono shadow-sm"
                      title="Số lượng Token đầu ra (Output / Completion Tokens)"
                    >
                      <ArrowDownLeft className="w-3 h-3 text-emerald-400 shrink-0" />
                      <span>Output: {c.toLocaleString()} tok</span>
                    </span>

                    <span
                      className="hidden sm:flex items-center space-x-1 px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 text-[10px] font-mono"
                      title="Tổng số Token tiêu thụ trong lượt trả lời này"
                    >
                      <span>Tổng: {tot.toLocaleString()}</span>
                    </span>
                  </>
                );
              })()}
            </div>

            <div className="flex items-center space-x-1.5">
              <button
                onClick={handleCopyText}
                className="flex items-center space-x-1 px-2 py-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition text-xs"
                title="Sao chép Markdown"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Đã chép' : 'Copy'}</span>
              </button>

              <button
                onClick={handleExportDocx}
                disabled={exportingDocx}
                className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-600 text-indigo-300 hover:text-white transition text-xs font-medium border border-indigo-500/20 active:scale-95 disabled:opacity-50"
                title="Tải văn bản Microsoft Word (.docx) chuẩn Heading và Bảng biểu"
              >
                {exportingDocx ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <FileDown className="w-3.5 h-3.5" />
                )}
                <span>{exportingDocx ? 'Đang tạo Word...' : 'Tải DOCX'}</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 shadow-md">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
