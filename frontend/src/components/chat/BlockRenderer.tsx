import React, { useState } from 'react';
import { ContentBlock } from '../../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Brain,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Code2,
  Table as TableIcon,
  Info,
  Lightbulb,
  AlertTriangle,
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  ExternalLink,
  Sigma,
  GitGraph,
  Quote,
  CheckSquare,
  Square,
  FileSpreadsheet,
  Download,
  Image as ImageIcon
} from 'lucide-react';
import { useToast } from '../../context/ToastContext';

interface BlockRendererProps {
  blocks: ContentBlock[];
  onSuggestionClick?: (text: string) => void;
}

export const BlockRenderer: React.FC<BlockRendererProps> = ({ blocks, onSuggestionClick }) => {
  return (
    <div className="space-y-4 w-full">
      {blocks.map((block, idx) => (
        <SingleBlockItem key={idx} block={block} onSuggestionClick={onSuggestionClick} />
      ))}
    </div>
  );
};

const SingleBlockItem: React.FC<{ block: ContentBlock; onSuggestionClick?: (text: string) => void }> = ({
  block,
  onSuggestionClick,
}) => {
  const { showToast } = useToast();
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [showDiagramCode, setShowDiagramCode] = useState(false);

  const handleCopy = (textToCopy: string, label: string = 'Đã sao chép!') => {
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    showToast(label, 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  switch (block.type) {
    case 'thought':
      return (
        <div className="rounded-xl border border-purple-500/25 bg-purple-950/20 overflow-hidden shadow-sm">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between px-3.5 py-2.5 bg-purple-900/20 hover:bg-purple-900/30 transition text-xs text-purple-300 font-medium"
          >
            <div className="flex items-center space-x-2">
              <Brain className="w-4 h-4 text-purple-400 animate-pulse" />
              <span>{block.title || 'Quá trình suy luận (Thinking Process)'}</span>
              <span className="px-1.5 py-0.5 rounded-full bg-purple-500/20 text-[10px] text-purple-200 border border-purple-500/30">
                AI Reasoning
              </span>
            </div>
            <div className="flex items-center space-x-1 text-purple-400">
              <span className="text-[11px]">{expanded ? 'Thu gọn' : 'Xem chi tiết'}</span>
              {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          </button>
          {expanded && (
            <div className="p-3 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed border-t border-purple-500/20 bg-black/30 max-h-96 overflow-y-auto">
              {block.content}
            </div>
          )}
        </div>
      );

    case 'code':
      return (
        <div className="rounded-xl border border-slate-700/80 bg-[#0d1117] overflow-hidden shadow-lg my-2">
          <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-300">
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
              </div>
              <span className="font-mono text-purple-400 font-medium uppercase text-[11px] tracking-wider ml-1">
                {block.language || 'code'}
              </span>
              {block.filename && (
                <span className="text-slate-400 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                  {block.filename}
                </span>
              )}
              {block.lines_count ? (
                <span className="text-slate-500 text-[10px]">({block.lines_count} dòng)</span>
              ) : null}
            </div>
            <button
              onClick={() => handleCopy(block.content || '', 'Đã sao chép mã nguồn!')}
              className="flex items-center space-x-1 px-2 py-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition text-xs"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Đã chép' : 'Copy code'}</span>
            </button>
          </div>
          <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed selection:bg-purple-900">
            <code>{block.content}</code>
          </pre>
        </div>
      );

    case 'diagram':
      return (
        <div className="rounded-xl border border-indigo-500/30 bg-slate-900/90 overflow-hidden shadow-md my-2">
          <div className="flex items-center justify-between px-3.5 py-2 bg-indigo-950/40 border-b border-indigo-500/20 text-xs text-indigo-300">
            <div className="flex items-center space-x-2">
              <GitGraph className="w-4 h-4 text-indigo-400" />
              <span className="font-medium">{block.title || 'Sơ đồ trực quan (Mermaid)'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowDiagramCode(!showDiagramCode)}
                className="px-2 py-0.5 rounded bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-200 text-[11px] transition"
              >
                {showDiagramCode ? 'Xem biểu đồ' : 'Xem mã nguồn'}
              </button>
              <button
                onClick={() => handleCopy(block.code || '', 'Đã sao chép mã Mermaid!')}
                className="flex items-center space-x-1 px-2 py-0.5 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition text-[11px]"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>Copy</span>
              </button>
            </div>
          </div>
          {showDiagramCode ? (
            <pre className="p-3 text-xs font-mono text-slate-300 bg-[#0d1117] overflow-x-auto">
              <code>{block.code}</code>
            </pre>
          ) : (
            <div className="p-4 bg-slate-950 flex flex-col items-center justify-center">
              <pre className="text-xs font-mono text-indigo-200 p-3 rounded-lg bg-indigo-950/30 border border-indigo-500/20 max-w-full overflow-x-auto">
                <code>{block.code}</code>
              </pre>
              <span className="text-[10px] text-slate-500 mt-2">
                * Hỗ trợ tự động render đồ họa Mermaid SVG trực tiếp
              </span>
            </div>
          )}
        </div>
      );

    case 'table': {
      const copyTableAsCsv = () => {
        if (!block.headers || !block.rows) return;
        const csvRows = [
          block.headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(','),
          ...block.rows.map((row) => row.map((cell) => `"${(cell || '').replace(/"/g, '""')}"`).join(',')),
        ];
        handleCopy(csvRows.join('\n'), 'Đã sao chép bảng dưới dạng CSV!');
      };

      return (
        <div className="rounded-xl border border-slate-800 bg-slate-900/80 overflow-hidden shadow my-2">
          <div className="flex items-center justify-between px-3.5 py-2 bg-slate-950 border-b border-slate-800 text-xs text-slate-400">
            <div className="flex items-center space-x-2">
              <TableIcon className="w-3.5 h-3.5 text-purple-400" />
              <span>Bảng dữ liệu</span>
              {block.headers && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  {block.headers.length} cột × {block.rows?.length || 0} dòng
                </span>
              )}
            </div>
            <button
              onClick={copyTableAsCsv}
              className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition"
            >
              <FileSpreadsheet className="w-3 h-3 text-emerald-400" />
              <span>Chép CSV</span>
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              {block.headers && (
                <thead>
                  <tr className="bg-slate-800/60 border-b border-slate-700 text-slate-200">
                    {block.headers.map((h, i) => (
                      <th
                        key={i}
                        className={`p-2.5 font-semibold ${
                          block.alignments?.[i] === 'right'
                            ? 'text-right'
                            : block.alignments?.[i] === 'center'
                            ? 'text-center'
                            : 'text-left'
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              {block.rows && (
                <tbody className="divide-y divide-slate-800">
                  {block.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-800/40 transition">
                      {row.map((cell, cIdx) => (
                        <td
                          key={cIdx}
                          className={`p-2.5 text-slate-300 ${
                            block.alignments?.[cIdx] === 'right'
                              ? 'text-right'
                              : block.alignments?.[cIdx] === 'center'
                              ? 'text-center'
                              : 'text-left'
                          }`}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              )}
            </table>
          </div>
        </div>
      );
    }

    case 'callout': {
      const variantStyles = {
        note: {
          border: 'border-blue-500/30 bg-blue-500/10 text-blue-200',
          titleColor: 'text-blue-400',
          icon: <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />,
        },
        info: {
          border: 'border-blue-500/30 bg-blue-500/10 text-blue-200',
          titleColor: 'text-blue-400',
          icon: <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />,
        },
        tip: {
          border: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
          titleColor: 'text-emerald-400',
          icon: <Lightbulb className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
        },
        warning: {
          border: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
          titleColor: 'text-amber-400',
          icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
        },
        caution: {
          border: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
          titleColor: 'text-rose-400',
          icon: <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
        },
        important: {
          border: 'border-purple-500/30 bg-purple-500/10 text-purple-200',
          titleColor: 'text-purple-400',
          icon: <Sparkles className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />,
        },
        success: {
          border: 'border-green-500/30 bg-green-500/10 text-green-200',
          titleColor: 'text-green-400',
          icon: <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />,
        },
      };

      const style = variantStyles[block.variant || 'note'] || variantStyles.note;

      return (
        <div className={`rounded-xl border p-3.5 my-2 flex items-start space-x-3 ${style.border}`}>
          {style.icon}
          <div className="flex-1 space-y-1 text-xs">
            {block.title && <div className={`font-semibold ${style.titleColor}`}>{block.title}</div>}
            <div className="prose-dark leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content || ''}</ReactMarkdown>
            </div>
          </div>
        </div>
      );
    }

    case 'math':
      return (
        <div className="rounded-xl border border-teal-500/30 bg-slate-900/90 p-4 text-center my-2 shadow relative group">
          <div className="flex items-center justify-between text-xs text-teal-400 mb-2">
            <div className="flex items-center space-x-1.5">
              <Sigma className="w-3.5 h-3.5" />
              <span className="font-medium">Công thức Toán học (LaTeX)</span>
            </div>
            <button
              onClick={() => handleCopy(block.formula || '', 'Đã chép công thức LaTeX!')}
              className="flex items-center space-x-1 text-[11px] text-slate-400 hover:text-slate-200 opacity-0 group-hover:opacity-100 transition"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Đã chép' : 'Copy LaTeX'}</span>
            </button>
          </div>
          <div className="text-base font-serif text-teal-200 tracking-wider py-1 select-all overflow-x-auto">
            $${block.formula}$$
          </div>
        </div>
      );

    case 'citations':
      return (
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 my-2 space-y-2.5">
          <div className="flex items-center space-x-1.5 text-xs text-slate-400 font-medium">
            <ExternalLink className="w-3.5 h-3.5 text-blue-400" />
            <span>{block.title || 'Nguồn tham khảo từ Google Web Search'}</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {block.sources?.map((s, idx) => (
              <a
                key={idx}
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-start justify-between p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 transition group text-xs"
              >
                <div className="space-y-0.5 overflow-hidden pr-2">
                  <div className="font-medium text-slate-200 group-hover:text-purple-300 truncate">
                    {s.title}
                  </div>
                  {s.domain && <div className="text-[10px] text-slate-500">{s.domain}</div>}
                </div>
                <ExternalLink className="w-3 h-3 text-slate-500 group-hover:text-purple-400 shrink-0 mt-0.5" />
              </a>
            ))}
          </div>
        </div>
      );

    case 'key_value':
      return (
        <div className="rounded-xl border border-purple-500/20 bg-slate-950/60 p-3.5 my-2 space-y-2">
          {block.title && (
            <div className="text-xs font-semibold text-purple-300 flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>{block.title}</span>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {block.items?.map((item, idx) => (
              <div key={idx} className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-0.5">
                <div className="text-[11px] text-slate-400 font-medium">{item.key}</div>
                <div className="text-slate-200 font-semibold">{item.value}</div>
              </div>
            ))}
          </div>
        </div>
      );

    case 'task_list':
      return (
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 my-2 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Danh sách việc cần làm (Checklist)</span>
            {block.total ? (
              <span className="text-[10px] text-emerald-400 font-semibold">
                {block.completed_count}/{block.total} hoàn thành
              </span>
            ) : null}
          </div>
          <div className="space-y-1.5 text-xs">
            {block.items?.map((it, idx) => (
              <div
                key={idx}
                className={`flex items-start space-x-2 p-1.5 rounded ${
                  it.completed ? 'text-slate-400 line-through' : 'text-slate-200'
                }`}
              >
                {it.completed ? (
                  <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <Square className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                )}
                <span>{it.task}</span>
              </div>
            ))}
          </div>
        </div>
      );

    case 'suggestion':
      return (
        <div className="rounded-xl border border-purple-500/20 bg-purple-950/10 p-3.5 my-2 space-y-2">
          <div className="flex items-center space-x-1.5 text-xs text-purple-300 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>{block.title || 'Gợi ý câu hỏi tiếp theo'}</span>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {block.items?.map((sug, idx) => (
              <button
                key={idx}
                onClick={() => onSuggestionClick && onSuggestionClick(sug)}
                className="text-left text-xs px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-purple-900/30 text-slate-300 hover:text-purple-200 border border-slate-800 hover:border-purple-500/40 transition active:scale-95 shadow-sm"
              >
                💬 {sug}
              </button>
            ))}
          </div>
        </div>
      );

    case 'quote':
      return (
        <div className="relative rounded-xl border-l-4 border-purple-500 bg-slate-900/60 pl-4 pr-3 py-3 my-2 text-xs italic text-slate-300">
          <Quote className="w-4 h-4 text-purple-400/40 absolute right-3 top-3" />
          <div className="leading-relaxed">{block.content}</div>
        </div>
      );

    case 'image':
      return (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-2 my-2 space-y-1.5">
          <img
            src={block.url}
            alt={block.alt || 'AI Artwork'}
            className="w-full max-h-96 object-cover rounded-lg shadow"
            loading="lazy"
          />
          {block.caption && (
            <div className="text-[11px] text-center text-slate-400 italic py-1">{block.caption}</div>
          )}
        </div>
      );

    case 'text':
    default:
      return (
        <div className="prose-dark overflow-x-auto leading-relaxed text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content || ''}</ReactMarkdown>
        </div>
      );
  }
};
