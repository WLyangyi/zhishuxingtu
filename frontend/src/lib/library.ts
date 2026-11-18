import type { FolderTree } from '@/types/folder'
import type { Note } from '@/types/note'

export interface LibrarySelection {
  categoryId: string | null
  folderId: string | null
  tagId: string | null
  keyword: string
}

export interface TagCount {
  id: string
  name: string
  color: string
  count: number
}

/** 深度优先扁平化文件夹树。 */
export function flattenFolders(tree: FolderTree[]): FolderTree[] {
  const result: FolderTree[] = []
  const walk = (nodes: FolderTree[]) => {
    for (const node of nodes) {
      result.push(node)
      if (node.children?.length) walk(node.children)
    }
  }
  walk(tree)
  return result
}

/** 选中文件夹时，其自身与所有后代文件夹的 id。 */
export function descendantFolderIds(folderId: string, flat: FolderTree[]): Set<string> {
  const ids = new Set<string>([folderId])
  const queue = [folderId]

  while (queue.length) {
    const parent = queue.shift()!
    for (const folder of flat) {
      if (folder.parent_id === parent && !ids.has(folder.id)) {
        ids.add(folder.id)
        queue.push(folder.id)
      }
    }
  }

  return ids
}

export function folderIdsForCategory(categoryId: string, flat: FolderTree[]): Set<string> {
  return new Set(flat.filter((folder) => folder.category_id === categoryId).map((folder) => folder.id))
}

export function filterLibraryNotes(
  notes: Note[],
  selection: LibrarySelection,
  flat: FolderTree[]
): Note[] {
  let scoped = notes

  if (selection.folderId) {
    const ids = descendantFolderIds(selection.folderId, flat)
    scoped = scoped.filter((note) => note.folder_id && ids.has(note.folder_id))
  } else if (selection.categoryId) {
    const ids = folderIdsForCategory(selection.categoryId, flat)
    scoped = scoped.filter((note) => note.folder_id && ids.has(note.folder_id))
  }

  if (selection.tagId) {
    scoped = scoped.filter((note) => note.tags.some((tag) => tag.id === selection.tagId))
  }

  const keyword = selection.keyword.trim().toLowerCase()
  if (keyword) {
    scoped = scoped.filter(
      (note) =>
        note.title.toLowerCase().includes(keyword) ||
        (note.content ?? '').toLowerCase().includes(keyword)
    )
  }

  return [...scoped].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )
}

export function countNotesForCategory(notes: Note[], categoryId: string, flat: FolderTree[]): number {
  const ids = folderIdsForCategory(categoryId, flat)
  return notes.filter((note) => note.folder_id && ids.has(note.folder_id)).length
}

export function countNotesForFolder(notes: Note[], folderId: string, flat: FolderTree[]): number {
  const ids = descendantFolderIds(folderId, flat)
  return notes.filter((note) => note.folder_id && ids.has(note.folder_id)).length
}

export function tagCounts(notes: Note[]): TagCount[] {
  const counts = new Map<string, TagCount>()
  for (const note of notes) {
    for (const tag of note.tags) {
      const entry = counts.get(tag.id)
      if (entry) entry.count += 1
      else counts.set(tag.id, { id: tag.id, name: tag.name, color: tag.color, count: 1 })
    }
  }
  return [...counts.values()].sort(
    (a, b) => b.count - a.count || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0)
  )
}

export function folderPath(flat: FolderTree[], folderId: string): FolderTree[] {
  const byId = new Map(flat.map((folder) => [folder.id, folder]))
  const path: FolderTree[] = []
  let current = byId.get(folderId)
  let guard = 0

  while (current && guard < 10) {
    path.unshift(current)
    current = current.parent_id ? byId.get(current.parent_id) : undefined
    guard += 1
  }

  return path
}
