import React, { useState, useEffect, useRef } from 'react';
import { ChatMessage, Skill } from '../../types';
import { chatService } from '../../services/chatService';
import { skillService } from '../../services/skillService';
import { useToast } from '../../context/ToastContext';
import { MessageItem } from './MessageItem';
import { SessionsModal, SavedSession } from './SessionsModal';
import {
  Send,
  Loader2,
  Paperclip,
  Image as ImageIcon,
  X,
  Sparkles,
  Globe,
  Trash2,
  Cpu,
  Bot,
  SlidersHorizontal,
  Plus,
  BrainCircuit,
  Copy,
  History,
  Users,
  FolderOpen,
  FolderSearch,
  Folder,
  FileText,
  Search,
  Eye
} from 'lucide-react';

const MODEL_GROUPS = [
  {
    label: 'Google Gemini',
    models: [
      { id: 'gemini-4-argon', name: 'Gemini 4 Argon (Suy luận nâng cao)' },
      { id: 'gemini-3.8-flash-tiered', name: 'Gemini 3.8 Flash (High - Nhanh & Mới Nhất)' },
      { id: 'gemini-3-flash', name: 'Gemini 3 Flash (Cân Bằng)' },
      { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash' },
    ]
  },
  {
    label: 'Anthropic Claude',
    models: [
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6 (Thinking - Tư Duy Sâu)' },
      { id: 'claude-opus-4-6-thinking', name: 'Claude Opus 4.6 (Thinking - Nâng Cao)' },
    ]
  },
  {
    label: '🎨 Tạo Hình Ảnh (AI Image)',
    models: [
      { id: 'flux-image-generator', name: '🎨 Flux.1 Vẽ Ảnh' },
    ]
  }
];

interface ChatTabProps {
  selectedSkillId: string;
  onSkillChange: (skillId: string) => void;
}

const SESSIONS_STORAGE_KEY = 'antigravity_sessions_store';
const CURRENT_SESSION_KEY = 'antigravity_current_session';

const MANIFEST_PATTERNS = [
  'readme.md', 'readme.txt', 'readme', 'read_me.md',
  'package.json', 'requirements.txt', 'requirements-dev.txt',
  'composer.json', 'go.mod', 'pom.xml', 'build.gradle', 'cargo.toml',
  'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
  'tsconfig.json', 'vite.config.ts', 'vite.config.js',
  'next.config.js', 'next.config.mjs', 'next.config.ts', '.env.example'
];

const isManifestFileName = (name: string): boolean => {
  const base = name.split('/').pop()?.toLowerCase() || '';
  if (MANIFEST_PATTERNS.includes(base)) return true;
  if (base.startsWith('readme') || base.startsWith('docker-compose')) return true;
  return false;
};

const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const buildAsciiTree = (paths: string[], maxEntries = 120): string => {
  if (!paths || paths.length === 0) return '';
  const tree: Record<string, any> = {};
  for (const p of [...paths].sort()) {
    const parts = p.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '').split('/').filter(Boolean);
    let curr = tree;
    for (const part of parts.slice(0, -1)) {
      if (!curr[part]) curr[part] = {};
      curr = curr[part];
    }
    if (parts.length > 0) {
      curr[parts[parts.length - 1]] = null;
    }
  }

  const lines: string[] = [];
  const walk = (d: Record<string, any>, prefix = '') => {
    const keys = Object.keys(d);
    for (let idx = 0; idx < keys.length; idx++) {
      if (lines.length >= maxEntries) {
        lines.push(`${prefix}... (và thêm ${paths.length - maxEntries} file khác)`);
        return;
      }
      const k = keys[idx];
      const isLast = idx === keys.length - 1;
      const connector = isLast ? '└── ' : '├── ';
      const val = d[k];
      if (val === null) {
        lines.push(`${prefix}${connector}📄 ${k}`);
      } else {
        lines.push(`${prefix}${connector}📁 ${k}/`);
        const newPrefix = prefix + (isLast ? '    ' : '│   ');
        walk(val, newPrefix);
      }
    }
  };
  walk(tree);
  return lines.join('\n');
};

