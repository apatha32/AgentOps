const BASE = '/api'

export async function fetchTasks() {
  const res = await fetch(`${BASE}/tasks/`)
  if (!res.ok) throw new Error(`fetchTasks: ${res.status}`)
  return res.json()
}

export async function createTask(body: { title: string; description: string; service: string }) {
  const res = await fetch(`${BASE}/tasks/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`createTask: ${res.status}`)
  return res.json()
}

export async function fetchTrace(taskId: string) {
  const res = await fetch(`${BASE}/traces/${taskId}`)
  if (!res.ok) throw new Error(`fetchTrace: ${res.status}`)
  return res.json()
}

export function openTraceStream(taskId: string, onEvent: (e: unknown) => void): () => void {
  const es = new EventSource(`${BASE}/traces/${taskId}/stream`)
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data))
    } catch {
      // ignore malformed
    }
  }
  return () => es.close()
}
