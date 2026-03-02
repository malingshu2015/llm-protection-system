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
  private baseURL: string = '';

  constructor() {
    this.client = axios.create({
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
    this.baseURL = url;
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
}

// 导出单例
export const apiService = new ApiService();
