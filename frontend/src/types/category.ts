export interface ContentType {
  id: string
  name: string
  icon: string
  color: string
  field_schema: Record<string, any>
}

export interface Category {
  id: string
  name: string
  icon: string
  color: string
  sort_order: number
  is_system: boolean
  created_at: string
  content_types: ContentType[]
}

export interface CategoryCreate {
  name: string
  icon?: string
  color?: string
  sort_order?: number
}

export interface CategoryUpdate {
  name?: string
  icon?: string
  color?: string
  sort_order?: number
}

export interface ContentTypeCreate {
  name: string
  category_id: string
  icon?: string
  color?: string
  field_schema?: Record<string, any>
}

export interface ContentTypeUpdate {
  name?: string
  icon?: string
  color?: string
  field_schema?: Record<string, any>
}

export interface ContentTag {
  id: string
  name: string
  color: string
}

export interface Content {
  id: string
  type_id: string
  category_id: string
  user_id: string
  title: string
  content: string | null
  extra_fields: Record<string, any>
  linked_content_ids: string[]
  file_path: string | null
  file_url: string | null
  file_size: number
  created_at: string
  updated_at: string
  content_type: ContentType | null
  category: Category | null
  tags: ContentTag[]
}

export interface ContentCreate {
  title: string
  content?: string
  type_id: string
  category_id: string
  extra_fields?: Record<string, any>
  tag_ids?: string[]
}

export interface ContentUpdate {
  title?: string
  content?: string
  type_id?: string
  category_id?: string
  extra_fields?: Record<string, any>
  tag_ids?: string[]
  file_path?: string
  file_url?: string
  file_size?: number
}

export interface ContentListResponse {
  items: Content[]
  total: number
  page: number
  page_size: number
}
