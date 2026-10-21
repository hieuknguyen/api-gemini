import { apiRequest } from './apiClient';
import { SystemSettings } from '../types';

export const settingsService = {
  async getSettings(): Promise<SystemSettings> {
    return apiRequest<SystemSettings>('/api/settings');
  },

  async updateSettings(settings: Partial<SystemSettings>): Promise<any> {
    return apiRequest('/api/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  },

  async generateKey(): Promise<{ api_key: string }> {
    return apiRequest<{ api_key: string }>('/api/settings/generate-key', {
      method: 'POST',
    });
  },

  async saveGoogleOAuth(client_id: string, client_secret?: string): Promise<SystemSettings> {
    return apiRequest<SystemSettings>('/api/settings/google-oauth', {
      method: 'POST',
      body: JSON.stringify({ client_id, client_secret }),
    });
  },

  async deleteGoogleOAuth(): Promise<void> {
    return apiRequest<void>('/api/settings/google-oauth', {
      method: 'DELETE',
    });
  },
};
