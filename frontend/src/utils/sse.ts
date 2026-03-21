export interface SSEMessage {
  type: 'content' | 'sources' | 'disclaimer' | 'error' | 'done'
  text?: string
  notes?: Array<{ id: string; title: string }>
  message?: string
}

export interface SSEOptions {
  onMessage: (msg: SSEMessage) => void
  onError?: (error: Error) => void
  onComplete?: () => void
  token?: string
}

export class SSEClient {
  private controller: AbortController | null = null
  private isAborted = false

  async connect(url: string, body: any, options: SSEOptions): Promise<void> {
    this.isAborted = false
    this.controller = new AbortController()

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      
      if (options.token) {
        headers['Authorization'] = `Bearer ${options.token}`
      }

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: this.controller.signal
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (!this.isAborted) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            
            if (data === '[DONE]') {
              options.onMessage({ type: 'done' })
              options.onComplete?.()
              return
            }

            try {
              const msg = JSON.parse(data) as SSEMessage
              options.onMessage(msg)
            } catch (e) {
              console.warn('Failed to parse SSE message:', data)
            }
          }
        }
      }

      options.onComplete?.()
    } catch (error: any) {
      if (error.name === 'AbortError') {
        options.onMessage({ type: 'done' })
        options.onComplete?.()
        return
      }
      options.onError?.(error)
    }
  }

  abort(): void {
    this.isAborted = true
    this.controller?.abort()
  }

  isActive(): boolean {
    return this.controller !== null && !this.isAborted
  }
}

export function createSSEClient(): SSEClient {
  return new SSEClient()
}
