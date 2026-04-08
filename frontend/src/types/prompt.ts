export interface Prompt {
  id: string
  user_id: string | null
  name: string
  description: string | null
  category: string
  system_prompt: string
  user_prompt_template: string
  output_format: string
  variables: string[]
  is_system: boolean
  is_active: boolean
  is_default: boolean
  priority: string
  created_at: string
  updated_at: string
}

export interface PromptCreate {
  name: string
  description?: string
  category: string
  system_prompt: string
  user_prompt_template?: string
  output_format?: string
  variables?: string[]
  is_system?: boolean
  is_active?: boolean
  is_default?: boolean
  priority?: string
}

export interface PromptUpdate {
  name?: string
  description?: string
  category?: string
  system_prompt?: string
  user_prompt_template?: string
  output_format?: string
  variables?: string[]
  is_active?: boolean
  is_default?: boolean
  priority?: string
}

export interface PromptTemplate {
  name: string
  description: string
  category: string
  system_prompt: string
  user_prompt_template: string
  output_format: string
  variables: string[]
}

export interface PromptListResponse {
  items: Prompt[]
  total: number
  page: number
  page_size: number
}

export interface PromptCategory {
  value: string
  label: string
}

export const PROMPT_CATEGORIES: Record<string, string> = {
  ai_chat: 'AI 对话',
  ai_search: 'AI 搜索',
  skill: '技能模板',
  custom: '自定义'
}
