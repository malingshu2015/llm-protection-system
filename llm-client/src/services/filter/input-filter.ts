import { Policy, FilterResult } from '@/types/policy';

export class InputFilter {
  private sensitivePatterns: Map<string, RegExp> = new Map();
  private blockedKeywords: Set<string> = new Set();
  private policy: Policy | null = null;

  /**
   * 加载策略
   */
  loadPolicy(policy: Policy): void {
    this.policy = policy;

    // 编译正则表达式
    this.sensitivePatterns.clear();
    for (const [name, pattern] of Object.entries(policy.patterns)) {
      try {
        this.sensitivePatterns.set(name, new RegExp(pattern, 'gi'));
      } catch (error) {
        console.error(`正则表达式编译失败: ${name}`, error);
      }
    }

    // 加载敏感词
    this.blockedKeywords = new Set(policy.keywords);
  }

  /**
   * 过滤输入文本
   */
  async filter(text: string): Promise<FilterResult> {
    // 1. 快速检查:敏感词
    const keywordCheck = this.checkKeywords(text);
    if (keywordCheck.blocked) {
      return keywordCheck;
    }

    // 2. 模式匹配检查
    const patternCheck = this.checkPatterns(text);
    if (patternCheck.blocked) {
      return patternCheck;
    }

    // 3. 自定义规则检查
    if (this.policy?.customRules) {
      const customCheck = await this.checkCustomRules(text);
      if (customCheck.blocked) {
        return customCheck;
      }
    }

    return {
      blocked: false,
      text,
      confidence: 1.0,
    };
  }

  /**
   * 检查敏感词
   */
  private checkKeywords(text: string): FilterResult {
    const lowerText = text.toLowerCase();

    for (const keyword of this.blockedKeywords) {
      if (lowerText.includes(keyword.toLowerCase())) {
        return {
          blocked: true,
          reason: `包含敏感词: ${keyword}`,
          suggestions: ['请重新表述您的问题', '避免使用敏感词汇'],
          text,
          confidence: 1.0,
        };
      }
    }

    return { blocked: false, text, confidence: 1.0 };
  }

  /**
   * 检查模式匹配
   */
  private checkPatterns(text: string): FilterResult {
    for (const [name, pattern] of this.sensitivePatterns) {
      const matches = text.match(pattern);
      if (matches) {
        return {
          blocked: true,
          reason: `匹配到敏感模式: ${name}`,
          matches: matches.map((m) => ({ text: m, pattern: name })),
          text,
          confidence: 0.9,
        };
      }
    }

    return { blocked: false, text, confidence: 1.0 };
  }

  /**
   * 检查自定义规则
   */
  private async checkCustomRules(text: string): Promise<FilterResult> {
    // 执行自定义 JavaScript 规则
    try {
      for (const rule of this.policy!.customRules!) {
        if (!rule.enabled) continue;

        const fn = new Function('text', rule.code);
        const result = fn(text);

        if (result.blocked) {
          return {
            blocked: true,
            reason: result.reason || '违反自定义规则',
            text,
            confidence: result.confidence || 0.8,
          };
        }
      }
    } catch (error) {
      console.error('自定义规则执行失败:', error);
    }

    return { blocked: false, text, confidence: 1.0 };
  }

  /**
   * 获取当前策略
   */
  getCurrentPolicy(): Policy | null {
    return this.policy;
  }
}

// 全局单例
export const inputFilter = new InputFilter();
