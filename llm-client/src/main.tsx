import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './App.css';

console.log('[main.tsx] 脚本开始执行');
console.log('[main.tsx] document.getElementById("root"):', document.getElementById('root'));

const rootElement = document.getElementById('root');
if (!rootElement) {
  console.error('[main.tsx] 找不到 root 元素!');
  throw new Error('找不到 root 元素');
}

console.log('[main.tsx] 创建 React root');
const root = ReactDOM.createRoot(rootElement);

console.log('[main.tsx] 开始渲染 App');
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

console.log('[main.tsx] 渲染完成');
