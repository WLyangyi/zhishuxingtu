import api from './index'
import type { 
  Skill, SkillCreate, SkillUpdate, SkillListResponse,
  SkillExecution, SkillExecutionCreate, SkillTemplate
} from '@/types/skill'

export const skillsApi = {
  async getTemplates(): Promise<SkillTemplate[]> {
    const response = await api.get('/skills/templates')
    return response.data
  },

  async getSkills(params?: {
    is_template?: boolean
    page?: number
    page_size?: number
  }): Promise<SkillListResponse> {
    const response = await api.get('/skills', { params })
    return response.data
  },

  async getSkill(id: string): Promise<Skill> {
    const response = await api.get(`/skills/${id}`)
    return response.data
  },

  async createSkill(data: SkillCreate): Promise<Skill> {
    const response = await api.post('/skills', data)
    return response.data
  },

  async createFromTemplate(templateIndex: number): Promise<Skill> {
    const response = await api.post(`/skills/from-template/${templateIndex}`)
    return response.data
  },

  async updateSkill(id: string, data: SkillUpdate): Promise<Skill> {
    const response = await api.put(`/skills/${id}`, data)
    return response.data
  },

  async deleteSkill(id: string): Promise<void> {
    await api.delete(`/skills/${id}`)
  },

  async executeSkill(id: string, data: SkillExecutionCreate): Promise<SkillExecution> {
    const response = await api.post(`/skills/${id}/execute`, data)
    return response.data
  },

  async getExecutions(skillId: string, limit: number = 20): Promise<SkillExecution[]> {
    const response = await api.get(`/skills/${skillId}/executions`, {
      params: { limit }
    })
    return response.data
  }
}
