import React, { useState, useRef, KeyboardEvent } from 'react';
import { Input, Button, Tooltip, Space } from 'antd';
import { SendOutlined, PaperClipOutlined } from '@ant-design/icons';
import './InputBox.css';

const { TextArea } = Input;

interface InputBoxProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export const InputBox: React.FC<InputBoxProps> = ({
  onSend,
  disabled = false,
  loading = false,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<any>(null);

  const handleSend = () => {
    if (!text.trim() || disabled || loading) return;

    onSend(text.trim());
    setText('');

    // 重置高度
    if (textareaRef.current?.resizableTextArea?.textArea) {
      textareaRef.current.resizableTextArea.textArea.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl/Cmd + Enter 发送
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="input-box">
      <div className="input-wrapper">
        <Space.Compact style={{ width: '100%' }}>
          <Tooltip title="附加文件">
            <Button
              type="text"
              icon={<PaperClipOutlined />}
              disabled={disabled || loading}
            />
          </Tooltip>

          <TextArea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... (Ctrl+Enter 发送)"
            disabled={disabled || loading}
            autoSize={{ minRows: 1, maxRows: 6 }}
            style={{ flex: 1 }}
          />

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!text.trim() || disabled}
            loading={loading}
          >
            发送
          </Button>
        </Space.Compact>
      </div>

      <div className="input-footer">
        <span className="hint">{text.length} 字符 | Ctrl+Enter 发送</span>
      </div>
    </div>
  );
};
