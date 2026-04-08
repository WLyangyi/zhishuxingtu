export interface Skill {
  id: string
  user_id: string
  name: string
  description: string | null
  icon: string
  color: string
  input_schema: Record<string, any>
  output_schema: Record<string, any>
  execution_logic: Record<string, any>
  trigger_type: string
  schedule_config: Record<string, any>
  output_category_id: string | null
  output_type_id: string | null
  output_tag_ids: string[]
  is_template: boolean
  is_active: boolean
  execution_count?: number
  created_at: string
  updated_at: string
}

export interface SkillCreate {
  name: string
  description?: string
  icon?: string
  color?: string
  input_schema?: Record<string, any>
  output_schema?: Record<string, any>
  execution_logic?: Record<string, any>
  trigger_type?: string
  schedule_config?: Record<string, any>
  output_category_id?: string
  output_type_id?: string
  output_tag_ids?: string[]
}

export interface SkillUpdate {
  name?: string
  description?: string
  icon?: string
  color?: string
  input_schema?: Record<string, any>
  output_schema?: Record<string, any>
  execution_logic?: Record<string, any>
  trigger_type?: string
  schedule_config?: Record<string, any>
  output_category_id?: string
  output_type_id?: string
  output_tag_ids?: string[]
  is_active?: boolean
}

export interface SkillExecution {
  id: string
  skill_id: string
  user_id: string
  input_data: Record<string, any> | null
  output_data: Record<string, any> | null
  output_content_id: string | null
  status: string
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface SkillExecutionCreate {
  input_data?: Record<string, any>
}

export interface SkillTemplate {
  name: string
  description: string
  icon: string
  color: string
  input_schema: Record<string, any>
  output_schema: Record<string, any>
  execution_logic: Record<string, any>
  trigger_type: string
}

export interface SkillListResponse {
  items: Skill[]
  total: number
}
