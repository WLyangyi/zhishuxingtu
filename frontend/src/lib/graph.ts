import type { GraphEdge, GraphNode } from '@/types/graph'

export interface Point {
  x: number
  y: number
}

const RING_RATIO: Record<string, number> = {
  folder: 0.34,
  note: 0.66,
  tag: 0.95
}

/** 布局变形缓动（P2-1）：easeOutQuart，设计文档 §4.2 规定的 1000ms 飞行曲线。 */
export function easeOutQuart(t: number): number {
  const x = Math.min(1, Math.max(0, t))
  return 1 - Math.pow(1 - x, 4)
}

/** 径向布局：文件夹在内环，笔记居中，标签在外环。 */
export function radialPositions(
  nodes: GraphNode[],
  width: number,
  height: number
): Map<string, Point> {
  const result = new Map<string, Point>()
  const cx = width / 2
  const cy = height / 2
  const maxRadius = Math.min(width, height) * 0.46

  const groups = new Map<string, GraphNode[]>()
  for (const node of nodes) {
    const list = groups.get(node.type) ?? []
    list.push(node)
    groups.set(node.type, list)
  }

  for (const [type, list] of groups) {
    const ring = maxRadius * (RING_RATIO[type] ?? 0.8)
    const sorted = [...list].sort((a, b) => a.label.localeCompare(b.label, 'zh-CN'))
    sorted.forEach((node, index) => {
      const angle = (index / Math.max(1, sorted.length)) * Math.PI * 2 - Math.PI / 2
      result.set(node.id, {
        x: cx + Math.cos(angle) * ring,
        y: cy + Math.sin(angle) * ring
      })
    })
  }

  return result
}

/** 按类型过滤节点，并丢弃任一端被隐藏的边。 */
export function filterGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  activeTypes: Set<string>
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const kept = nodes.filter((node) => activeTypes.has(node.type))
  const ids = new Set(kept.map((node) => node.id))

  const seen = new Set<string>()
  const keptEdges: GraphEdge[] = []
  for (const edge of edges) {
    if (!ids.has(edge.source) || !ids.has(edge.target)) continue
    const key = `${edge.source}|${edge.target}|${edge.type}`
    if (seen.has(key)) continue
    seen.add(key)
    keptEdges.push(edge)
  }

  return { nodes: kept, edges: keptEdges }
}

export function findNode(nodes: GraphNode[], keyword: string): GraphNode | undefined {
  const query = keyword.trim().toLowerCase()
  if (!query) return undefined
  return (
    nodes.find((node) => node.label.toLowerCase() === query) ??
    nodes.find((node) => node.label.toLowerCase().includes(query))
  )
}

export function graphStats(nodes: GraphNode[], edges: GraphEdge[]) {
  const stats = { note: 0, tag: 0, folder: 0, total: nodes.length, links: edges.length }
  for (const node of nodes) {
    if (node.type === 'note') stats.note += 1
    else if (node.type === 'tag') stats.tag += 1
    else if (node.type === 'folder') stats.folder += 1
  }
  return stats
}

export function nodeDegrees(edges: GraphEdge[]): Map<string, number> {
  const degrees = new Map<string, number>()
  for (const edge of edges) {
    degrees.set(edge.source, (degrees.get(edge.source) ?? 0) + 1)
    degrees.set(edge.target, (degrees.get(edge.target) ?? 0) + 1)
  }
  return degrees
}
