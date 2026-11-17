import { notesApi } from '@/api/notes'

const reported = new Set<string>()

/**
 * 阅读上报：同一会话同一篇笔记只报一次；失败静默，不阻塞阅读。
 */
export function reportNoteView(noteId: string | null | undefined) {
  if (!noteId || reported.has(noteId)) return
  reported.add(noteId)
  void notesApi.recordView(noteId).catch(() => {
    // 阅读记录是增强能力，失败不打扰用户
  })
}

export function resetReportedViews() {
  reported.clear()
}
