export interface Task {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'done' | 'failed'
  created_at: string
}

export interface AgentEvent {
  id: string
  task_id: string
  agent_name: string
  event_type: 'start' | 'tool_call' | 'handoff' | 'complete' | 'error'
  payload: Record<string, unknown>
  latency_ms: number | null
  created_at: string
}
