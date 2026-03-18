export interface GraphNode {
  id: string
  label: string
  type: 'note' | 'folder' | 'tag'
  color: string
  size: number
}

export interface GraphEdge {
  source: string
  target: string
  type: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
