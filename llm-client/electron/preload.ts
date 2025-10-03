import { contextBridge, ipcRenderer } from 'electron';

// 向渲染进程暴露安全的 API
contextBridge.exposeInMainWorld('electronAPI', {
  // 应用信息
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),

  // 系统操作
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close'),

  // 文件操作
  selectFile: () => ipcRenderer.invoke('dialog-select-file'),
  selectFolder: () => ipcRenderer.invoke('dialog-select-folder'),

  // 存储操作
  storeGet: (key: string) => ipcRenderer.invoke('store-get', key),
  storeSet: (key: string, value: any) => ipcRenderer.invoke('store-set', key, value),
  storeDelete: (key: string) => ipcRenderer.invoke('store-delete', key),

  // 通知
  showNotification: (title: string, body: string) =>
    ipcRenderer.send('show-notification', { title, body }),

  // 事件监听
  onUpdateAvailable: (callback: (info: any) => void) =>
    ipcRenderer.on('update-available', (_, info) => callback(info)),
  onUpdateDownloaded: (callback: () => void) =>
    ipcRenderer.on('update-downloaded', () => callback()),
});

// TypeScript 类型定义
export interface ElectronAPI {
  getAppVersion: () => Promise<string>;
  getPlatform: () => Promise<string>;
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;
  selectFile: () => Promise<string | null>;
  selectFolder: () => Promise<string | null>;
  storeGet: (key: string) => Promise<any>;
  storeSet: (key: string, value: any) => Promise<void>;
  storeDelete: (key: string) => Promise<void>;
  showNotification: (title: string, body: string) => void;
  onUpdateAvailable: (callback: (info: any) => void) => void;
  onUpdateDownloaded: (callback: () => void) => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
