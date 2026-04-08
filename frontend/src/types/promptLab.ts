export interface FewShotExample {
  id: string
  prompt_id: string | null
  scenario: string
  input_example: string
  output_example: string
  quality_score: number
  is_active: boolean
  created_at: string
}

export interface FewShotExampleCreate {
  prompt_id?: string
  scenario: string
  input_example: string
  output_example: string
  quality_score?: number
}

export interface FewShotExampleUpdate {
  input_example?: string
  output_example?: string
  quality_score?: number
  is_active?: boolean
}

export interface PromptVersion {
  id: string
  prompt_id: string
  version_number: string
  version_name: string | null
  system_prompt: string
  user_prompt_template: string | null
  changes_description: string | null
  is_active: boolean
  created_at: string
}

export interface PromptVersionCreate {
  prompt_id: string
  version_number: string
  version_name?: string
  system_prompt: string
  user_prompt_template?: string
  changes_description?: string
}

export interface ABExperiment {
  id: string
  name: string
  description: string | null
  prompt_id: string
  version_a_id: string
  version_b_id: string
  traffic_split: number
  status: string
  start_time: string | null
  end_time: string | null
  created_at: string
}

export interface ABExperimentCreate {
  name: string
  description?: string
  prompt_id: string
  version_a_id: string
  version_b_id: string
  traffic_split?: number
}

export interface ABExperimentStats {
  experiment_id: string
  experiment_name: string | null
  version_a_id: string
  version_b_id: string
  total_samples: number
  version_a_samples: number
  version_b_samples: number
  version_a_avg_feedback: number | null
  version_b_avg_feedback: number | null
  version_a_avg_response_time: number | null
  version_b_avg_response_time: number | null
}

export interface ABTestResult {
  id: string
  experiment_id: string
  version_id: string
  session_id: string | null
  user_question: string
  ai_response: string
  response_time_ms: number | null
  token_count: number | null
  user_feedback: number | null
  created_at: string
}

export interface ABTestResultCreate {
  experiment_id: string
  version_id: string
  session_id?: string
  user_question: string
  ai_response: string
  response_time_ms?: number
  token_count?: number
  user_feedback?: number
}

export interface CoTTemplate {
  type: string
  name: string
  description: string
}

export interface ChainStep {
  id: string
  chain_id: string
  step_order: number
  step_name: string
  prompt_template: string
  input_mapping: string | null
  output_mapping: string | null
  created_at: string
}

export interface ChainStepCreate {
  step_order: number
  step_name: string
  prompt_template: string
  input_mapping?: string
  output_mapping?: string
}

export interface PromptChain {
  id: string
  name: string
  description: string | null
  is_active: boolean
  created_at: string
  steps?: ChainStep[]
}

export interface PromptChainCreate {
  name: string
  description?: string
  steps?: ChainStepCreate[]
}

export interface PromptChainUpdate {
  name?: string
  description?: string
  is_active?: boolean
}

export interface ChainExecution {
  id: string
  chain_id: string
  session_id: string | null
  input_data: string | null
  output_data: string | null
  status: string
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface ChainExecutionResult {
  success: boolean
  output?: string
  execution_id: string
  error?: string
}

export interface PromptEvaluationStats {
  total_evaluations: number
  avg_overall_score: number | null
  avg_relevance_score: number | null
  avg_accuracy_score: number | null
  avg_completeness_score: number | null
  avg_clarity_score: number | null
  score_distribution: {
    excellent: number
    good: number
    average: number
    poor: number
  }
}

export const COT_TEMPLATES: CoTTemplate[] = [
  {
    type: 'step_by_step',
    name: '分步推理',
    description: '适用于复杂问题分析，按步骤逐步推理'
  },
  {
    type: 'compare_analyze',
    name: '对比分析',
    description: '适用于对比类问题，识别维度并综合评估'
  },
  {
    type: 'deep_reasoning',
    name: '深度推理',
    description: '适用于需要深度思考的问题，问题分解并验证假设'
  }
]

export const SCENARIOS = [
  { value: 'conversation_summary', label: '对话总结' },
  { value: 'knowledge_extraction', label: '知识提取' },
  { value: 'knowledge_qa', label: '知识库问答' }
]
