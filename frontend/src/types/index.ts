export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  is_active: boolean;
  balance?: number;
  token_balance?: number;
  note?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ApiKey {
  id: string;
  user_id: string;
  key_value: string;
  name: string;
  is_active: boolean;
  requests_count: number;
  total_tokens: number;
  last_used_at?: string;
  created_at?: string;
}

export interface GoogleAccount {
  id: string;
  name?: string;
  email: string;
  is_active: boolean;
  total_requests: number;
  total_tokens: number;
  last_used_at?: string;
  added_at?: string;
  status_badge?: string;
  nav_count?: number;
  project_id?: string;
  is_primary?: boolean;
  is_rate_limited?: boolean;
  cooldown_left?: number;
  requests_count?: number;
  picture?: string;
}

export interface Skill {
  id: string;
  user_id?: string | null;
  name: string;
  system_prompt: string;
  is_default: boolean;
  is_system?: boolean;
  is_owner?: boolean;
  created_at?: string;
  updated_at?: string;
}

export type ContentBlockType =
  | 'text'
  | 'code'
  | 'thought'
  | 'table'
  | 'callout'
  | 'math'
  | 'diagram'
  | 'citations'
  | 'key_value'
  | 'task_list'
  | 'suggestion'
  | 'quote'
  | 'image';

export interface CitationSource {
  title: string;
  url: string;
  domain?: string;
  snippet?: string;
}

export interface TaskListItem {
  task: string;
  completed: boolean;
}

export interface KeyValueItem {
  key: string;
  value: string;
}

export interface ContentBlock {
  type: ContentBlockType;
  content?: string;
  language?: string;
  filename?: string;
  lines_count?: number;
  title?: string;
  variant?: 'note' | 'tip' | 'warning' | 'caution' | 'info' | 'success';
  headers?: string[];
  rows?: string[][];
  alignments?: Array<'left' | 'center' | 'right'>;
  formula?: string;
  display?: boolean;
  diagram_type?: string;
  code?: string;
  sources?: CitationSource[];
  items?: any[];
  url?: string;
  alt?: string;
  caption?: string;
  raw?: string;
  total?: number;
  completed_count?: number;
}

export interface DiscussionRound {
  round: number;
  worker_model: string;
  worker_draft: string;
  evaluator_model: string;
  evaluator_feedback: string;
  verdict: 'PASSED' | 'NEEDS_REVISION' | string;
  score: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  blocks?: ContentBlock[];
  images?: string[];
  files?: Array<{ name: string; type?: string }>;
  model?: string;
  account_used?: string;
  skill_used?: string;
  dual_ai_mode?: boolean;
  rounds_count?: number;
  discussion_history?: DiscussionRound[];
  tokens?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    prompt?: number;
    completion?: number;
    total?: number;
  };
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface QuotaStats {
  total_requests: number;
  total_tokens: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  active_accounts: number;
  models_usage: Record<string, number>;
}

export interface RequestLog {
  id: number;
  timestamp: number;
  account_id: string;
  account_email: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  status: string;
}

export interface SystemSettings {
  strategy?: string;
  default_model?: string;
  api_key?: string;
  google_oauth_client_id?: string;
  google_oauth_secret_configured?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface GeneratedImage {
  id: string;
  url: string;
  prompt: string;
  style?: string;
  aspect_ratio?: string;
  created_at: string;
}

export type TabType = 'chat' | 'images' | 'skills' | 'accounts' | 'api';

export interface TokenPackage {
  id: string;
  name: string;
  price: number;
  tokens: number;
  description: string;
  badge?: string;
  popular?: boolean;
}

export interface PaymentTransaction {
  id: number;
  order_id: string;
  request_id?: string;
  amount: number;
  tokens_granted: number;
  package_name?: string;
  status: 'pending' | 'success' | 'failed';
  payment_url?: string;
  qr_code_url?: string;
  deeplink?: string;
  momo_trans_id?: string;
  message?: string;
  created_at?: string;
  updated_at?: string;
}

export interface MoMoPaymentCreateResponse {
  status: string;
  order_id: string;
  amount: number;
  tokens: number;
  package_name?: string;
  pay_url?: string;
  qr_code_url?: string;
  deeplink?: string;
  message?: string;
}

export interface MoMoConfig {
  partner_code: string;
  access_key: string;
  secret_key_masked?: string;
  ipn_url: string;
  redirect_url: string;
  environment: 'sandbox' | 'production';
}
