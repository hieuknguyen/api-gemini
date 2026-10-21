import { apiRequest } from './apiClient';
import { Skill } from '../types';

export const skillService = {
  async getSkills(): Promise<Skill[]> {
    return apiRequest<Skill[]>('/api/skills');
  },

  async updateSkill(id: string, system_prompt: string): Promise<Skill> {
    return apiRequest<Skill>(`/api/skills/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ system_prompt }),
    });
  },

};
