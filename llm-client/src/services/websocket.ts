/**
 * WebSocket 客户端服务
 * 负责与后端建立和维护 WebSocket 连接
 */


export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

class WebSocketService {
  private socket: WebSocket | null = null;
  private serverUrl: string = '';
  private token: string = '';
  private clientId: string = '';
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private messageHandlers: Map<string, Set<(data: any) => void>> = new Map();

  /**
   * 初始化 WebSocket 连接
   */
  connect(serverUrl: string, token: string, clientId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.serverUrl = serverUrl;
      this.token = token;
      this.clientId = clientId;

      // 转换 HTTP URL 为 WebSocket URL
      let wsUrl = serverUrl;
      if (serverUrl.startsWith('http://')) {
        wsUrl = serverUrl.replace('http://', 'ws://');
      } else if (serverUrl.startsWith('https://')) {
        wsUrl = serverUrl.replace('https://', 'wss://');
      }

      const fullUrl = `${wsUrl}/api/v1/client/ws?token=${encodeURIComponent(token)}&client_id=${encodeURIComponent(clientId)}`;

      console.log('[WebSocket] 连接到:', fullUrl);

      // 创建原生 WebSocket 连接(因为后端使用 FastAPI WebSocket)
      const ws = new WebSocket(fullUrl);

      ws.onopen = () => {
        console.log('[WebSocket] 连接成功');
        this.reconnectAttempts = 0;
        resolve();
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error);
        reject(error);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] 连接关闭:', event.code, event.reason);
        this.handleReconnect();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('[WebSocket] 收到消息:', message);
          this.handleMessage(message);
        } catch (error) {
          console.error('[WebSocket] 解析消息失败:', error);
        }
      };

      // 保存 WebSocket 实例
      this.socket = ws;
    });
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(message: WebSocketMessage) {
    const handlers = this.messageHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => handler(message.data || message));
    }

    // 触发通用消息处理器
    const allHandlers = this.messageHandlers.get('*');
    if (allHandlers) {
      allHandlers.forEach(handler => handler(message));
    }
  }

  /**
   * 处理重连
   */
  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`[WebSocket] ${delay}ms 后尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connect(this.serverUrl, this.token, this.clientId).catch(err => {
          console.error('[WebSocket] 重连失败:', err);
        });
      }, delay);
    }
  }

  /**
   * 发送消息
   */
  send(type: string, data?: any): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log('[WebSocket] 准备发送消息, readyState:', this.socket?.readyState, 'OPEN=', WebSocket.OPEN);

      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
        const error = new Error('WebSocket 未连接');
        console.error('[WebSocket] 发送失败:', error);
        reject(error);
        return;
      }

      const message = {
        type,
        data,
        timestamp: new Date().toISOString(),
      };

      try {
        const msgStr = JSON.stringify(message);
        console.log('[WebSocket] 发送消息:', message);
        console.log('[WebSocket] 消息JSON:', msgStr);
        this.socket.send(msgStr);
        console.log('[WebSocket] 消息已发送');
        resolve();
      } catch (error) {
        console.error('[WebSocket] 发送异常:', error);
        reject(error);
      }
    });
  }

  /**
   * 发送聊天消息
   */
  async sendChatMessage(sessionId: string, message: string): Promise<void> {
    await this.send('chat:message', {
      sessionId,
      message,
    });
  }

  /**
   * 注册消息处理器
   */
  on(type: string, handler: (data: any) => void): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    this.messageHandlers.get(type)!.add(handler);
  }

  /**
   * 移除消息处理器
   */
  off(type: string, handler: (data: any) => void): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.messageHandlers.clear();
    console.log('[WebSocket] 已断开连接');
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
}

// 导出单例
export const websocketService = new WebSocketService();
