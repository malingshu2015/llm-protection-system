// 安全策略相关类型

export interface Policy {
  version: number;
  patterns: Record<string, string>;
  keywords: string[];
  customRules?: CustomRule[];
  inputRules?: FilterRule[];
  outputRules?: FilterRule[];
  modelConfig?: ModelConfig;
  updatedAt: Date;
}

export interface CustomRule {
  name: string;
  code: string;
  enabled: boolean;
}

export interface FilterRule {
  id: string;
  name: string;
  pattern?: string;
  keywords?: string[];
  severity: 'low' | 'medium' | 'high';
  action: 'block' | 'warn' | 'log';
  enabled: boolean;
}

export interface ModelConfig {
  maxTokens?: number;
  temperature?: number;
  allowedModels?: string[];
  blockedModels?: string[];
}

export interface FilterResult {
  blocked: boolean;
  text?: string;
  reason?: string;
  suggestions?: string[];
  matches?: Array<{
    text: string;
    pattern: string;
  }>;
  confidence: number;
}
