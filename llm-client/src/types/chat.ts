// 聊天相关类型

export interface Session {
  id: string;
  modelId: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  metadata: SessionMetadata;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  tokens?: number;
  filtered?: boolean;
  warnings?: string[];
  isError?: boolean;
  images?: string[];  // 添加图片附件字段
}

export interface SessionMetadata {
  tags: string[];
  tokens: number;
  cost: number;
  archived?: boolean;
}

export interface Model {
  id: string;
  name: string;
  provider: string;
  description?: string;
  maxTokens?: number;
  available: boolean;
}
