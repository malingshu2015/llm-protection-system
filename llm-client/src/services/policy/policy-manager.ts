import { Policy } from '@/types/policy';

export class PolicyManager {
  private currentPolicy: Policy | null = null;
  private syncInterval: NodeJS.Timeout | null = null;
  private listeners: Set<(policy: Policy) => void> = new Set();

  /**
   * 初始化策略管理器
   */
  async initialize(): Promise<void> {
    // 1. 从本地加载缓存的策略
    const cachedPolicy = await this.loadFromCache();
    if (cachedPolicy) {
      this.currentPolicy = cachedPolicy;
      this.notifyListeners();
    }

    // 2. 同步最新策略
    try {
      await this.sync();
    } catch (error) {
      console.error('初始策略同步失败:', error);
    }

    // 3. 启动定时同步
    this.startAutoSync();

    // 4. 监听策略更新事件
    window.addEventListener('policy_update', ((event: CustomEvent) => {
      this.handlePolicyUpdate(event.detail);
    }) as EventListener);
  }

  /**
   * 同步策略
   */
  async sync(): Promise<Policy> {
    try {
      // TODO: 从服务器获取最新策略
      // const response = await fetch(`${serverUrl}/api/v1/client/policies/latest`);
      // const data = await response.json();
      // const newPolicy = data.policy;

      // 模拟策略数据
      const newPolicy: Policy = {
        version: 1,
        patterns: {},
        keywords: [],
        updatedAt: new Date(),
      };

      // 检查是否有更新
      if (
        !this.currentPolicy ||
        newPolicy.version > this.currentPolicy.version
      ) {
        this.currentPolicy = newPolicy;
        await this.saveToCache(newPolicy);
        this.notifyListeners();

        console.log(`✅ 策略已更新到版本 ${newPolicy.version}`);
      }

      return newPolicy;
    } catch (error) {
      console.error('策略同步失败:', error);

      // 使用缓存的策略
      if (this.currentPolicy) {
        console.log('⚠️ 使用本地缓存的策略');
        return this.currentPolicy;
      }

      throw new Error('无法获取安全策略,请检查网络连接');
    }
  }

  /**
   * 启动自动同步
   */
  private startAutoSync(): void {
    // 每 5 分钟同步一次
    this.syncInterval = setInterval(() => {
      this.sync().catch(console.error);
    }, 5 * 60 * 1000);
  }

  /**
   * 停止自动同步
   */
  stopAutoSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * 监听策略更新
   */
  onPolicyUpdate(callback: (policy: Policy) => void): () => void {
    this.listeners.add(callback);
    // 返回取消监听函数
    return () => this.listeners.delete(callback);
  }

  /**
   * 通知监听器
   */
  private notifyListeners(): void {
    if (this.currentPolicy) {
      this.listeners.forEach((cb) => cb(this.currentPolicy!));
    }
  }

  /**
   * 处理策略更新事件
   */
  private handlePolicyUpdate(policy: Policy): void {
    this.currentPolicy = policy;
    this.saveToCache(policy).catch(console.error);
    this.notifyListeners();
  }

  /**
   * 从缓存加载策略
   */
  private async loadFromCache(): Promise<Policy | null> {
    try {
      const cached = localStorage.getItem('cached_policy');
      if (cached) {
        const policy = JSON.parse(cached);
        // 恢复日期对象
        policy.updatedAt = new Date(policy.updatedAt);
        return policy;
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * 保存策略到缓存
   */
  private async saveToCache(policy: Policy): Promise<void> {
    localStorage.setItem('cached_policy', JSON.stringify(policy));
  }

  /**
   * 获取当前策略
   */
  getCurrentPolicy(): Policy | null {
    return this.currentPolicy;
  }

  /**
   * 销毁策略管理器
   */
  destroy(): void {
    this.stopAutoSync();
    this.listeners.clear();
  }
}

// 全局单例
export const policyManager = new PolicyManager();
