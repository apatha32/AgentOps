import clsx from 'clsx'
import type { AgentEvent } from '../types'

interface Props {
  events: AgentEvent[]
}

const agentColor: Record<string, string> = {
  triage_agent: 'border-purple-500 bg-purple-500/10',
  research_agent: 'border-blue-500 bg-blue-500/10',
  resolver_agent: 'border-green-500 bg-green-500/10',
}

const eventBadge: Record<string, string> = {
  start: 'bg-white/10 text-white/60',
  tool_call: 'bg-orange-500/20 text-orange-300',
  handoff: 'bg-indigo-500/20 text-indigo-300',
  complete: 'bg-green-500/20 text-green-300',
  error: 'bg-red-500/20 text-red-300',
}

export function AgentTrace({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-white/30 text-sm">
        Select a task to see its live agent trace
      </div>
    )
  }

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full">
      {events.map((e, i) => (
        <div
          key={e.id ?? i}
          className={clsx(
            'rounded-lg border p-3 transition-all',
            agentColor[e.agent_name] ?? 'border-white/10 bg-white/5'
          )}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-semibold text-white/80">{e.agent_name}</span>
            <span
              className={clsx(
                'text-xs px-2 py-0.5 rounded-full',
                eventBadge[e.event_type] ?? 'bg-white/10 text-white/50'
              )}
            >
              {e.event_type}
            </span>
            {e.latency_ms != null && (
              <span className="ml-auto text-xs text-white/30 font-mono">{e.latency_ms.toFixed(0)} ms</span>
            )}
          </div>
          <pre className="text-xs text-white/60 font-mono whitespace-pre-wrap break-all">
            {JSON.stringify(e.payload, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  )
}
