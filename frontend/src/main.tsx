import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import App from './App'
import './global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#d97706',
          colorSuccess: '#10b981',
          colorError: '#ef4444',
          colorWarning: '#f59e0b',
          colorInfo: '#3b82f6',
          borderRadius: 8,
          colorBgContainer: '#ffffff',
          colorBgElevated: '#ffffff',
          colorText: '#292524',
          colorTextSecondary: '#78716c',
          colorBorder: '#e7e5e4',
          controlOutline: 'rgba(217,119,6,0.15)',
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
)
