/**
 * API 服务模块
 * 封装所有后端 API 调用
 */

import axios, { AxiosInstance } from 'axios';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    email: string;
  };
}

export interface ApiError {
  detail: string;
  code?: string;
}

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: 'http://localhost:8082', // 设置默认 baseURL
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('[API] 请求失败:', error);
        throw error;
      }
    );
  }

  /**
   * 设置服务器地址
   */
  setBaseURL(url: string) {
    this.client.defaults.baseURL = url;
  }

  /**
   * 设置认证令牌
   */
  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  /**
   * 用户登录
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      const response = await this.client.post<LoginResponse>(
        '/api/v1/auth/login',
        {
          username,
          password,
          remember_me: true,
        }
      );

      return response.data;
    } catch (error: any) {
      console.error('[API] 登录失败:', error);
      throw new Error(error.response?.data?.detail || '登录失败');
    }
  }

  /**
   * 用户注册
   */
  async register(username: string, email: string, password: string) {
    try {
      const response = await this.client.post('/api/v1/auth/register', {
        username,
        email,
        password,
      });

      return response.data;
    } catch (error: any) {
      console.error('[API] 注册失败:', error);
      throw new Error(error.response?.data?.detail || '注册失败');
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser() {
    try {
      const response = await this.client.get('/api/v1/auth/me');
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取用户信息失败:', error);
      throw new Error(error.response?.data?.detail || '获取用户信息失败');
    }
  }

  /**
   * 健康检查
   */
  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error: any) {
      console.error('[API] 健康检查失败:', error);
      throw new Error('服务器连接失败');
    }
  }

  /**
   * 获取可用模型列表
   */
  async getModels() {
    try {
      const response = await this.client.get('/api/v1/models');
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取模型列表失败:', error);
      throw new Error(error.response?.data?.detail || '获取模型列表失败');
    }
  }

  /**
   * 获取全局安全设置
   */
  async getSecuritySettings() {
    try {
      const response = await this.client.get('/api/v1/settings/security');
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取安全设置失败:', error);
      throw new Error(error.response?.data?.detail || '获取安全设置失败');
    }
  }

  /**
   * 更新全局安全设置
   */
  async updateSecuritySettings(settings: any) {
    try {
      // 提取模型选择并单独保存
      const { selected_models, ...securitySettings } = settings;

      // 保存安全设置
      const response = await this.client.put('/api/v1/settings/security', securitySettings);

      // 如果有选择的模型，保存模型配置
      if (selected_models && Array.isArray(selected_models)) {
        localStorage.setItem('selected_models', JSON.stringify(selected_models));
        console.log('[API] 已保存选择的模型:', selected_models);
      }

      return response.data;
    } catch (error: any) {
      console.error('[API] 更新安全设置失败:', error);
      throw new Error(error.response?.data?.detail || '更新安全设置失败');
    }
  }

  /**
   * 获取选择的模型列表
   */
  getSelectedModels(): string[] {
    try {
      const saved = localStorage.getItem('selected_models');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  }

  // ==================== 规则管理 API ====================

  /**
   * 获取所有规则
   */
  async getRules(params?: { detection_type?: string; enabled?: boolean; category?: string }) {
    try {
      const response = await this.client.get('/api/v1/rules', { params });
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取规则列表失败:', error);
      throw new Error(error.response?.data?.detail || '获取规则列表失败');
    }
  }

  /**
   * 获取单个规则详情
   */
  async getRule(ruleId: string) {
    try {
      const response = await this.client.get(`/api/v1/rules/${ruleId}`);
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取规则详情失败:', error);
      throw new Error(error.response?.data?.detail || '获取规则详情失败');
    }
  }

  /**
   * 创建新规则
   */
  async createRule(rule: any) {
    try {
      const response = await this.client.post('/api/v1/rules', rule);
      return response.data;
    } catch (error: any) {
      console.error('[API] 创建规则失败:', error);
      throw new Error(error.response?.data?.detail || '创建规则失败');
    }
  }

  /**
   * 更新规则
   */
  async updateRule(ruleId: string, rule: any) {
    try {
      const response = await this.client.put(`/api/v1/rules/${ruleId}`, rule);
      return response.data;
    } catch (error: any) {
      console.error('[API] 更新规则失败:', error);
      throw new Error(error.response?.data?.detail || '更新规则失败');
    }
  }

  /**
   * 删除规则
   */
  async deleteRule(ruleId: string) {
    try {
      const response = await this.client.delete(`/api/v1/rules/${ruleId}`);
      return response.data;
    } catch (error: any) {
      console.error('[API] 删除规则失败:', error);
      throw new Error(error.response?.data?.detail || '删除规则失败');
    }
  }

  /**
   * 批量启用/禁用规则
   */
  async batchToggleRules(ruleIds: string[], enabled: boolean) {
    try {
      const promises = ruleIds.map(id =>
        this.client.put(`/api/v1/rules/${id}`, { enabled })
      );
      await Promise.all(promises);
      return { success: true, message: `已${enabled ? '启用' : '禁用'} ${ruleIds.length} 条规则` };
    } catch (error: any) {
      console.error('[API] 批量操作规则失败:', error);
      throw new Error(error.response?.data?.detail || '批量操作规则失败');
    }
  }

  /**
   * 批量删除规则
   */
  async batchDeleteRules(ruleIds: string[]) {
    try {
      const promises = ruleIds.map(id =>
        this.client.delete(`/api/v1/rules/${id}`)
      );
      await Promise.all(promises);
      return { success: true, message: `已删除 ${ruleIds.length} 条规则` };
    } catch (error: any) {
      console.error('[API] 批量删除规则失败:', error);
      throw new Error(error.response?.data?.detail || '批量删除规则失败');
    }
  }

  /**
   * 获取规则统计信息
   */
  async getRulesStats() {
    try {
      const response = await this.client.get('/api/v1/rules/stats');
      return response.data;
    } catch (error: any) {
      console.error('[API] 获取规则统计失败:', error);
      // 如果后端没有实现，返回空数据
      return { total: 0, enabled: 0, by_type: {}, by_severity: {} };
    }
  }

  /**
   * 验证正则表达式
   */
  async validatePattern(pattern: string, testText: string) {
    try {
      const response = await this.client.post('/api/v1/rules/validate-pattern', {
        pattern,
        test_text: testText
      });
      return response.data;
    } catch (error: any) {
      console.error('[API] 验证正则表达式失败:', error);
      // 本地验证作为后备
      try {
        const regex = new RegExp(pattern, 'i');
        const matches = regex.test(testText);
        return { valid: true, matches };
      } catch (e) {
        return { valid: false, error: '无效的正则表达式' };
      }
    }
  }
}

// 导出单例
export const apiService = new ApiService();
