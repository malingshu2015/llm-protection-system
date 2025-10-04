import { io, Socket } from 'socket.io-client';
import { StreamChunk } from '@/types/api';

export class GatewayClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private serverUrl: string = '';
  private token: string = '';

  /**
   * 连接到服务器
   */
  async connect(serverUrl: string, token: string): Promise<void> {
    this.serverUrl = serverUrl;
    this.token = token;

    return new Promise((resolve, reject) => {
      this.socket = io(serverUrl, {
        auth: { token },
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: this.maxReconnectAttempts,
      });

      this.socket.on('connect', () => {
        console.log('✅ 已连接到服务器');
        this.reconnectAttempts = 0;
        resolve();
      });

      this.socket.on('disconnect', (reason) => {
        console.log('❌ 连接断开:', reason);
        if (reason === 'io server disconnect') {
          // 服务器主动断开,需要重新认证
          this.reconnect();
        }
      });

      this.socket.on('connect_error', (error) => {
        console.error('连接错误:', error);
        this.reconnectAttempts++;

        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          reject(new Error('连接失败,请检查网络'));
        }
      });

      // 策略更新事件
      this.socket.on('policy_update', (policy) => {
        this.handlePolicyUpdate(policy);
      });

      // 强制下线事件
      this.socket.on('force_logout', (reason) => {
        this.handleForceLogout(reason);
      });
    });
  }

  /**
   * 重新连接
   */
  private async reconnect(): Promise<void> {
    try {
      await this.connect(this.serverUrl, this.token);
    } catch (error) {
      console.error('重连失败:', error);
    }
  }

  /**
   * 发送聊天消息
   */
  async sendMessage(sessionId: string, message: string): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error('未连接到服务器'));
        return;
      }

      this.socket.emit(
        'chat:message',
        {
          sessionId,
          message,
          timestamp: Date.now(),
        },
        (response: any) => {
          if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response.reply);
          }
        }
      );
    });
  }

  /**
   * 流式响应
   */
  async streamMessage(
    sessionId: string,
    message: string,
    onChunk: (chunk: string) => void
  ): Promise<void> {
    if (!this.socket?.connected) {
      throw new Error('未连接到服务器');
    }

    return new Promise((resolve, reject) => {
      const streamId = `stream_${Date.now()}`;

      this.socket!.emit('chat:stream', {
        streamId,
        sessionId,
        message,
      });

      this.socket!.on(`stream:${streamId}:chunk`, (chunk: StreamChunk) => {
        onChunk(chunk.data);
      });

      this.socket!.on(`stream:${streamId}:end`, () => {
        this.socket!.off(`stream:${streamId}:chunk`);
        this.socket!.off(`stream:${streamId}:end`);
        this.socket!.off(`stream:${streamId}:error`);
        resolve();
      });

      this.socket!.on(`stream:${streamId}:error`, (error: any) => {
        this.socket!.off(`stream:${streamId}:chunk`);
        this.socket!.off(`stream:${streamId}:end`);
        this.socket!.off(`stream:${streamId}:error`);
        reject(new Error(error.message));
      });
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.socket?.disconnect();
    this.socket = null;
  }

  /**
   * 处理策略更新
   */
  private handlePolicyUpdate(policy: any): void {
    console.log('📋 策略已更新:', policy);
    // 触发策略更新事件
    window.dispatchEvent(
      new CustomEvent('policy_update', { detail: policy })
    );
  }

  /**
   * 处理强制下线
   */
  private handleForceLogout(reason: string): void {
    console.log('⚠️ 强制下线:', reason);
    // 触发强制下线事件
    window.dispatchEvent(
      new CustomEvent('force_logout', { detail: reason })
    );
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  /**
   * 发送 ping
   */
  ping(): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.socket?.connected) {
        reject(new Error('未连接到服务器'));
        return;
      }

      const startTime = Date.now();
      this.socket.emit('ping', { timestamp: startTime }, () => {
        const latency = Date.now() - startTime;
        resolve(latency);
      });
    });
  }
}

// 全局单例
export const gatewayClient = new GatewayClient();
