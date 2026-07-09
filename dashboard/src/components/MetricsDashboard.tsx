import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import type { AgentEvent } from '../types'

interface Props {
  events: AgentEvent[]
}

const AGENT_COLORS: Record<string, string> = {
  triage_agent: '#a855f7',
  research_agent: '#3b82f6',
  resolver_agent: '#22c55e',
}

export function MetricsDashboard({ events }: Props) {
  // Aggregate per-agent latency
  const latencyMap: Record<string, number[]> = {}
  for (const e of events) {
    if (e.latency_ms != null) {
      if (!latencyMap[e.agent_name]) latencyMap[e.agent_name] = []
      latencyMap[e.agent_name].push(e.latency_ms)
    }
  }

  const chartData = Object.entries(latencyMap).map(([agent, lats]) => ({
    agent,
    avg: Math.round(lats.reduce((a, b) => a + b, 0) / lats.length),
    p99: Math.round([...lats].sort((a, b) => a - b)[Math.floor(lats.length * 0.99)] ?? 0),
  }))

  const toolCalls = events.filter((e) => e.event_type === 'tool_call').length
  const errors = events.filter((e) => e.event_type === 'error').length
  const steps = events.length

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Total Steps" value={steps} />
        <Stat label="Tool Calls" value={toolCalls} color="text-orange-300" />
        <Stat label="Errors" value={errors} color={errors > 0 ? 'text-red-400' : 'text-white/60'} />
      </div>

      {chartData.length > 0 && (
        <div>
          <p className="text-xs text-white/40 mb-2 uppercase tracking-wider">Avg Latency (ms)</p>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <XAxis dataKey="agent" tick={{ fill: '#ffffff50', fontSize: 10 }} />
              <YAxis tick={{ fill: '#ffffff50', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #ffffff20', borderRadius: 6 }}
                labelStyle={{ color: '#ffffffb0' }}
                itemStyle={{ color: '#ffffff80' }}
              />
              <Bar dataKey="avg" radius={[4, 4, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.agent} fill={AGENT_COLORS[entry.agent] ?? '#6366f1'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color = 'text-white/80' }: { label: string; value: number; color?: string }) {
  return (
    <div className="rounded-lg bg-white/5 border border-white/10 p-3 text-center">
      <p className={`text-2xl font-bold font-mono ${color}`}>{value}</p>
      <p className="text-xs text-white/30 mt-1">{label}</p>
    </div>
  )
}
