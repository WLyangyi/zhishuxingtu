import type { Tag } from './tag'

export { type Tag }

export interface Note {
  id: string
  title: string
  content: string | null
  folder_id: string | null
  linked_note_ids: string[]
  tags: Tag[]
  category_id?: string | null
  created_at: string
  updated_at: string
}

export interface NoteCreate {
  title: string
  content?: string
  folder_id?: string | null
  tag_ids?: string[]
}

export interface NoteUpdate {
  title?: string
  content?: string
  folder_id?: string | null
  tag_ids?: string[]
}

export interface Backlink {
  id: string
  title: string
  created_at: string
}
