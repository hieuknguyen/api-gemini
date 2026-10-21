import { apiRequest } from './apiClient';
import { TokenPackage, PaymentTransaction, MoMoPaymentCreateResponse, MoMoConfig } from '../types';

export interface PaymentPackagesResponse {
  status: string;
  packages: TokenPackage[];
  rate_vnd_per_million_tokens: number;
  description: string;
}

export interface CheckOrderStatusResponse {
  status: 'pending' | 'success' | 'failed';
  order_id: string;
  amount: number;
  tokens_granted: number;
  package_name?: string;
  message?: string;
  user_token_balance: number;
  updated_at: string;
}

export const paymentService = {
  async getPackages(): Promise<PaymentPackagesResponse> {
    return apiRequest<PaymentPackagesResponse>('/api/payment/packages');
  },

  async createPayment(
    packageId?: string,
    customAmount?: number,
    redirectUrl?: string
  ): Promise<MoMoPaymentCreateResponse> {
    return apiRequest<MoMoPaymentCreateResponse>('/api/payment/momo/create', {
      method: 'POST',
      body: JSON.stringify({
        package_id: packageId || undefined,
        amount: customAmount || undefined,
        redirect_url: redirectUrl || window.location.origin
      }),
    });
  },

  async checkOrderStatus(orderId: string): Promise<CheckOrderStatusResponse> {
    return apiRequest<CheckOrderStatusResponse>(`/api/payment/momo/check/${orderId}`);
  },

  async getMyTransactions(): Promise<PaymentTransaction[]> {
    return apiRequest<PaymentTransaction[]>('/api/payment/my-transactions');
  },

  async getAllTransactionsAdmin(): Promise<PaymentTransaction[]> {
    return apiRequest<PaymentTransaction[]>('/api/payment/admin/transactions');
  },

  async getMoMoConfigAdmin(): Promise<MoMoConfig> {
    return apiRequest<MoMoConfig>('/api/payment/admin/momo-config');
  },

  async updateMoMoConfigAdmin(config: Partial<MoMoConfig>): Promise<any> {
    return apiRequest<any>('/api/payment/admin/momo-config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  async adjustUserTokensAdmin(userId: string, tokens: number, amount: number = 0): Promise<any> {
    return apiRequest<any>(`/api/users/${userId}/tokens`, {
      method: 'POST',
      body: JSON.stringify({ tokens, amount }),
    });
  }
};
