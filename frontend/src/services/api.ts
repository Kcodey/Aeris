import axios, { AxiosError } from 'axios'
import { message } from 'antd'
import { getToken, removeToken } from '../utils/token'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      removeToken()
      window.location.href = '/login'
      message.error('登录已过期，请重新登录')
    } else {
      const detail = (error.response?.data as any)?.detail
      message.error(detail || '请求失败')
    }
    return Promise.reject(error)
  }
)

export default api
