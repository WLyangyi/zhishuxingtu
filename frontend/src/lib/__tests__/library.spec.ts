import { describe, expect, it } from 'vitest'
import {
  countNotesForCategory,
  countNotesForFolder,
  descendantFolderIds,
  filterLibraryNotes,
  flattenFolders,
  folderPath,
  tagCounts
} from '../library'
import type { FolderTree } from '@/types/folder'
import type { Note } from '@/types/note'

const folders: FolderTree[] = [
  {
    id: 'f-work',
    name: '工作',
    parent_id: null,
    level: 0,
    category_id: 'c-work',
    note_count: 2,
    created_at: '',
    children: [
      {
        id: 'f-ai',
        name: 'AI',
        parent_id: 'f-work',
        level: 1,
        category_id: 'c-work',
        note_count: 1,
        created_at: '',
        children: [
          {
            id: 'f-rag',
            name: 'RAG',
            parent_id: 'f-ai',
            level: 2,
            category_id: 'c-work',
            note_count: 1,
            created_at: '',
            children: []
          }
        ]
      }
    ]
  },
  {
    id: 'f-personal',
    name: '日记',
    parent_id: null,
    level: 0,
    category_id: 'c-personal',
    note_count: 1,
    created_at: '',
    children: []
  }
]

function note(id: string, title: string, folderId: string | null, content = '', tags: string[] = []): Note {
  return {
    id,
    title,
    content,
    folder_id: folderId,
    linked_note_ids: [],
    tags: tags.map((name) => ({ id: `t-${name}`, name, color: '', note_count: 0, created_at: '' })),
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z'
  }
}

const notes: Note[] = [
  note('n1', 'Agent 三查反思', 'f-ai', 'ReAct 与反思', ['RAG', 'Agent']),
  note('n2', '向量检索实验', 'f-rag', '混合检索', ['RAG']),
  note('n3', '周记', 'f-personal', '本周复盘', ['日记']),
  note('n4', '无目录笔记', null, '散落的想法', ['RAG'])
]

const flat = flattenFolders(folders)

describe('笔记库过滤与统计', () => {
  it('递归扁平化文件夹树', () => {
    expect(flat.map((folder) => folder.id)).toEqual([
      'f-work',
      'f-ai',
      'f-rag',
      'f-personal'
    ])
  })

  it('选文件夹时包含所有后代文件夹的笔记', () => {
    const ids = descendantFolderIds('f-ai', flat)
    expect([...ids].sort()).toEqual(['f-ai', 'f-rag'])

    const result = filterLibraryNotes(notes, {
      categoryId: null,
      folderId: 'f-ai',
      tagId: null,
      keyword: ''
    }, flat)
    expect(result.map((item) => item.id).sort()).toEqual(['n1', 'n2'])
  })

  it('选分区时包含分区下所有文件夹的笔记，不含无目录笔记', () => {
    const result = filterLibraryNotes(notes, {
      categoryId: 'c-work',
      folderId: null,
      tagId: null,
      keyword: ''
    }, flat)
    expect(result.map((item) => item.id).sort()).toEqual(['n1', 'n2'])
  })

  it('标签与关键词可叠加', () => {
    const byTag = filterLibraryNotes(notes, {
      categoryId: null,
      folderId: null,
      tagId: 't-RAG',
      keyword: ''
    }, flat)
    expect(byTag.map((item) => item.id).sort()).toEqual(['n1', 'n2', 'n4'])

    const byKeyword = filterLibraryNotes(notes, {
      categoryId: null,
      folderId: null,
      tagId: null,
      keyword: '反思'
    }, flat)
    expect(byKeyword.map((item) => item.id)).toEqual(['n1'])
  })

  it('分区与文件夹计数包含后代', () => {
    expect(countNotesForCategory(notes, 'c-work', flat)).toBe(2)
    expect(countNotesForFolder(notes, 'f-work', flat)).toBe(2)
    expect(countNotesForFolder(notes, 'f-rag', flat)).toBe(1)
  })

  it('标签计数按使用次数倒序', () => {
    const counts = tagCounts(notes)
    expect(counts[0]).toMatchObject({ id: 't-RAG', name: 'RAG', count: 3 })
    expect(counts.map((item) => item.name)).toEqual(['RAG', 'Agent', '日记'])
  })

  it('文件夹路径从根到当前', () => {
    expect(folderPath(flat, 'f-rag').map((folder) => folder.name)).toEqual(['工作', 'AI', 'RAG'])
  })
})
