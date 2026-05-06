import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { message } from 'antd'
import Login from './pages/Login'
import ChatPage from './pages/ChatPage'
import MonitoringPage from './pages/MonitoringPage'
import AppLayout from './components/Layout/AppLayout'
import { getToken, removeToken } from './utils/token'

function App() {
  // TEMP: Tailwind verification element - will be removed after validation
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = getToken()
    setIsAuthenticated(!!token)
    setIsLoading(false)
  }, [])

  const handleLogin = () => {
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    removeToken()
    setIsAuthenticated(false)
    message.success('已退出登录')
  }

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-surface-page"
        // TEMP: Tailwind verification - amber dot should appear top-right if Tailwind works
      >
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 bg-brand rounded-2xl shadow-glow" />
          <span className="text-caption text-content-secondary">Loading...</span>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to="/" /> : <Login onLogin={handleLogin} />
          }
        />
        <Route
          path="/*"
          element={
            isAuthenticated ? (
              <AppLayout onLogout={handleLogout}>
                <Routes>
                  <Route path="/" element={<ChatPage />} />
                  <Route path="/monitoring" element={<MonitoringPage />} />
                </Routes>
              </AppLayout>
            ) : (
              <Navigate to="/login" />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
