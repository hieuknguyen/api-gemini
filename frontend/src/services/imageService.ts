import { apiRequest } from './apiClient';

export interface ImageGenerateParams {
  prompt: string;
  style?: string;
  aspect_ratio?: string;
  model?: string;
  enhance_prompt?: boolean;
  seed?: number;
}

export interface ImageGenerateResult {
  status: string;
  image_url?: string;
  data?: string;
  prompt: string;
  enhanced_prompt?: string;
}

export const imageService = {
  async generateImage(params: ImageGenerateParams): Promise<ImageGenerateResult> {
    return apiRequest<ImageGenerateResult>('/api/image/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async enhancePrompt(prompt: string, style?: string): Promise<{ enhanced_prompt: string }> {
    return apiRequest('/api/image/enhance-prompt', {
      method: 'POST',
      body: JSON.stringify({ prompt, style }),
    });
  }
};
