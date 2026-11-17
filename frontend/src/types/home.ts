export interface HomeStats {
  notes: number
  tags: number
  folders: number
  categories: number
  words: number
  links: number
}

export interface HomeRecentNote {
  id: string
  title: string
  excerpt: string
  updated_at: string
  folder_id: string | null
  category_id: string | null
  link_count: number
}

export interface HomeRecentRead {
  note_id: string
  title: string
  excerpt: string
  viewed_at: string
}

export interface HomeTopTag {
  id: string
  name: string
  note_count: number
}

export interface HomeArea {
  id: string
  name: string
  note_count: number
}

export interface HomeOverview {
  stats: HomeStats
  recent_notes: HomeRecentNote[]
  recent_reads: HomeRecentRead[]
  top_tags: HomeTopTag[]
  areas: HomeArea[]
}