export const ChatTab: React.FC<ChatTabProps> = ({ selectedSkillId, onSkillChange }) => {
  const { showToast } = useToast();

  const [skills, setSkills] = useState<Skill[]>([]);
  const [model, setModel] = useState('gemini-3.8-flash-tiered');
  const [webSearch, setWebSearch] = useState(true);
  const [thinking, setThinking] = useState(false);
  const [dualAiMode, setDualAiMode] = useState(false);
  const [evaluatorModel, setEvaluatorModel] = useState('claude-sonnet-4-6');
  const [maxRounds, setMaxRounds] = useState(3);

  // Sessions Store
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem(CURRENT_SESSION_KEY) || 'sess_' + Math.random().toString(36).substring(2, 9);
  });

  const [isSessionsModalOpen, setIsSessionsModalOpen] = useState(false);

  // Workspace files cache for On-Demand file loading
  const workspaceFilesRef = useRef<Map<string, { name: string; size: number; file?: File; fullPath?: string }>>(new Map());
  const [workspaceFilesList, setWorkspaceFilesList] = useState<Array<{ name: string; size: number; isManifest?: boolean; fullPath?: string }>>([]);
  const [isFilesDrawerOpen, setIsFilesDrawerOpen] = useState(false);
  const [currentWorkspaceFolder, setCurrentWorkspaceFolder] = useState<string>('');
  const [searchFileFilter, setSearchFileFilter] = useState('');

  // Helper to load sessions store
  const getSessionsStore = (): Record<string, SavedSession> => {
    try {
      const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  };

  const saveSessionsStore = (store: Record<string, SavedSession>) => {
    try {
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(store));
    } catch (e) {
      console.error('Failed to save sessions store', e);
    }
  };

  // Load messages for current session
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const store = getSessionsStore();
    const currentId = localStorage.getItem(CURRENT_SESSION_KEY) || '';
    if (currentId && store[currentId] && store[currentId].messages) {
      return store[currentId].messages;
    }
    return [
      {
        id: 'msg_welcome',
        role: 'assistant',
        content: 'Xin chào! Tôi là **Antigravity AI Gateway**. Bạn có thể đặt câu hỏi, yêu cầu lập trình, viết content chuẩn SEO, dịch thuật hoặc đính kèm tài liệu phân tích bất cứ lúc nào.',
        timestamp: new Date().toLocaleTimeString(),
        model: 'gemini-3.8-flash-tiered',
      },
    ];
  });

  const [inputPrompt, setInputPrompt] = useState('');
  const [sending, setSending] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<Array<{ name: string; data: string }>>([]);
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [isLocalFolderModalOpen, setIsLocalFolderModalOpen] = useState(false);
  const [localFolderPathInput, setLocalFolderPathInput] = useState('');
  const [isScanningFolder, setIsScanningFolder] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Xử lý nạp ảnh từ Clipboard Data (hỗ trợ Snipping Tool, Win+Shift+S, Copy Image trên web/máy)
  const processClipboardData = (clipboardData: DataTransfer | null): boolean => {
    if (!clipboardData) return false;

    const imageFiles: File[] = [];

    // 1. Kiểm tra clipboardData.files (file copy từ máy tính / Explorer)
    if (clipboardData.files && clipboardData.files.length > 0) {
      for (let i = 0; i < clipboardData.files.length; i++) {
        const file = clipboardData.files[i];
        if (file.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)) {
          imageFiles.push(file);
        }
      }
    }

    // 2. Kiểm tra clipboardData.items (ảnh screenshot từ Snipping Tool, Win+Shift+S, Copy Image trên web)
    if (imageFiles.length === 0 && clipboardData.items && clipboardData.items.length > 0) {
      for (let i = 0; i < clipboardData.items.length; i++) {
        const item = clipboardData.items[i];
        if (item.type.startsWith('image/') || item.type.indexOf('image') !== -1) {
          const file = item.getAsFile();
          if (file) {
            imageFiles.push(file);
          }
        }
      }
    }

    if (imageFiles.length === 0) return false;

    let loadedCount = 0;
    const newImages: string[] = [];
    for (const file of imageFiles) {
      const reader = new FileReader();
      reader.onload = () => {
        newImages.push(reader.result as string);
        loadedCount++;
        if (loadedCount === imageFiles.length) {
          setAttachedImages((prev) => [...prev, ...newImages]);
          showToast(`Đã dán ${newImages.length} ảnh từ clipboard!`, 'success');
        }
      };
      reader.readAsDataURL(file);
    }
    return true;
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    if (processClipboardData(e.clipboardData)) {
      e.preventDefault();
    }
  };

  // Bắt sự kiện Paste toàn cục trên cửa sổ khi người dùng bấm Ctrl + V
  useEffect(() => {
    const handleGlobalPaste = (e: ClipboardEvent) => {
      const active = document.activeElement;
      if (active && (active.tagName === 'INPUT' || (active.tagName === 'TEXTAREA' && active !== textareaRef.current))) {
        return;
      }
      if (processClipboardData(e.clipboardData)) {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };

    window.addEventListener('paste', handleGlobalPaste);
    return () => window.removeEventListener('paste', handleGlobalPaste);
  }, []);

  useEffect(() => {
    skillService.getSkills().then(setSkills).catch(() => {});
  }, []);

  // Save messages to session store whenever messages or sessionId changes
  useEffect(() => {
    localStorage.setItem(CURRENT_SESSION_KEY, sessionId);
    const store = getSessionsStore();
    const firstUserMsg = messages.find((m) => m.role === 'user')?.content || 'Cuộc trò chuyện mới';
    const title = firstUserMsg.slice(0, 40) + (firstUserMsg.length > 40 ? '...' : '');

    store[sessionId] = {
      id: sessionId,
      title: store[sessionId]?.title || title,
      created_at: store[sessionId]?.created_at || Date.now(),
      updated_at: Date.now(),
      messages,
    };
    saveSessionsStore(store);

    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sessionId]);

  const handleCreateNewSession = () => {
    const newId = 'sess_' + Math.random().toString(36).substring(2, 9);
    setSessionId(newId);
    setMessages([]);
    localStorage.setItem(CURRENT_SESSION_KEY, newId);
    showToast('Đã bắt đầu cuộc trò chuyện mới!', 'info');
  };

  const handleClearCurrentSession = () => {
    if (!window.confirm('Bạn có chắc muốn xóa nội dung cuộc trò chuyện hiện tại?')) return;
    setMessages([]);
    showToast('Đã xóa nội dung cuộc trò chuyện hiện tại!', 'info');
  };

  const handleSelectSession = (session: SavedSession) => {
    setSessionId(session.id);
    setMessages(session.messages || []);
    localStorage.setItem(CURRENT_SESSION_KEY, session.id);
    setIsSessionsModalOpen(false);
    showToast(`Đã chuyển sang phiên: ${session.id}`, 'info');
  };

  const handleDeleteSession = (idToDelete: string) => {
    if (!window.confirm(`Bạn có chắc muốn xóa phiên trò chuyện [${idToDelete}] khỏi trình duyệt?`)) return;
    const store = getSessionsStore();
    delete store[idToDelete];
    saveSessionsStore(store);

    if (idToDelete === sessionId) {
      handleCreateNewSession();
    }
    showToast('Đã xóa phiên trò chuyện!', 'info');
  };

  // Lọc file rác / file binary khi tải folder
  const isIgnoredFile = (filePath: string): boolean => {
    const lower = filePath.toLowerCase().replace(/\\/g, '/');
    const parts = lower.split('/');
    const ignoredDirs = [
      'node_modules', '.git', '__pycache__', 'dist', 'build', '.next',
      '.nuxt', '.venv', 'venv', 'env', '.idea', '.vscode', '__macosx',
      'coverage', 'bin', 'obj'
    ];
    for (const p of parts) {
      if (ignoredDirs.includes(p)) return true;
      if (p.startsWith('.') && !['.env.example', '.gitignore', '.oxlintrc.json'].includes(p)) return true;
    }
    const ignoredExts = [
      '.exe', '.dll', '.bin', '.pyc', '.class', '.jar', '.iso', '.dmg',
      '.tar', '.gz', '.7z', '.rar', '.ds_store', '.thumbs.db'
    ];
    for (const ext of ignoredExts) {
      if (lower.endsWith(ext)) return true;
    }
    return false;
  };

  // Đính kèm 1 hoặc nhiều file
  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const filesArray = Array.from(fileList);
    let readCount = 0;
    const newItems: Array<{ name: string; data: string }> = [];

    for (const file of filesArray) {
      const reader = new FileReader();
      reader.onload = () => {
        newItems.push({ name: file.name, data: reader.result as string });
        readCount++;
        if (readCount === filesArray.length) {
          setAttachedFiles((prev) => [...prev, ...newItems]);
          showToast(`Đã đính kèm ${newItems.length} file!`, 'success');
        }
      };
      reader.readAsDataURL(file);
    }
    e.target.value = '';
  };

  // Đính kèm cả thư mục từ máy tính theo Chế Độ On-Demand Mặc Định
  const handleFolderAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const filesToRead: Array<{ relPath: string; file: File; size: number }> = [];
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i];
      const relPath = (f as any).webkitRelativePath || f.name;
      if (!isIgnoredFile(relPath)) {
        filesToRead.push({ relPath, file: f, size: f.size });
      }
    }

    if (filesToRead.length === 0) {
      showToast('Không tìm thấy file mã nguồn hoặc tài liệu hợp lệ trong thư mục.', 'info');
      e.target.value = '';
      return;
    }

    // Xác định tên thư mục gốc
    const firstRel = filesToRead[0].relPath;
    const folderName = firstRel.includes('/') ? firstRel.split('/')[0] : 'project';

    // Lưu tất cả file vào workspace cache phía client
    for (const item of filesToRead) {
      workspaceFilesRef.current.set(item.relPath, {
        name: item.relPath,
        size: item.size,
        file: item.file,
      });
    }

    const filePaths = filesToRead.map((f) => f.relPath);
    const treeStr = buildAsciiTree(filePaths);
    const totalBytes = filesToRead.reduce((sum, f) => sum + f.size, 0);

    // Cập nhật danh sách file cho Modal/Drawer
    const filesList = filesToRead.map((f) => ({
      name: f.relPath,
      size: f.size,
      isManifest: isManifestFileName(f.relPath),
    }));
    setWorkspaceFilesList(filesList);
    setCurrentWorkspaceFolder(folderName);

    // Dựng tài liệu tóm tắt Markdown chuẩn On-Demand (Chỉ cây thư mục + danh sách tên file)
    const parts = [
      `📁 **TỔNG QUAN THƯ MỤC DỰ ÁN: \`${folderName}\`**`,
      `- Tổng số file: **${filesToRead.length}** file (Tổng dung lượng: **${formatFileSize(totalBytes)}**)`,
      `\n\`\`\`text\n📂 ${folderName}/\n${treeStr}\n\`\`\`\n`,
      `📋 **DANH MỤC CÁC FILE TRONG DỰ ÁN:**`,
      `| STT | File | Dung lượng |`,
      `| :--- | :--- | :--- |`
    ];

    filesToRead.slice(0, 200).forEach((f, idx) => {
      parts.push(`| ${idx + 1} | \`${f.relPath}\` | ${formatFileSize(f.size)} |`);
    });

    if (filesToRead.length > 200) {
      parts.push(`\n*... và ${filesToRead.length - 200} file khác (xem chi tiết trên sơ đồ cây).*\n`);
    }

    parts.push(
      `\n💡 **CHẾ ĐỘ TIẾT KIỆM TOKEN & NẠP THEO NHU CẦU (MẶC ĐỊNH):**\n` +
      `- Danh sách trên thể hiện toàn bộ các tệp và cấu trúc thư mục của dự án.\n` +
      `- Để tối ưu hóa token và tốc độ phản hồi, nội dung chi tiết của các tệp mã nguồn CHƯA được nạp sẵn.\n` +
      `- Khi bạn cần phân tích, đọc code hoặc xem chi tiết bất kỳ tệp nào, hãy yêu cầu trong câu trả lời theo cú pháp: ` +
      `\`[READ_FILE: đường_dẫn_file]\` (Ví dụ: \`[READ_FILE: src/index.ts]\`). ` +
      `Backend sẽ tự động đọc đúng tệp đó và gửi lại nội dung cho bạn tiếp tục hoàn thành câu trả lời.`
    );

    const markdownSummary = parts.join('\n');
    const folderDataUrl = 'data:text/markdown;base64,' + btoa(unescape(encodeURIComponent(markdownSummary)));

    // Đính kèm 1 mục tóm tắt duy nhất vào attachedFiles
    setAttachedFiles((prev) => [
      ...prev.filter((f) => !f.name.startsWith(`📁 ${folderName}`)),
      {
        name: `📁 ${folderName} (${filesToRead.length} files - On-Demand)`,
        data: folderDataUrl,
      },
    ]);

    showToast(`Đã nạp sơ đồ thư mục ${folderName} (${filesToRead.length} file - Chế độ On-Demand)!`, 'success');
    e.target.value = '';
  };

  // Quét thư mục từ đường dẫn đĩa cứng
  const handleScanLocalFolder = async () => {
    if (!localFolderPathInput.trim()) return;
    setIsScanningFolder(true);
    try {
      const res = await chatService.readLocalFolder(localFolderPathInput.trim());
      if (res.success) {
        if (res.files && res.files.length > 0) {
          for (const f of res.files) {
            workspaceFilesRef.current.set(f.filename, {
              name: f.filename,
              size: f.size,
              fullPath: (f as any).full_path || f.filename,
            });
          }
          setWorkspaceFilesList(
            res.files.map((f) => ({
              name: f.filename,
              size: f.size,
              isManifest: isManifestFileName(f.filename),
              fullPath: (f as any).full_path || f.filename,
            }))
          );
          setCurrentWorkspaceFolder(res.folder_name);
        }

        setAttachedFiles((prev) => [
          ...prev,
          {
            name: `📁 ${res.folder_name} (${res.total_files} files - On-Demand)`,
            data: 'data:text/markdown;base64,' + btoa(unescape(encodeURIComponent(res.context_text))),
          },
        ]);
        showToast(`Đã nạp thành công thư mục ${res.folder_name} (${res.total_files} files - Chế độ On-Demand)!`, 'success');
        setIsLocalFolderModalOpen(false);
        setLocalFolderPathInput('');
      } else {
        showToast('Không thể quét thư mục này', 'error');
      }
    } catch (err: any) {
      showToast(err.message || 'Lỗi quét thư mục trên máy tính', 'error');
    } finally {
      setIsScanningFolder(false);
    }
  };

  // Kéo thả files / folders
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);

    const items = e.dataTransfer.items;
    if (!items || items.length === 0) return;

    const filesFound: Array<{ name: string; file: File }> = [];

    const traverseEntry = async (entry: any, path = '') => {
      if (entry.isFile) {
        const file: File = await new Promise((resolve) => entry.file(resolve));
        const fullPath = path ? `${path}/${file.name}` : file.name;
        if (!isIgnoredFile(fullPath)) {
          filesFound.push({ name: fullPath, file });
        }
      } else if (entry.isDirectory) {
        const dirReader = entry.createReader();
        const entries: any[] = await new Promise((resolve) => {
          dirReader.readEntries(resolve);
        });
        for (const child of entries) {
          await traverseEntry(child, path ? `${path}/${entry.name}` : entry.name);
        }
      }
    };

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const entry = typeof (item as any).webkitGetAsEntry === 'function' ? (item as any).webkitGetAsEntry() : null;
      if (entry) {
        await traverseEntry(entry);
      } else {
        const file = items[i].getAsFile();
        if (file && !isIgnoredFile(file.name)) {
          filesFound.push({ name: file.name, file });
        }
      }
    }

    if (filesFound.length > 0) {
      const hasDirectory = filesFound.some((f) => f.name.includes('/')) || filesFound.length > 3;

      if (hasDirectory) {
        // Áp dụng Chế Độ On-Demand Mặc Định
        const firstRel = filesFound[0].name;
        const folderName = firstRel.includes('/') ? firstRel.split('/')[0] : 'workspace';

        for (const item of filesFound) {
          workspaceFilesRef.current.set(item.name, {
            name: item.name,
            size: item.file.size,
            file: item.file,
          });
        }

        const filePaths = filesFound.map((f) => f.name);
        const treeStr = buildAsciiTree(filePaths);
        const totalBytes = filesFound.reduce((sum, f) => sum + f.file.size, 0);

        const filesList = filesFound.map((f) => ({
          name: f.name,
          size: f.file.size,
          isManifest: isManifestFileName(f.name),
        }));
        setWorkspaceFilesList(filesList);
        setCurrentWorkspaceFolder(folderName);

        // Dựng tài liệu tóm tắt Markdown chuẩn On-Demand (Chỉ cây thư mục + danh sách tên file)
        const parts = [
          `📁 **TỔNG QUAN THƯ MỤC DỰ ÁN: \`${folderName}\`**`,
          `- Tổng số file: **${filesFound.length}** file (Tổng dung lượng: **${formatFileSize(totalBytes)}**)`,
          `\n\`\`\`text\n📂 ${folderName}/\n${treeStr}\n\`\`\`\n`,
          `📋 **DANH MỤC CÁC FILE TRONG DỰ ÁN:**`,
          `| STT | File | Dung lượng |`,
          `| :--- | :--- | :--- |`
        ];

        filesFound.slice(0, 200).forEach((f, idx) => {
          parts.push(`| ${idx + 1} | \`${f.name}\` | ${formatFileSize(f.file.size)} |`);
        });

        if (filesFound.length > 200) {
          parts.push(`\n*... và ${filesFound.length - 200} file khác (xem chi tiết trên sơ đồ cây).*\n`);
        }

        parts.push(
          `\n💡 **CHẾ ĐỘ TIẾT KIỆM TOKEN & NẠP THEO NHU CẦU (MẶC ĐỊNH):**\n` +
          `- Danh sách trên thể hiện toàn bộ các tệp và cấu trúc thư mục của dự án.\n` +
          `- Để tối ưu hóa token và tốc độ phản hồi, nội dung chi tiết của các tệp mã nguồn CHƯA được nạp sẵn.\n` +
          `- Khi bạn cần phân tích, đọc code hoặc xem chi tiết bất kỳ tệp nào, hãy yêu cầu trong câu trả lời theo cú pháp: ` +
          `\`[READ_FILE: đường_dẫn_file]\` (Ví dụ: \`[READ_FILE: src/index.ts]\`). ` +
          `Backend sẽ tự động đọc đúng tệp đó và gửi lại nội dung cho bạn tiếp tục hoàn thành câu trả lời.`
        );

        const markdownSummary = parts.join('\n');
        const folderDataUrl = 'data:text/markdown;base64,' + btoa(unescape(encodeURIComponent(markdownSummary)));

        setAttachedFiles((prev) => [
          ...prev.filter((f) => !f.name.startsWith(`📁 ${folderName}`)),
          {
            name: `📁 ${folderName} (${filesFound.length} files - On-Demand)`,
            data: folderDataUrl,
          },
        ]);

        showToast(`Đã nạp sơ đồ thư mục ${folderName} (${filesFound.length} file - Chế độ On-Demand)!`, 'success');
      } else {
        // Phân loại file ảnh vs file văn bản/mã nguồn khi kéo thả
        const isImage = (f: File) => f.type.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp)$/i.test(f.name);
        const imageFiles = filesFound.filter((f) => isImage(f.file));
        const docFiles = filesFound.filter((f) => !isImage(f.file));

        if (imageFiles.length > 0) {
          let imgCount = 0;
          const newImgs: string[] = [];
          for (const item of imageFiles) {
            const reader = new FileReader();
            reader.onload = () => {
              newImgs.push(reader.result as string);
              imgCount++;
              if (imgCount === imageFiles.length) {
                setAttachedImages((prev) => [...prev, ...newImgs]);
                showToast(`Đã nhận ${newImgs.length} ảnh kéo thả!`, 'success');
              }
            };
            reader.readAsDataURL(item.file);
          }
        }

        if (docFiles.length > 0) {
          const newItems: Array<{ name: string; data: string }> = [];
          let count = 0;
          for (const item of docFiles) {
            const reader = new FileReader();
            reader.onload = () => {
              newItems.push({ name: item.name, data: reader.result as string });
              count++;
              if (count === docFiles.length) {
                setAttachedFiles((prev) => [...prev, ...newItems]);
                showToast(`Đã nhận ${newItems.length} tài liệu kéo thả!`, 'success');
              }
            };
            reader.readAsDataURL(item.file);
          }
        }
      }
    }
  };

  // Nạp nội dung một file đơn lẻ từ workspace vào chat
  const handleAttachSingleFileFromWorkspace = async (item: { name: string; size: number; file?: File; fullPath?: string }) => {
    let fileContent = '';
    const cached = workspaceFilesRef.current.get(item.name);
    const fileObj = item.file || cached?.file;
    const fullP = item.fullPath || cached?.fullPath;

    if (fileObj) {
      try {
        fileContent = await fileObj.text();
      } catch (e: any) {
        showToast(`Lỗi đọc file: ${e.message}`, 'error');
        return;
      }
    } else if (fullP) {
      try {
        const res = await chatService.readFile(fullP);
        if (res.success && res.content) {
          fileContent = res.content;
        }
      } catch (e: any) {
        showToast(`Lỗi đọc file: ${e.message}`, 'error');
        return;
      }
    }

    if (!fileContent) {
      showToast(`Không đọc được file ${item.name}`, 'error');
      return;
    }

    const dataUrl = 'data:text/plain;base64,' + btoa(unescape(encodeURIComponent(fileContent)));
    setAttachedFiles((prev) => [
      ...prev.filter((f) => f.name !== item.name),
      { name: item.name, data: dataUrl },
    ]);
    showToast(`Đã thêm ${item.name} vào danh sách đính kèm!`, 'success');
  };

  // Helper: Giải quyết đọc nội dung file từ cache workspace client hoặc backend
  const resolveFileContent = async (filePath: string): Promise<{ name: string; content: string; lang: string } | null> => {
    const cleaned = filePath.trim().replace(/^[`'"]+|[`'"]+$/g, '');
    let item = workspaceFilesRef.current.get(cleaned);

    // Tìm kiếm mờ nếu đường dẫn không khớp hoàn toàn
    if (!item) {
      for (const [key, val] of workspaceFilesRef.current.entries()) {
        if (key.endsWith(cleaned) || cleaned.endsWith(key) || key.split('/').pop() === cleaned.split('/').pop()) {
          item = val;
          break;
        }
      }
    }

    let fileContent = '';
    let foundName = cleaned;
    let lang = cleaned.split('.').pop() || 'text';

    if (item) {
      foundName = item.name;
      lang = foundName.split('.').pop() || 'text';
      if (item.file) {
        try {
          fileContent = await item.file.text();
        } catch (e: any) {
          console.error(`Lỗi đọc tệp ${foundName}:`, e);
        }
      } else if (item.fullPath) {
        try {
          const res = await chatService.readFile(item.fullPath);
          if (res.success && res.content) {
            fileContent = res.content;
            lang = res.lang || lang;
          }
        } catch (e: any) {
          console.error(`Lỗi nạp file từ backend:`, e);
        }
      }
    }

    if (!fileContent) {
      // Thử gọi backend readFile trực tiếp
      try {
        const res = await chatService.readFile(cleaned);
        if (res.success && res.content) {
          fileContent = res.content;
          foundName = res.filename || cleaned;
          lang = res.lang || lang;
        }
      } catch {}
    }

    if (fileContent) {
      return { name: foundName, content: fileContent, lang };
    }
    return null;
  };

  // Vòng lặp tự động nạp file theo yêu cầu của AI (Auto-Fetch Loop - Không giới hạn số lần)
  const triggerAutoFetchLoop = async (
    botContent: string,
    historyMessages: Array<{ role: string; content: string }>,
    depth = 0,
    alreadyFetched = new Set<string>()
  ) => {
    // Chặn an toàn tối đa 100 vòng đệ quy để chống crash trình duyệt
    if (depth >= 100) return;

    const matches = [...botContent.matchAll(/\[(?:FETCH_FILE|READ_FILE):\s*([^\]]+)\]/gi)];
    const requestedPaths = Array.from(
      new Set(
        matches
          .map((m) => m[1].trim().replace(/^[`'"]+|[`'"]+$/g, ''))
          .filter((p) => Boolean(p) && !alreadyFetched.has(p))
      )
    );

    // Nếu AI không yêu cầu file mới nào nữa -> vòng lặp kết thúc tự nhiên
    if (requestedPaths.length === 0) return;

    // Nạp toàn bộ các file mà AI yêu cầu trong câu trả lời này
    const filesToFetch = requestedPaths;
    filesToFetch.forEach((p) => alreadyFetched.add(p));

    showToast(`🤖 AI yêu cầu đọc ${filesToFetch.length} file: ${filesToFetch.join(', ')}. Đang tự động nạp từ backend...`, 'info');

    const loadedFiles: Array<{ name: string; content: string; lang: string }> = [];
    const failedFiles: string[] = [];

    for (const fp of filesToFetch) {
      const res = await resolveFileContent(fp);
      if (res) {
        loadedFiles.push(res);
      } else {
        failedFiles.push(fp);
      }
    }

    if (loadedFiles.length === 0 && failedFiles.length === 0) return;

    let promptToSend = '';
    let userDisplayTitle = '';

    if (loadedFiles.length > 0) {
      userDisplayTitle = `📄 [Tự động nạp tệp từ backend theo yêu cầu của AI: ${loadedFiles.map((f) => `\`${f.name}\``).join(', ')}]`;
      const fileBlocks = loadedFiles.map(
        (f) => `#### 📄 File: \`${f.name}\` (${formatFileSize(f.content.length)})\n\`\`\`${f.lang}\n${f.content}\n\`\`\``
      ).join('\n\n');

      promptToSend = `Đây là nội dung tệp được backend tự động cung cấp theo yêu cầu [READ_FILE] của bạn:\n\n${fileBlocks}\n\nHãy phân tích kỹ nội dung trên và hoàn thành câu trả lời chi tiết cho người dùng.`;
    }

    if (failedFiles.length > 0) {
      const failMsg = `⚠️ Không tìm thấy hoặc không thể đọc được các tệp sau từ backend: ${failedFiles.map((f) => `\`${f}\``).join(', ')}. Vui lòng xem lại danh sách tệp của dự án và tiếp tục trả lời dựa trên những tệp đã có.`;
      if (promptToSend) {
        promptToSend += `\n\n${failMsg}`;
      } else {
        userDisplayTitle = `⚠️ [Không tìm thấy tệp: ${failedFiles.join(', ')}]`;
        promptToSend = failMsg;
      }
    }

    const newUserMsg: ChatMessage = {
      id: 'msg_auto_' + Date.now(),
      role: 'user',
      content: userDisplayTitle,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setSending(true);

    try {
      const newHistoryPayload = [
        ...historyMessages,
        { role: 'assistant', content: botContent },
        { role: 'user', content: promptToSend },
      ];

      const res = await chatService.sendMessage({
        messages: newHistoryPayload,
        prompt: promptToSend,
        model,
        skill_id: selectedSkillId === 'default' ? undefined : selectedSkillId,
        web_search: webSearch,
        thinking,
        dual_ai_mode: dualAiMode,
        evaluator_model: dualAiMode ? evaluatorModel : undefined,
        max_rounds: dualAiMode ? maxRounds : undefined,
      });

      const nextBotContent = res.response || res.text || '(Không nhận được phản hồi)';
      const newBotMsg: ChatMessage = {
        id: 'msg_' + (Date.now() + 1),
        role: 'assistant',
        content: nextBotContent,
        timestamp: new Date().toLocaleTimeString(),
        model: res.model || model,
        skill_used: res.skill_used,
        account_used: res.account_used,
        dual_ai_mode: res.dual_ai_mode,
        rounds_count: res.rounds_count,
        discussion_history: res.discussion_history,
        blocks: res.blocks,
        tokens: res.tokens || res.usage,
      };

      setMessages((prev) => [...prev, newBotMsg]);
      showToast(`AI đã nhận nội dung tệp và hoàn tất phản hồi!`, 'success');

      // Tiếp tục đệ quy nếu AI lại yêu cầu đọc thêm file khác
      await triggerAutoFetchLoop(nextBotContent, newHistoryPayload, depth + 1, alreadyFetched);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: 'msg_err_' + Date.now(),
        role: 'assistant',
        content: `⚠️ **Đã xảy ra lỗi khi nạp file tự động**: ${err.message || 'Không thể kết nối đến AI Gateway'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
  };

  // Xử lý khi AI hoặc người dùng yêu cầu nạp file cụ thể thủ công (On-Demand Fetching)
  const handleFetchFile = async (filePath: string) => {
    const res = await resolveFileContent(filePath);
    if (!res) {
      showToast(`Không tìm thấy nội dung file: ${filePath}`, 'error');
      return;
    }

    const { name: foundName, content: fileContent, lang } = res;
    const promptToSend = `Đây là nội dung chi tiết của tệp \`${foundName}\`:\n\n\`\`\`${lang}\n${fileContent}\n\`\`\`\nHãy phân tích và trả lời tiếp.`;

    const newUserMsg: ChatMessage = {
      id: 'msg_' + Date.now(),
      role: 'user',
      content: `📄 [Nạp tệp On-Demand: \`${foundName}\` (${formatFileSize(fileContent.length)})]`,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, newUserMsg]);
    setSending(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const newHistoryPayload = [...historyPayload, { role: 'user', content: promptToSend }];

      const sendRes = await chatService.sendMessage({
        messages: newHistoryPayload,
        prompt: promptToSend,
        model,
        skill_id: selectedSkillId === 'default' ? undefined : selectedSkillId,
        web_search: webSearch,
        thinking,
        dual_ai_mode: dualAiMode,
        evaluator_model: dualAiMode ? evaluatorModel : undefined,
        max_rounds: dualAiMode ? maxRounds : undefined,
      });

      const botContent = sendRes.response || sendRes.text || '(Không nhận được phản hồi)';
      const newBotMsg: ChatMessage = {
        id: 'msg_' + (Date.now() + 1),
        role: 'assistant',
        content: botContent,
        timestamp: new Date().toLocaleTimeString(),
        model: sendRes.model || model,
        skill_used: sendRes.skill_used,
        account_used: sendRes.account_used,
        dual_ai_mode: sendRes.dual_ai_mode,
        rounds_count: sendRes.rounds_count,
        discussion_history: sendRes.discussion_history,
        blocks: sendRes.blocks,
        tokens: sendRes.tokens || sendRes.usage,
      };

      setMessages((prev) => [...prev, newBotMsg]);
      showToast(`Đã nạp tệp ${foundName} và gửi cho AI!`, 'success');

      // Tự động tiếp tục nếu AI lại yêu cầu đọc thêm file khác
      const alreadyFetched = new Set<string>([foundName, filePath]);
      await triggerAutoFetchLoop(botContent, newHistoryPayload, 1, alreadyFetched);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: 'msg_err_' + Date.now(),
        role: 'assistant',
        content: `⚠️ **Đã xảy ra lỗi**: ${err.message || 'Không thể kết nối đến AI Gateway'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  };

  const handleImageAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const filesArray = Array.from(fileList);
    let readCount = 0;
    const newImages: string[] = [];

    for (const file of filesArray) {
      const reader = new FileReader();
      reader.onload = () => {
        newImages.push(reader.result as string);
        readCount++;
        if (readCount === filesArray.length) {
          setAttachedImages((prev) => [...prev, ...newImages]);
          showToast(`Đã đính kèm ${newImages.length} ảnh!`, 'success');
        }
      };
      reader.readAsDataURL(file);
    }
    e.target.value = '';
  };

  const handleSendMessage = async () => {
    const prompt = inputPrompt.trim();
    if (!prompt && attachedFiles.length === 0 && attachedImages.length === 0) return;

    const currentFiles = [...attachedFiles];
    const currentImages = [...attachedImages];

    const userMessageId = 'msg_' + Date.now();
    const newUserMsg: ChatMessage = {
      id: userMessageId,
      role: 'user',
      content: prompt || (currentImages.length > 0 ? (currentImages.length === 1 ? '[Hình ảnh đính kèm]' : `[Đã đính kèm ${currentImages.length} hình ảnh]`) : (currentFiles.length > 0 ? `[Đã đính kèm ${currentFiles.length} file tài liệu/thư mục]` : '')),
      timestamp: new Date().toLocaleTimeString(),
      images: currentImages.length > 0 ? currentImages : undefined,
      files: currentFiles.map((f) => ({ name: f.name })),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInputPrompt('');
    setAttachedImages([]);
    setAttachedFiles([]);
    setSending(true);

    try {
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
        image: m.images?.[0],
        images: m.images,
        files: m.files,
      }));

      const defaultPrompt = currentImages.length > 0
        ? 'Hãy phân tích chi tiết hình ảnh đính kèm'
        : 'Hãy phân tích toàn bộ thư mục / tài liệu đính kèm';
      const promptToSend = prompt || defaultPrompt;

      const messagePayload = {
        messages: [
          ...historyPayload,
          {
            role: 'user',
            content: promptToSend,
            image: currentImages[0] || undefined,
            images: currentImages.length > 0 ? currentImages : undefined,
          }
        ],
        prompt: promptToSend,
        model,
        skill_id: selectedSkillId === 'default' ? undefined : selectedSkillId,
        web_search: webSearch,
        thinking,
        image: currentImages[0] || undefined,
        images: currentImages.length > 0 ? currentImages : undefined,
        files: currentFiles.map((f) => ({ filename: f.name, data: f.data })),
        dual_ai_mode: dualAiMode,
        evaluator_model: dualAiMode ? evaluatorModel : undefined,
        max_rounds: dualAiMode ? maxRounds : undefined,
      };

      if (!dualAiMode) {
        const botMsgId = 'msg_' + (Date.now() + 1);
        let accumulatedText = '';

        const initialBotMsg: ChatMessage = {
          id: botMsgId,
          role: 'assistant',
          content: '',
          timestamp: new Date().toLocaleTimeString(),
          model,
        };
        setMessages((prev) => [...prev, initialBotMsg]);

        await chatService.sendMessageStream(
          messagePayload,
          (chunk) => {
            accumulatedText += chunk;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId ? { ...msg, content: accumulatedText } : msg
              )
            );
          },
          (_thoughtChunk) => {
            // Có thể hiển thị indicator thinking nếu cần
          },
          (finalRes) => {
            const finalBotContent = finalRes.response || finalRes.text || accumulatedText;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      content: finalBotContent,
                      model: finalRes.model || model,
                      skill_used: finalRes.skill_used,
                      account_used: finalRes.account_used,
                      blocks: finalRes.blocks,
                      tokens: finalRes.tokens || finalRes.usage,
                    }
                  : msg
              )
            );

            const newHistoryPayload = [
              ...historyPayload,
              { role: 'user', content: prompt || 'Hãy phân tích toàn bộ thư mục / tài liệu đính kèm' },
            ];
            triggerAutoFetchLoop(finalBotContent, newHistoryPayload, 0);
          }
        );
      } else {
        const res = await chatService.sendMessage(messagePayload);

        const botContent = res.response || res.text || '(Không nhận được phản hồi)';
        const newBotMsg: ChatMessage = {
          id: 'msg_' + (Date.now() + 1),
          role: 'assistant',
          content: botContent,
          timestamp: new Date().toLocaleTimeString(),
          model: res.model || model,
          skill_used: res.skill_used,
          account_used: res.account_used,
          dual_ai_mode: res.dual_ai_mode,
          rounds_count: res.rounds_count,
          discussion_history: res.discussion_history,
          blocks: res.blocks,
          tokens: res.tokens || res.usage,
        };

        setMessages((prev) => [...prev, newBotMsg]);

        const newHistoryPayload = [
          ...historyPayload,
          { role: 'user', content: prompt || 'Hãy phân tích toàn bộ thư mục / tài liệu đính kèm' },
        ];
        await triggerAutoFetchLoop(botContent, newHistoryPayload, 0);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: 'msg_err_' + Date.now(),
        role: 'assistant',
        content: `⚠️ **Đã xảy ra lỗi**: ${err.message || 'Không thể kết nối đến AI Gateway'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  };

  const handleSuggestionClick = (text: string) => {
    setInputPrompt(text);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex gap-3 h-[calc(100vh-84px)] min-h-[500px]">
      {/* Left: Chat Area (Takes full remaining space) */}
      <div className="flex-1 flex flex-col min-w-0 h-full gap-2">
        {/* Chat History Box (Fills 100% Available Height) */}
        <div className="flex-1 min-h-0 bg-slate-900/40 border border-slate-800 rounded-2xl p-3 sm:p-5 overflow-y-auto space-y-3.5 flex flex-col">
          {messages.length === 0 && (
            <div className="m-auto text-center py-10 max-w-md">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mx-auto mb-4">
                <Bot className="w-8 h-8" />
              </div>
              <h3 className="font-bold text-lg text-white mb-2">Thử nghiệm Gemini Multimodal Vision</h3>
              <p className="text-xs text-slate-400 mb-6">
                Bạn có thể hỏi bất kỳ câu hỏi văn bản nào hoặc tải kèm hình ảnh (PNG, JPEG, WebP, GIF) để AI nhận diện và phân tích trực quan.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-left">
                <button
                  onClick={() => setInputPrompt('Bức ảnh này có nội dung gì? Hãy mô tả chi tiết.')}
                  className="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 rounded-xl text-slate-300 transition"
                >
                  🔍 "Bức ảnh này có nội dung gì?..."
                </button>
                <button
                  onClick={() => setInputPrompt('Hãy giới thiệu về bản thân bạn trong 2 câu ngắn gọn.')}
                  className="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 rounded-xl text-slate-300 transition"
                >
                  👋 "Hãy giới thiệu về bản thân..."
                </button>
                <button
                  onClick={() => setInputPrompt('Hãy viết một bài tóm tắt về trí tuệ nhân tạo (AI) sử dụng các kiểu định dạng: tiêu đề H1, H2, H3, chữ in đậm, in nghiêng, gạch chân <u>, danh sách và bảng so sánh.')}
                  className="p-3 bg-purple-950/40 hover:bg-purple-900/50 border border-purple-800/50 rounded-xl text-purple-200 transition"
                >
                  🎨 "Thử nghiệm định dạng chữ phong phú..."
                </button>
                <button
                  onClick={() => setInputPrompt('Vẽ một chú rồng vàng uy nghiêm bay lượn trên đỉnh Fansipan lúc bình minh, mây mù huyền ảo, phong cách sơn dầu kiệt tác 8k')}
                  className="p-3 bg-pink-950/40 hover:bg-pink-900/50 border border-pink-800/50 rounded-xl text-pink-200 transition"
                >
                  🖼️ "Vẽ chú rồng vàng Fansipan..."
                </button>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <MessageItem
              key={msg.id}
              message={msg}
              onSuggestionClick={handleSuggestionClick}
              onFetchFile={handleFetchFile}
            />
          ))}

          {sending && (
            <div className="flex items-start space-x-3 w-full">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-white shrink-0 shadow animate-pulse ${
                  dualAiMode
                    ? 'bg-gradient-to-tr from-indigo-600 to-purple-600'
                    : 'bg-gradient-to-tr from-blue-600 to-indigo-500'
                }`}
              >
                {dualAiMode ? <Users className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div
                className={`p-4 rounded-2xl rounded-tl-sm text-sm flex-1 ${
                  dualAiMode
                    ? 'bg-indigo-950/40 border border-indigo-500/30 text-indigo-200'
                    : 'bg-slate-900/90 border border-slate-800 text-slate-300'
                }`}
              >
                <div className="flex items-center space-x-2 font-medium">
                  <Loader2 className={`w-4 h-4 animate-spin ${dualAiMode ? 'text-indigo-400' : 'text-blue-400'}`} />
                  <span>
                    {dualAiMode
                      ? '👥 Hai AI đang thảo luận & phản biện theo Kỹ năng...'
                      : 'AI đang suy nghĩ và tạo nội dung phản hồi...'}
                  </span>
                </div>
                {dualAiMode && (
                  <p className="text-xs text-indigo-300/80 mt-1.5 pl-6">
                    AI 1 tạo bản nháp ➔ AI 2 giám định khắt khe & yêu cầu làm lại cho đến khi đạt chuẩn xuất sắc.
                  </p>
                )}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Attached items preview pills */}
        {(attachedFiles.length > 0 || attachedImages.length > 0) && (
          <div className="flex flex-wrap items-center gap-2 p-2 bg-slate-900/90 border border-slate-800 rounded-xl text-xs shrink-0">
            {/* Attached Images Thumbnail Cards */}
            {attachedImages.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {attachedImages.map((imgData, idx) => (
                  <div
                    key={idx}
                    className="relative group rounded-xl overflow-hidden border border-blue-500/40 bg-slate-950 shadow-md h-14 w-14 shrink-0"
                    title={`Ảnh ${idx + 1}`}
                  >
                    <img
                      src={imgData}
                      alt={`Ảnh ${idx + 1}`}
                      className="h-full w-full object-cover transition-transform group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                      <button
                        type="button"
                        onClick={() => setAttachedImages((prev) => prev.filter((_, i) => i !== idx))}
                        className="p-1 bg-red-600/90 hover:bg-red-600 text-white rounded-full transition shadow"
                        title="Xóa ảnh này"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <span className="absolute bottom-0.5 right-0.5 text-[9px] font-mono bg-black/70 px-1 rounded text-white/90">
                      #{idx + 1}
                    </span>
                  </div>
                ))}
                {attachedImages.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setAttachedImages([])}
                    className="text-[11px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950/40 transition flex items-center space-x-1"
                    title="Xóa tất cả ảnh"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Xóa hết ảnh ({attachedImages.length})</span>
                  </button>
                )}
              </div>
            )}

            {/* Grouped Folder Pills & File Pills */}
            {(() => {
              const folders: Record<string, number[]> = {};
              const standalones: number[] = [];

              attachedFiles.forEach((f, idx) => {
                const normalized = f.name.replace(/\\/g, '/');
                if (!f.name.startsWith('📁') && normalized.includes('/')) {
                  const root = normalized.split('/')[0];
                  if (!folders[root]) folders[root] = [];
                  folders[root].push(idx);
                } else {
                  standalones.push(idx);
                }
              });

              return (
                <>
                  {Object.entries(folders).map(([folderName, indices]) => (
                    <div
                      key={folderName}
                      className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-200 shadow-sm"
                      title={`${indices.length} file trong thư mục ${folderName}`}
                    >
                      <Folder className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span className="font-semibold">{folderName}/</span>
                      <span className="text-[10px] bg-amber-900/60 px-1.5 py-0.2 rounded text-amber-300 font-mono">
                        {indices.length} files
                      </span>
                      <button
                        onClick={() => {
                          const removeSet = new Set(indices);
                          setAttachedFiles((prev) => prev.filter((_, i) => !removeSet.has(i)));
                        }}
                        className="hover:text-white p-0.5 ml-1"
                        title="Xóa thư mục này"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}

                  {standalones.map((idx) => {
                    const f = attachedFiles[idx];
                    const isZip = f.name.toLowerCase().endsWith('.zip');
                    const isFolderScan = f.name.startsWith('📁');
                    return (
                      <div
                        key={idx}
                        className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border text-slate-200 ${
                          isZip || isFolderScan
                            ? 'bg-amber-950/40 border-amber-800/60 text-amber-200 shadow-sm'
                            : 'bg-slate-800 border-slate-700'
                        }`}
                      >
                        {isZip || isFolderScan ? (
                          <FolderOpen className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        ) : (
                          <Paperclip className="w-3.5 h-3.5 shrink-0" />
                        )}
                        <span className="max-w-[200px] truncate">{f.name}</span>
                        {isFolderScan && workspaceFilesList.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setIsFilesDrawerOpen(true)}
                            className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-900/70 hover:bg-amber-800 text-amber-200 text-[10px] font-semibold transition cursor-pointer"
                            title="Mở danh sách file để xem hoặc nạp file chi tiết"
                          >
                            <Eye className="w-3 h-3" />
                            <span>Xem files</span>
                          </button>
                        )}
                        <button
                          onClick={() => setAttachedFiles((prev) => prev.filter((_, i) => i !== idx))}
                          className="hover:text-white"
                          title="Xóa đính kèm"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </>
              );
            })()}

            {attachedFiles.length > 1 && (
              <button
                onClick={() => setAttachedFiles([])}
                className="text-[11px] text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-950/40 transition flex items-center space-x-1 ml-auto"
                title="Xóa toàn bộ file và thư mục đính kèm"
              >
                <Trash2 className="w-3 h-3" />
                <span>Xóa tất cả</span>
              </button>
            )}
          </div>
        )}

        {/* Chat Input Area (Compact & Fixed at Bottom) */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onPaste={handlePaste}
          className={`bg-slate-900 border rounded-2xl p-2.5 transition shadow-lg shrink-0 relative ${
            isDraggingOver
              ? 'border-2 border-dashed border-amber-500 bg-amber-950/20'
              : 'border-slate-800 focus-within:border-blue-500'
          }`}
        >
          {isDraggingOver && (
            <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-xs rounded-2xl flex items-center justify-center space-x-2 text-amber-300 font-medium z-10 pointer-events-none border-2 border-dashed border-amber-500">
              <FolderOpen className="w-5 h-5 animate-bounce" />
              <span>Thả thư mục hoặc các file vào đây để AI đọc ngay!</span>
            </div>
          )}
          <div className="flex items-end space-x-2">
            {/* Attach Buttons */}
            <div className="flex items-center space-x-1">
              {/* Button: Đính kèm File */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-2 hover:bg-slate-800 text-slate-400 hover:text-blue-400 rounded-xl transition"
                title="Đính kèm 1 hoặc nhiều tài liệu (.docx, .pdf, .txt, .zip, code...)"
              >
                <Paperclip className="w-5 h-5" />
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept=".docx,.doc,.pdf,.txt,.md,.json,.csv,.xlsx,.xls,.pptx,.ppt,.py,.ts,.tsx,.js,.jsx,.html,.css,.zip"
                  onChange={handleFileAttach}
                />
              </button>

              {/* Button: Tải lên cả Thư mục (Folder) */}
              <button
                type="button"
                onClick={() => folderInputRef.current?.click()}
                className="p-2 hover:bg-slate-800 text-slate-400 hover:text-amber-400 rounded-xl transition"
                title="Tải lên toàn bộ Thư mục (Folder) trên máy tính"
              >
                <FolderOpen className="w-5 h-5" />
                <input
                  ref={folderInputRef}
                  type="file"
                  className="hidden"
                  {...({ webkitdirectory: '', directory: '' } as any)}
                  multiple
                  onChange={handleFolderAttach}
                />
              </button>

              {/* Button: Quét Thư mục từ Đường dẫn đĩa cứng */}
              <button
                type="button"
                onClick={() => setIsLocalFolderModalOpen(true)}
                className="p-2 hover:bg-slate-800 text-slate-400 hover:text-emerald-400 rounded-xl transition"
                title="Nhập đường dẫn thư mục trên máy để quét trực tiếp"
              >
                <FolderSearch className="w-5 h-5" />
              </button>

              {/* Button: Đính kèm Ảnh */}
              <button
                type="button"
                onClick={() => imageInputRef.current?.click()}
                className="p-2 hover:bg-slate-800 text-slate-400 hover:text-blue-400 rounded-xl transition"
                title="Đính kèm 1 hoặc nhiều ảnh (hoặc bấm Ctrl+V để dán trực tiếp)"
              >
                <ImageIcon className="w-5 h-5" />
                <input
                  ref={imageInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept="image/*"
                  onChange={handleImageAttach}
                />
              </button>
            </div>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="Nhập câu hỏi, dán ảnh (Ctrl+V) hoặc kéo thả file vào đây... (Shift+Enter xuống dòng, Enter để gửi)"
              className="flex-1 bg-transparent border-0 text-slate-100 placeholder-slate-500 focus:outline-none resize-none py-1.5 text-sm max-h-32"
            />

            {/* Send Button */}
            <button
              onClick={handleSendMessage}
              disabled={sending || (!inputPrompt.trim() && attachedFiles.length === 0 && attachedImages.length === 0)}
              className="p-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition shadow-lg shadow-blue-600/30 flex items-center justify-center shrink-0 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
            >
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>

          {/* Rich Typography Indicators */}
          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1.5 px-1 border-t border-slate-800/60 mt-1.5 select-none">
            <div className="flex items-center space-x-2 text-slate-400 text-[11px]">
              <span>✨ Hỗ trợ Markdown & Dán ảnh (Ctrl+V) từ Clipboard</span>
            </div>
            <span className="hidden sm:inline text-slate-500 text-[10px]">Shift+Enter xuống dòng, Enter để gửi</span>
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Compact AI Settings & Control Sidebar */}
      <aside className="w-full lg:w-56 xl:w-60 shrink-0 bg-slate-900/80 border border-slate-800 rounded-2xl p-2.5 flex flex-col gap-2 min-h-0 overflow-y-auto shadow-sm">
        {/* Sidebar Title */}
        <div className="flex items-center space-x-1.5 pb-1.5 border-b border-slate-800">
          <SlidersHorizontal className="w-3.5 h-3.5 text-blue-400 shrink-0" />
          <h3 className="text-[11px] font-bold text-white uppercase tracking-wider truncate">Cài Đặt Chat</h3>
        </div>

        {/* New Chat Action */}
        <button
          onClick={handleCreateNewSession}
          className="w-full flex items-center justify-center space-x-1.5 py-2 px-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-blue-600/20 transition group shrink-0 active:scale-95"
          title="Bắt đầu cuộc trò chuyện mới"
        >
          <Plus className="w-3.5 h-3.5 group-hover:rotate-90 transition-transform" />
          <span>Cuộc trò chuyện mới</span>
        </button>

        {/* Model Picker Box */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-2 space-y-1 shadow-inner">
          <div className="flex items-center space-x-1">
            <Cpu className="w-3 h-3 text-blue-400 shrink-0" />
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Model</label>
          </div>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-blue-500 cursor-pointer truncate"
          >
            {MODEL_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label} className="bg-slate-950 text-blue-300 font-bold">
                {group.models.map((m) => (
                  <option key={m.id} value={m.id} className="bg-slate-900 text-slate-100 font-normal">
                    {m.name}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {/* Skill Picker Box */}
        <div className="bg-slate-950/80 border border-purple-900/40 rounded-xl p-2 space-y-1 shadow-inner">
          <div className="flex items-center space-x-1">
            <Sparkles className="w-3 h-3 text-purple-400 shrink-0" />
            <label className="text-[10px] font-bold text-purple-300 uppercase tracking-wider">Kỹ năng (Skill)</label>
          </div>
          <select
            value={selectedSkillId}
            onChange={(e) => onSkillChange(e.target.value)}
            className="w-full bg-slate-900 border border-purple-800/60 rounded-lg px-2 py-1 text-xs text-purple-200 focus:outline-none focus:border-purple-500 cursor-pointer truncate"
          >
            <option value="default" className="bg-slate-900 text-slate-100">
              ⚡ Trợ lý Toàn năng
            </option>
            {skills
              .filter((s) => s.id !== 'default')
              .map((s) => (
                <option key={s.id} value={s.id} className="bg-slate-900 text-slate-100">
                  {s.name}
                </option>
              ))}
          </select>
        </div>

        {/* Feature Toggles Box */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-2 space-y-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Tính năng</span>

          {/* Dual AI Mode Toggle */}
          <label
            className={`flex items-center justify-between p-1.5 rounded-lg border transition select-none cursor-pointer ${
              dualAiMode
                ? 'bg-indigo-950/60 border-indigo-500/50 text-indigo-200 shadow-sm shadow-indigo-950/50'
                : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700 text-slate-300'
            }`}
            title="Kích hoạt 2 AI thảo luận & phản biện lặp: AI 1 thực hiện theo Kỹ năng, AI 2 giám định & bắt lỗi đến khi chuẩn xác"
          >
            <div className="flex items-center space-x-1.5 truncate">
              <Users className={`w-3.5 h-3.5 shrink-0 ${dualAiMode ? 'text-indigo-400' : 'text-slate-400'}`} />
              <span className="text-xs font-semibold">👥 Thảo Luận 2 AI</span>
            </div>
            <input
              type="checkbox"
              checked={dualAiMode}
              onChange={(e) => setDualAiMode(e.target.checked)}
              className="rounded border-indigo-500 text-indigo-600 focus:ring-indigo-500 bg-slate-900 w-3.5 h-3.5 cursor-pointer shrink-0 ml-1"
            />
          </label>

          {/* Sub-options when Dual AI Mode is active */}
          {dualAiMode && (
            <div className="pl-2 border-l-2 border-indigo-500/40 space-y-1.5 pt-1 pb-1">
              <div>
                <label className="text-[9px] font-bold text-indigo-300 uppercase tracking-wider block mb-0.5">
                  AI Phản Biện (Critic)
                </label>
                <select
                  value={evaluatorModel}
                  onChange={(e) => setEvaluatorModel(e.target.value)}
                  className="w-full bg-slate-900 border border-indigo-500/40 rounded px-1.5 py-1 text-[11px] text-indigo-200 focus:outline-none focus:border-indigo-400 cursor-pointer"
                >
                  <option value="gemini-4-argon">Gemini 4 Argon (Suy luận nâng cao)</option>
                  <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (Phản biện sâu sắc)</option>
                  <option value="gemini-3.8-flash-tiered">Gemini 3.8 Flash (Phản biện nhanh & chuẩn)</option>
                  <option value="claude-opus-4-6-thinking">Claude Opus 4.6 (Phản biện nâng cao)</option>
                  <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between items-center text-[9px] font-bold text-indigo-300 uppercase tracking-wider mb-0.5">
                  <span>Vòng phản biện tối đa:</span>
                  <span className="font-mono text-indigo-200 font-bold">{maxRounds}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={5}
                  value={maxRounds}
                  onChange={(e) => setMaxRounds(parseInt(e.target.value, 10))}
                  className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded cursor-pointer"
                />
              </div>
            </div>
          )}

          <label className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition select-none">
            <div className="flex items-center space-x-1.5 truncate">
              <BrainCircuit className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span className="text-xs text-slate-300">Chế độ Suy luận</span>
            </div>
            <input
              type="checkbox"
              checked={thinking}
              onChange={(e) => setThinking(e.target.checked)}
              className="rounded border-slate-700 text-blue-600 focus:ring-blue-500 bg-slate-900 w-3.5 h-3.5 cursor-pointer shrink-0 ml-1"
            />
          </label>

          <label className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition select-none" title="Cho phép AI tự động tra cứu dữ liệu mới nhất trên Google Search">
            <div className="flex items-center space-x-1.5 truncate">
              <Globe className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span className="text-xs text-slate-300">Google Search</span>
            </div>
            <input
              type="checkbox"
              checked={webSearch}
              onChange={(e) => setWebSearch(e.target.checked)}
              className="rounded border-slate-700 text-blue-600 focus:ring-blue-500 bg-slate-900 w-3.5 h-3.5 cursor-pointer shrink-0 ml-1"
            />
          </label>
        </div>

        {/* Session & History Box */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-2 space-y-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Phiên hội thoại</span>

          {/* Context Session Badge */}
          <div className="flex items-center justify-between bg-slate-900 px-2 py-1 rounded-lg border border-slate-800 text-[11px] font-mono">
            <div className="flex items-center space-x-1 truncate">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
              <span className="text-slate-400 text-[10px]">ID:</span>
              <span className="text-blue-300 font-semibold truncate max-w-[95px] text-[10px]">
                {sessionId}
              </span>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(sessionId);
                showToast('Đã sao chép Session ID!', 'success');
              }}
              title="Sao chép Session ID"
              className="text-slate-500 hover:text-slate-200 p-0.5 ml-0.5"
            >
              <Copy className="w-3 h-3" />
            </button>
          </div>

          {/* Action: Sessions History Modal Button */}
          <button
            onClick={() => setIsSessionsModalOpen(true)}
            className="w-full py-1.5 px-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium flex items-center justify-center space-x-1 transition active:scale-95"
            title="Xem danh sách lịch sử các phiên trò chuyện"
          >
            <History className="w-3 h-3 text-blue-400" />
            <span>Lịch sử</span>
          </button>

          {/* Action: Clear */}
          <button
            onClick={handleClearCurrentSession}
            className="w-full py-1.5 px-1 bg-slate-800/60 hover:bg-red-950/40 text-slate-400 hover:text-red-300 border border-slate-800 hover:border-red-800/50 rounded-lg text-xs font-medium flex items-center justify-center space-x-1 transition active:scale-95"
            title="Xóa nội dung cuộc trò chuyện hiện tại"
          >
            <Trash2 className="w-3 h-3" />
            <span>Xóa nội dung</span>
          </button>
        </div>
      </aside>

      {/* Local Folder Path Scanner Modal */}
      {isLocalFolderModalOpen && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-5 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <FolderSearch className="w-5 h-5 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Quét Thư Mục Trên Máy Tính</h3>
              </div>
              <button
                onClick={() => setIsLocalFolderModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Nhập đường dẫn thư mục tuyệt đối trên máy tính hoặc máy chủ (ví dụ:{' '}
              <code className="text-emerald-300 bg-slate-950 px-1 py-0.5 rounded font-mono text-[11px]">
                H:\antigravity-fastapi\frontend\src
              </code>{' '}
              hoặc{' '}
              <code className="text-emerald-300 bg-slate-950 px-1 py-0.5 rounded font-mono text-[11px]">
                /app
              </code>
              ). Hệ thống sẽ tự động quét đệ quy các file mã nguồn/tài liệu và phân tích cho AI.
            </p>

            <div>
              <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block mb-1">
                Đường dẫn thư mục (Folder Path)
              </label>
              <input
                type="text"
                value={localFolderPathInput}
                onChange={(e) => setLocalFolderPathInput(e.target.value)}
                placeholder="C:\Users\... hoặc H:\project\..."
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleScanLocalFolder();
                }}
              />
            </div>

            <div className="flex justify-end space-x-2 pt-2 border-t border-slate-800/80">
              <button
                type="button"
                onClick={() => setIsLocalFolderModalOpen(false)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                Đóng
              </button>
              <button
                type="button"
                disabled={isScanningFolder || !localFolderPathInput.trim()}
                onClick={handleScanLocalFolder}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/30 flex items-center space-x-1.5 transition disabled:opacity-50 active:scale-95"
              >
                {isScanningFolder ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Đang quét...</span>
                  </>
                ) : (
                  <>
                    <FolderSearch className="w-3.5 h-3.5" />
                    <span>Quét & Đọc Thư Mục</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Workspace / Folder File Explorer Modal */}
      {isFilesDrawerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
                  <FolderOpen className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                    <span>Thư mục: {currentWorkspaceFolder || 'Dự án'}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-mono">
                      {workspaceFilesList.length} files
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Chế độ On-Demand: Nội dung file sẽ được nạp khi AI hoặc bạn yêu cầu
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsFilesDrawerOpen(false)}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Search filter */}
            <div className="p-3 border-b border-slate-800 bg-slate-900/50">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={searchFileFilter}
                  onChange={(e) => setSearchFileFilter(e.target.value)}
                  placeholder="Tìm kiếm file trong dự án..."
                  className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* File List */}
            <div className="p-3 overflow-y-auto flex-1 space-y-1.5 divide-y divide-slate-800/40">
              {workspaceFilesList
                .filter((f) => !searchFileFilter || f.name.toLowerCase().includes(searchFileFilter.toLowerCase()))
                .map((f, idx) => {
                  const isManifest = f.isManifest || isManifestFileName(f.name);
                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between pt-1.5 px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-xs"
                    >
                      <div className="flex items-center space-x-2 min-w-0 pr-2">
                        <FileText className={`w-3.5 h-3.5 shrink-0 ${isManifest ? 'text-blue-400' : 'text-slate-400'}`} />
                        <span className="truncate text-slate-200 font-mono text-[11px]">{f.name}</span>
                        {isManifest && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] bg-blue-500/20 text-blue-300 font-sans shrink-0">
                            Cấu hình / README
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2 shrink-0">
                        <span className="text-[10px] text-slate-500 font-mono">{formatFileSize(f.size)}</span>
                        <button
                          type="button"
                          onClick={() => handleAttachSingleFileFromWorkspace(f)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white transition text-[11px] font-medium"
                          title="Nạp nội dung file này vào danh sách đính kèm"
                        >
                          + Nạp vào chat
                        </button>
                      </div>
                    </div>
                  );
                })}
              {workspaceFilesList.length === 0 && (
                <div className="text-center py-8 text-xs text-slate-500">
                  Không có file nào trong thư mục.
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
              <span>Đã nạp {workspaceFilesList.length} files vào bộ nhớ đệm On-Demand</span>
              <button
                type="button"
                onClick={() => setIsFilesDrawerOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sessions History Modal */}
      <SessionsModal
        isOpen={isSessionsModalOpen}
        onClose={() => setIsSessionsModalOpen(false)}
        sessions={Object.values(getSessionsStore())}
        currentSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
      />
    </div>
  );
};
