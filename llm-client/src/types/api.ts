// API 请求和响应类型

export interface LoginRequest {
  username: string;
  password: string;
  serverUrl: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  serverUrl: string;
}

export interface User {
  id: string;
  username: string;
  email?: string;
  avatar?: string;
  role?: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

export interface ApiError {
  message: string;
  code: string;
  details?: any;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  id?: string;
  tokens?: number;
  filtered?: boolean;
  warnings?: string[];
}

export interface ChatRequest {
  sessionId: string;
  message: string;
  timestamp: number;
}

export interface ChatResponse {
  reply: string;
  sessionId: string;
  messageId: string;
  tokens?: number;
  filtered?: boolean;
}

export interface StreamChunk {
  data: string;
  metadata?: {
    tokens?: number;
    filtered?: boolean;
  };
}
