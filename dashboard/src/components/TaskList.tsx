import clsx from 'clsx'
import type { Task } from '../types'

interface Props {
  tasks: Task[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNewTask: () => void
}

const statusColor: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
  running: 'bg-blue-500/20 text-blue-300 border-blue-500/40 animate-pulse',
  done: 'bg-green-500/20 text-green-300 border-green-500/40',
  failed: 'bg-red-500/20 text-red-300 border-red-500/40',
}

export function TaskList({ tasks, selectedId, onSelect, onNewTask }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Tasks</h2>
        <button
          onClick={onNewTask}
          className="text-xs px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          + New
        </button>
      </div>
      <div className="flex-1 overflow-y-auto divide-y divide-white/5">
        {tasks.length === 0 && (
          <p className="text-white/30 text-sm text-center mt-8">No tasks yet</p>
        )}
        {tasks.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.id)}
            className={clsx(
              'w-full text-left px-4 py-3 hover:bg-white/5 transition-colors',
              selectedId === t.id && 'bg-white/8 border-l-2 border-indigo-400'
            )}
          >
            <p className="text-sm text-white truncate">{t.title}</p>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={clsx(
                  'text-xs px-2 py-0.5 rounded-full border',
                  statusColor[t.status] ?? 'text-white/50'
                )}
              >
                {t.status}
              </span>
              <span className="text-xs text-white/30">
                {new Date(t.created_at).toLocaleTimeString()}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
