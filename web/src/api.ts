// 和 server.py 的接口对应的类型与请求函数

export interface Usage {
  calls: number
  prompt_tokens: number
  cache_hit_tokens: number
  completion_tokens: number
  reasoning_tokens: number
  cost_usd: number
}

export interface ToolCall {
  name: string
  arguments: string
  result: unknown
}

export interface StaffRequest {
  ticket: string
  reason: string
  language: string
  time: string
}

export interface ChatResponse {
  answer: string
  trace: ToolCall[]
  usage: Usage
  total: Usage
  staff_requests: StaffRequest[]
  model: string
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`${res.status} ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

export async function createSession(): Promise<string> {
  const { session_id } = await post<{ session_id: string }>('/api/session')
  return session_id
}

export function sendMessage(sessionId: string, message: string, thinking: boolean): Promise<ChatResponse> {
  return post<ChatResponse>('/api/chat', { session_id: sessionId, message, thinking })
}
