export interface SourceInfo {
  type: 'pdf' | 'web' | 'video' | 'video_url'
  url?: string
  filename?: string
  duration?: number
  platform?: string
  imported_at?: string
}

export interface ImportResult {
  title: string
  summary: string
  key_points: string[]
  tags: string[]
  source_info?: SourceInfo
}

export interface ImportTask {
  task_id: string
  source_type: 'pdf' | 'url' | 'video' | 'video_url'
  status: 'pending' | 'parsing' | 'extracting' | 'analyzing' | 'summarizing' | 'completed' | 'failed'
  progress: number
  progress_message: string
  result: ImportResult | null
  extracted_content?: string | null
  error?: string | null
  created_at: string
  updated_at: string
}

export interface ImportHistoryItem {
  id: string
  task_id: string
  source_type: string
  source_url?: string
  source_filename?: string
  duration?: number
  platform?: string
  generated_title?: string
  note_id?: string
  status: string
  created_at?: string
}

export interface ImportSaveRequest {
  task_id: string
  title?: string
  summary?: string
  key_points?: string[]
  tags?: string[]
  folder_id?: string | null
}

export interface SSEProgressMessage {
  type: 'progress' | 'completed' | 'error'
  progress?: number
  message?: string
  result?: ImportResult
  code?: string
}
