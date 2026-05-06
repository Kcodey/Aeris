import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../services/auth'
import { setToken } from '../utils/token'
import { LoginRequest, RegisterRequest } from '../types/auth'

interface LoginProps {
  onLogin: () => void
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const values: LoginRequest = {
      username: formData.get('username') as string,
      password: formData.get('password') as string,
    }

    setLoading(true)
    setError('')
    try {
      const response = await authApi.login(values)
      setToken(response.data.access_token)
      onLogin()
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const password = formData.get('password') as string
    const confirmPassword = formData.get('confirmPassword') as string

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    const values: RegisterRequest = {
      username: formData.get('username') as string,
      password,
    }

    setLoading(true)
    setError('')
    try {
      await authApi.register(values)
      setActiveTab('login')
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-surface-page relative overflow-hidden">
      {/* Ambient glow background */}
      <div className="absolute -top-20 -left-20 w-[400px] h-[400px] rounded-full bg-[radial-gradient(circle,rgba(251,191,36,0.2)_0%,transparent_70%)] animate-float" />
      <div
        className="absolute -bottom-16 -right-16 w-[350px] h-[350px] rounded-full bg-[radial-gradient(circle,rgba(217,119,6,0.12)_0%,transparent_70%)] animate-float"
        style={{ animationDelay: '-10s' }}
      />

      {/* Glass card */}
      <div
        className="relative z-10 w-[360px] max-w-[90vw] bg-white/85 border border-white/60 rounded-2xl shadow-floating p-8"
        style={{ backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }}
      >
        {/* Brand */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 bg-brand rounded-[14px] flex items-center justify-center text-white text-xl font-bold mb-3 shadow-glow">
            A
          </div>
          <h1 className="text-xl font-bold text-content-primary">Aeris</h1>
          <p className="text-caption text-content-secondary mt-1">AI Agent Platform</p>
        </div>

        {/* Tab switch */}
        <div className="flex gap-1 bg-surface-page rounded-lg p-1 mb-6">
          <button
            onClick={() => {
              setActiveTab('login')
              setError('')
            }}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
              activeTab === 'login'
                ? 'bg-brand-light text-amber-800 font-semibold'
                : 'text-content-secondary hover:text-content-primary'
            }`}
          >
            登录
          </button>
          <button
            onClick={() => {
              setActiveTab('register')
              setError('')
            }}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
              activeTab === 'register'
                ? 'bg-brand-light text-amber-800 font-semibold'
                : 'text-content-secondary hover:text-content-primary'
            }`}
          >
            注册
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 px-3 py-2 bg-red-50 border border-red-100 rounded-md text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Forms */}
        {activeTab === 'login' ? (
          <form onSubmit={handleLogin} className="flex flex-col gap-3">
            <input
              name="username"
              type="text"
              required
              placeholder="用户名"
              className="w-full h-11 px-4 bg-surface-page border border-border rounded-md text-body text-content-primary placeholder-content-tertiary transition-all duration-200 focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none"
            />
            <input
              name="password"
              type="password"
              required
              placeholder="密码"
              className="w-full h-11 px-4 bg-surface-page border border-border rounded-md text-body text-content-primary placeholder-content-tertiary transition-all duration-200 focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 mt-2 bg-brand text-white rounded-md text-sm font-medium shadow-glow transition-all duration-200 hover:bg-brand-dark hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(217,119,6,0.35)] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="flex flex-col gap-3">
            <input
              name="username"
              type="text"
              required
              placeholder="用户名"
              className="w-full h-11 px-4 bg-surface-page border border-border rounded-md text-body text-content-primary placeholder-content-tertiary transition-all duration-200 focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none"
            />
            <input
              name="password"
              type="password"
              required
              minLength={6}
              placeholder="密码（至少6位）"
              className="w-full h-11 px-4 bg-surface-page border border-border rounded-md text-body text-content-primary placeholder-content-tertiary transition-all duration-200 focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none"
            />
            <input
              name="confirmPassword"
              type="password"
              required
              placeholder="确认密码"
              className="w-full h-11 px-4 bg-surface-page border border-border rounded-md text-body text-content-primary placeholder-content-tertiary transition-all duration-200 focus:border-brand focus:ring-2 focus:ring-brand/15 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 mt-2 bg-brand text-white rounded-md text-sm font-medium shadow-glow transition-all duration-200 hover:bg-brand-dark hover:-translate-y-px hover:shadow-[0_4px_16px_rgba(217,119,6,0.35)] active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '注册中...' : '注册'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default Login
