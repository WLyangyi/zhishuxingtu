import { describe, expect, it } from 'vitest'
import { easeOutQuart, filterGraph, findNode, graphStats, nodeDegrees, radialPositions } from '../graph'
import type { GraphEdge, GraphNode } from '@/types/graph'

const nodes: GraphNode[] = [
  { id: 'n1', label: 'Agent 三查反思', type: 'note', color: '', size: 18 },
  { id: 'n2', label: '向量检索实验', type: 'note', color: '', size: 18 },
  { id: 'f1', label: '工作', type: 'folder', color: '', size: 20 },
  { id: 't1', label: 'RAG', type: 'tag', color: '', size: 15 }
]

const edges: GraphEdge[] = [
  { source: 'f1', target: 'n1', type: 'contains' },
  { source: 'n1', target: 't1', type: 'has_tag' },
  { source: 'n1', target: 'n2', type: 'links_to' }
]

describe('图谱布局与过滤', () => {
  it('径向布局把文件夹放内环、标签放外环，且位置唯一', () => {
    const positions = radialPositions(nodes, 800, 600)
    const center = { x: 400, y: 300 }

    const distance = (id: string) => {
      const point = positions.get(id)!
      return Math.hypot(point.x - center.x, point.y - center.y)
    }

    expect(positions.size).toBe(4)
    expect(distance('f1')).toBeLessThan(distance('n1'))
    expect(distance('n1')).toBeLessThan(distance('t1'))

    const keys = [...positions.values()].map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`)
    expect(new Set(keys).size).toBe(4)
  })

  it('隐藏标签类型时，相关边一起消失', () => {
    const filtered = filterGraph(nodes, edges, new Set(['note', 'folder']))
    expect(filtered.nodes.map((node) => node.id).sort()).toEqual(['f1', 'n1', 'n2'])
    expect(filtered.edges.map((edge) => edge.type).sort()).toEqual(['contains', 'links_to'])
  })

  it('重复边只保留一条', () => {
    const duplicated = [...edges, { ...edges[2] }]
    expect(filterGraph(nodes, duplicated, new Set(['note', 'folder', 'tag'])).edges).toHaveLength(3)
  })

  it('搜索优先精确匹配，其次包含匹配', () => {
    expect(findNode(nodes, 'rag')?.id).toBe('t1')
    expect(findNode(nodes, '反思')?.id).toBe('n1')
    expect(findNode(nodes, '不存在')).toBeUndefined()
  })

  it('easeOutQuart 端点正确、单调递增、比 cubic 更快逼近终点（P2-1）', () => {
    expect(easeOutQuart(0)).toBe(0)
    expect(easeOutQuart(1)).toBe(1)
    // 单调
    expect(easeOutQuart(0.5)).toBeGreaterThan(easeOutQuart(0.25))
    expect(easeOutQuart(0.75)).toBeGreaterThan(easeOutQuart(0.5))
    // quart 在 t=0.5 时为 1-0.5^4=0.9375，快于 cubic 的 0.875
    expect(easeOutQuart(0.5)).toBeCloseTo(0.9375, 4)
    expect(easeOutQuart(0.5)).toBeGreaterThan(1 - Math.pow(1 - 0.5, 3))
  })

  it('统计与度数按类型汇总', () => {
    expect(graphStats(nodes, edges)).toEqual({
      note: 2,
      tag: 1,
      folder: 1,
      total: 4,
      links: 3
    })

    const degrees = nodeDegrees(edges)
    expect(degrees.get('n1')).toBe(3)
    expect(degrees.get('t1')).toBe(1)
  })
})
