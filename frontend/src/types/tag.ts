export interface Tag {
  id: string
  name: string
  color: string
  note_count: number
  created_at: string
}

export interface TagCreate {
  name: string
  color?: string
}

export interface TagUpdate {
  name?: string
  color?: string
}
