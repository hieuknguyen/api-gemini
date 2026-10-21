import { apiRequest } from './apiClient';
import { QuotaStats, RequestLog } from '../types';

export const quotaService = {
  async getStats(): Promise<QuotaStats> {
    return apiRequest<QuotaStats>('/api/quota/stats');
  },

  async getLogs(limit: number = 50): Promise<RequestLog[]> {
    return apiRequest<RequestLog[]>(`/api/quota/logs?limit=${limit}`);
  },

  async clearLogs(): Promise<any> {
    return apiRequest('/api/quota/clear', {
      method: 'POST',
    });
  }
};
