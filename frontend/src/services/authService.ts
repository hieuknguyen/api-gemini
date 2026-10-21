import { apiRequest, setAuthSession, clearAuthSession, getCurrentUser, getAuthToken } from './apiClient';
import { User } from '../types';

export interface LoginResponse {
  status: string;
  message: string;
  user: User;
  api_key: string;
}

export const authService = {
  async login(emailOrName: string, password: string): Promise<LoginResponse> {
    const data = await apiRequest<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: emailOrName, password }),
    });
    if (data && data.api_key && data.user) {
      setAuthSession(data.api_key, data.user);
    }
    return data;
  },

  async register(name: string, email: string, password: string, note?: string): Promise<LoginResponse> {
    const data = await apiRequest<LoginResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, note }),
    });
    if (data && data.api_key && data.user) {
      setAuthSession(data.api_key, data.user);
    }
    return data;
  },

  logout() {
    clearAuthSession();
  },

  getUser(): User | null {
    return getCurrentUser();
  },

  isLoggedIn(): boolean {
    return !!getAuthToken();
  },

  isAdmin(): boolean {
    const user = getCurrentUser();
    return user?.role === 'admin';
  },

  async getMe(): Promise<User> {
    const user = await apiRequest<User>('/api/users/me');
    if (user && user.id) {
      const token = getAuthToken();
      if (token) setAuthSession(token, user);
    }
    return user;
  }
};
