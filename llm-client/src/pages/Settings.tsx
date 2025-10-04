import React from 'react';
import { Card, Typography } from 'antd';

const { Title } = Typography;

const SettingsPage: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Title level={3}>设置</Title>
        {/* TODO: 设置选项 */}
      </Card>
    </div>
  );
};

export default SettingsPage;
