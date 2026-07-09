import { useEffect, useState } from 'react'
import { fetchTasks, fetchTrace } from './api'
import { AgentTrace } from './components/AgentTrace'
import { MetricsDashboard } from './components/MetricsDashboard'
import { NewTaskModal } from './components/NewTaskModal'
import { TaskList } from './components/TaskList'
import { useLiveTrace } from './hooks/useLiveTrace'
import type { AgentEvent, Task } from './types'

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [historicEvents, setHistoricEvents] = useState<AgentEvent[]>([])
  const [showModal, setShowModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'trace' | 'metrics'>('trace')

  const liveEvents = useLiveTrace(selectedId)

  // Merge historic + live events (deduplicated by id)
  const allEvents = [
    ...historicEvents,
    ...liveEvents.filter((le) => !historicEvents.some((he) => he.id === le.id)),
  ]

  async function loadTasks() {
    try {
      const data = await fetchTasks()
      setTasks(data)
    } catch {
      // ignore
    }
  }

  async function handleSelect(id: string) {
    setSelectedId(id)
    setHistoricEvents([])
    try {
      const events = await fetchTrace(id)
      setHistoricEvents(events)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadTasks()
    const interval = setInterval(loadTasks, 5000)
    return () => clearInterval(interval)
  }, [])

  const selectedTask = tasks.find((t) => t.id === selectedId)

  return (
    <div className="h-screen bg-[#13131f] text-white flex flex-col font-mono overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-3 border-b border-white/10 shrink-0">
        <div className="w-3 h-3 rounded-full bg-indigo-500 shadow-lg shadow-indigo-500/50" />
        <h1 className="text-sm font-semibold tracking-wide text-white/90">AgentOps</h1>
        <span className="text-xs text-white/30 ml-1">— Live Observability</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-white/40">live</span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar: task list */}
        <aside className="w-72 border-r border-white/10 shrink-0 overflow-hidden flex flex-col">
          <TaskList
            tasks={tasks}
            selectedId={selectedId}
            onSelect={handleSelect}
            onNewTask={() => setShowModal(true)}
          />
        </aside>

        {/* Main content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Task header */}
          {selectedTask && (
            <div className="px-6 py-3 border-b border-white/10 shrink-0">
              <p className="text-sm text-white font-semibold truncate">{selectedTask.title}</p>
              <p className="text-xs text-white/40 mt-0.5">{selectedTask.id}</p>
            </div>
          )}

          {/* Tabs */}
          <div className="flex border-b border-white/10 shrink-0">
            {(['trace', 'metrics'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-2 text-xs uppercase tracking-wider transition-colors ${
                  activeTab === tab
                    ? 'text-indigo-400 border-b-2 border-indigo-400'
                    : 'text-white/30 hover:text-white/60'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'trace' ? (
              <AgentTrace events={allEvents} />
            ) : (
              <MetricsDashboard events={allEvents} />
            )}
          </div>
        </main>
      </div>

      {showModal && (
        <NewTaskModal
          onCreated={() => {
            setShowModal(false)
            loadTasks()
          }}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
