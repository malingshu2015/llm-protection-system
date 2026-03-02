import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    title: 'LLM防护客户端',
    show: false
  });

  // 开发环境加载开发服务器
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // 生产环境使用 file:// 协议加载
    const indexPath = path.join(__dirname, '../dist/index.html');
    const fileUrl = `file://${indexPath}`;
    console.log('Loading URL:', fileUrl);
    console.log('__dirname:', __dirname);
    console.log('App path:', app.getAppPath());

    mainWindow.loadURL(fileUrl).catch(err => {
      console.error('Failed to load URL:', err);
      // 尝试备用路径
      const altPath = path.join(app.getAppPath(), 'dist', 'index.html');
      const altUrl = `file://${altPath}`;
      console.log('Trying alternative URL:', altUrl);
      mainWindow?.loadURL(altUrl).catch(err2 => {
        console.error('Alternative URL also failed:', err2);
      });
    });
    // 在生产环境也打开开发者工具用于调试
    mainWindow.webContents.openDevTools();
  }

  // 监听控制台消息
  mainWindow.webContents.on('console-message', (_event, _level, message) => {
    console.log('[Renderer]', message);
  });

  // 监听加载错误
  mainWindow.webContents.on('did-fail-load', (_event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });

  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    console.log('Window ready to show');
    mainWindow?.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 应用程序就绪时创建窗口
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC 通信处理
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('get-platform', () => {
  return process.platform;
});
