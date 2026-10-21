import { getAuthToken } from './apiClient';

import { ContentBlock, DiscussionRound } from '../types';

export interface ChatPayload {
  messages: Array<{ role: string; content: string; image?: string; images?: string[]; files?: any[] }>;
  prompt: string;
  image?: string;
  images?: string[];
  files?: Array<{ data: string; filename: string }>;
  model: string;
  thinking: boolean;
  web_search: boolean;
  skill_id?: string;
  dual_ai_mode?: boolean;
  evaluator_model?: string;
  max_rounds?: number;
}

export interface ChatResponse {
  response?: string;
  text?: string;
  model?: string;
  skill_used?: string;
  account_used?: string;
  dual_ai_mode?: boolean;
  rounds_count?: number;
  discussion_history?: DiscussionRound[];
  blocks?: ContentBlock[];
  tokens?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    prompt?: number;
    completion?: number;
    total?: number;
  };
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export const chatService = {
  async sendMessage(payload: ChatPayload): Promise<ChatResponse> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let detail = `Lỗi ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || errJson.message || detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    return res.json();
  },

  async sendMessageStream(
    payload: ChatPayload,
    onChunk: (text: string) => void,
    onThought?: (text: string) => void,
    onDone?: (res: ChatResponse) => void,
    signal?: AbortSignal
  ): Promise<void> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, stream: true }),
      signal,
    });

    if (!res.ok) {
      let detail = `Lỗi ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || errJson.message || detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    if (!res.body) {
      throw new Error('Trình duyệt không hỗ trợ ReadableStream');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = 'chunk';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          currentEvent = 'chunk';
          continue;
        }

        if (trimmed.startsWith('event:')) {
          currentEvent = trimmed.slice(6).trim();
          continue;
        }

        if (trimmed.startsWith('data:')) {
          const dataStr = trimmed.slice(5).trim();
          try {
            const dataObj = JSON.parse(dataStr);
            if (currentEvent === 'chunk' || currentEvent === 'text') {
              if (dataObj.text) onChunk(dataObj.text);
            } else if (currentEvent === 'thought') {
              if (dataObj.text && onThought) onThought(dataObj.text);
            } else if (currentEvent === 'done') {
              if (onDone) onDone(dataObj);
            } else if (currentEvent === 'error') {
              throw new Error(dataObj.error || 'Lỗi streaming');
            }
          } catch (e: any) {
            if (e.message && e.message.includes('Lỗi streaming')) throw e;
          }
        }
      }
    }
  },

  async exportToDocx(markdownContent: string, filename?: string): Promise<Blob> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/api/export/docx', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        content: markdownContent,
        filename: filename || 'Antigravity_Content.docx',
      }),
    });

    if (!res.ok) {
      throw new Error(`Xuất Word thất bại (${res.status})`);
    }

    return res.blob();
  },

  downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  async readLocalFolder(folderPath: string, maxFiles: number = 80): Promise<{
    success: boolean;
    folder_name: string;
    folder_path: string;
    total_files: number;
    tree: string;
    context_text: string;
    files: Array<{ filename: string; size: number }>;
  }> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/api/read-folder', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        folder_path: folderPath,
        max_files: maxFiles,
      }),
    });

    if (!res.ok) {
      let detail = `Lỗi ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    return res.json();
  },

  async readFile(filePath: string, maxSizeKb: number = 500): Promise<{
    success: boolean;
    file_path: string;
    filename: string;
    content: string;
    size: number;
    lang?: string;
    error?: string;
  }> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch('/api/read-file', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        file_path: filePath,
        max_size_kb: maxSizeKb,
      }),
    });

    if (!res.ok) {
      let detail = `Lỗi ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    return res.json();
  },
};

