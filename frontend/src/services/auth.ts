import api from './api'
import {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
} from '../types/auth'

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login', data, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),

  register: (data: RegisterRequest) =>
    api.post<RegisterResponse>('/auth/register', data),

  getCurrentUser: () => api.get<User>('/auth/me'),
}
