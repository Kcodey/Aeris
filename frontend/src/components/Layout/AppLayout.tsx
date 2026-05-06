import React, { useState } from 'react'
import { Layout, Menu } from 'antd'
import {
  MessageOutlined,
  DashboardOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Sider, Content } = Layout

interface AppLayoutProps {
  children: React.ReactNode
  onLogout: () => void
}

const AppLayout: React.FC<AppLayoutProps> = ({ children, onLogout }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/', icon: <MessageOutlined />, label: '对话' },
    { key: '/monitoring', icon: <DashboardOutlined />, label: '监控' },
  ]

  const selectedKey = menuItems.find((item) =>
    location.pathname.startsWith(item.key)
  )?.key || '/'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{
          boxShadow: '2px 0 8px rgba(0,0,0,0.05)',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: collapsed ? 14 : 20,
            fontWeight: 'bold',
            color: '#1677ff',
          }}
        >
          {collapsed ? 'A' : 'Aeris'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: item.label,
            onClick: () => navigate(item.key),
          }))}
        />
        <Menu
          mode="inline"
          style={{ marginTop: 'auto' }}
          items={[
            {
              key: 'logout',
              icon: <LogoutOutlined />,
              label: '退出',
              onClick: onLogout,
            },
          ]}
        />
      </Sider>
      <Layout>
        <Content
          style={{
            margin: 16,
            background: '#fff',
            borderRadius: 8,
            height: 'calc(100vh - 32px)',
            overflow: 'hidden',
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout