import { apiRequest } from './apiClient';
import { GoogleAccount } from '../types';

export const accountService = {
  async getAccounts(): Promise<GoogleAccount[]> {
    return apiRequest<GoogleAccount[]>('/api/accounts');
  },

  async addManualAccount(refreshTokenOrUrl: string, name?: string): Promise<any> {
    return apiRequest('/api/accounts/manual', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshTokenOrUrl, name }),
    });
  },

  async exchangeOAuthCode(codeOrUrl: string, name?: string): Promise<any> {
    return apiRequest('/api/accounts/oauth/exchange', {
      method: 'POST',
      body: JSON.stringify({ code_or_url: codeOrUrl, name }),
    });
  },

  async toggleAccount(id: string): Promise<any> {
    return apiRequest(`/api/accounts/${id}/toggle`, {
      method: 'POST',
    });
  },

  async resetCooldown(id: string): Promise<any> {
    return apiRequest(`/api/accounts/${id}/reset-cooldown`, {
      method: 'POST',
    });
  },

  async setPrimary(id: string): Promise<any> {
    return apiRequest(`/api/accounts/${id}/primary`, {
      method: 'POST',
    });
  },

  async testAccount(id: string): Promise<any> {
    return apiRequest(`/api/accounts/${id}/test`, {
      method: 'POST',
    });
  },

  async deleteAccount(id: string): Promise<any> {
    return apiRequest(`/api/accounts/${id}`, {
      method: 'DELETE',
    });
  },

  async startOAuth(): Promise<{ url: string; auth_url: string; port?: number; redirect_uri?: string }> {
    return apiRequest('/api/accounts/oauth/start', {
      method: 'POST',
    });
  }
};
