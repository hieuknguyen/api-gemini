import { apiRequest } from './apiClient';
import { User, ApiKey } from '../types';

export const userService = {
  async getUsers(): Promise<User[]> {
    return apiRequest<User[]>('/api/users');
  },

  async getUsersSummary(): Promise<Array<{ id: string; name: string; email: string; role: string }>> {
    return apiRequest('/api/users/summary');
  },

  async createUser(payload: { name: string; email: string; password?: string; note?: string; role?: string }): Promise<User> {
    return apiRequest<User>('/api/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateUser(id: string, payload: { name?: string; email?: string; password?: string; note?: string; role?: string; is_active?: boolean }): Promise<User> {
    return apiRequest<User>(`/api/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  async deleteUser(id: string): Promise<any> {
    return apiRequest(`/api/users/${id}`, {
      method: 'DELETE',
    });
  },

  async getUserKeys(userId: string): Promise<ApiKey[]> {
    return apiRequest<ApiKey[]>(`/api/users/${userId}/keys`);
  },

  async createApiKey(userId: string, name: string, customKey?: string): Promise<ApiKey> {
    return apiRequest<ApiKey>(`/api/users/${userId}/keys`, {
      method: 'POST',
      body: JSON.stringify({ name, custom_key: customKey }),
    });
  },

  async deleteApiKey(keyId: string): Promise<any> {
    return apiRequest(`/api/keys/${keyId}`, {
      method: 'DELETE',
    });
  },

  async toggleApiKey(keyId: string): Promise<any> {
    return apiRequest(`/api/keys/${keyId}/toggle`, {
      method: 'POST',
    });
  }
};
