export interface Folder {
  id: string
  name: string
  parent_id: string | null
  level: number
  category_id?: string | null
  note_count: number
  created_at: string
}

export interface FolderTree extends Folder {
  children: FolderTree[]
}

export interface FolderCreate {
  name: string
  parent_id?: string
  category_id?: string
}

export interface FolderUpdate {
  name?: string
  category_id?: string
}
