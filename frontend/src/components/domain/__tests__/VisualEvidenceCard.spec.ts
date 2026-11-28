import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import VisualEvidenceCard from '../VisualEvidenceCard.vue'
import type { VisualEvidence } from '@/api/agent'

const evidence: VisualEvidence = {
  asset_id: 'asset-1',
  note_id: 'n1',
  page_number: 2,
  source_filename: 'visual.pdf',
  description: '第二页图表描述',
  description_status: 'completed',
  image_url: '/api/import/notes/n1/assets/asset-1/image'
}

describe('VisualEvidenceCard', () => {
  it('展示页码、来源和视觉描述', () => {
    const wrapper = mount(VisualEvidenceCard, { props: { evidence } })

    expect(wrapper.text()).toContain('第 2 页')
    expect(wrapper.text()).toContain('visual.pdf')
    expect(wrapper.text()).toContain('第二页图表描述')
  })

  it('点击查看原图发出事件', async () => {
    const wrapper = mount(VisualEvidenceCard, { props: { evidence } })

    await wrapper.get('button').trigger('click')

    expect(wrapper.emitted('view')?.[0]?.[0]).toEqual(evidence)
  })

  it('描述失败时显示不可用', () => {
    const wrapper = mount(VisualEvidenceCard, {
      props: { evidence: { ...evidence, description: '', description_status: 'failed' } }
    })

    expect(wrapper.text()).toContain('视觉描述不可用')
  })
})
