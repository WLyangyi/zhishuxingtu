import { beforeEach, describe, expect, it, vi } from 'vitest'

const { recordView } = vi.hoisted(() => ({ recordView: vi.fn(() => Promise.resolve()) }))
vi.mock('@/api/notes', () => ({ notesApi: { recordView } }))

import { reportNoteView, resetReportedViews } from '../readTracker'

describe('阅读上报', () => {
  beforeEach(() => {
    resetReportedViews()
    recordView.mockClear()
  })

  it('同一篇笔记在同一会话只上报一次', () => {
    reportNoteView('note-1')
    reportNoteView('note-1')
    expect(recordView).toHaveBeenCalledTimes(1)
  })

  it('不同笔记分别上报', () => {
    reportNoteView('note-1')
    reportNoteView('note-2')
    expect(recordView).toHaveBeenCalledTimes(2)
  })

  it('空 id 不上报', () => {
    reportNoteView(null)
    reportNoteView('')
    expect(recordView).not.toHaveBeenCalled()
  })
})
