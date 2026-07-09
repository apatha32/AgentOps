import { useState } from 'react'
import { createTask } from '../api'

interface Props {
  onCreated: () => void
  onClose: () => void
}

export function NewTaskModal({ onCreated, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [service, setService] = useState('api')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await createTask({ title, description, service })
      onCreated()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#1e1e2e] border border-white/10 rounded-xl w-full max-w-md p-6 shadow-2xl">
        <h2 className="text-white font-semibold text-lg mb-4">New Task</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-white/50 mb-1 block">Title *</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. High CPU on api-server-01"
              required
              minLength={3}
            />
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1 block">Description</label>
            <textarea
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the incident or task..."
            />
          </div>
          <div>
            <label className="text-xs text-white/50 mb-1 block">Service</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
              value={service}
              onChange={(e) => setService(e.target.value)}
              placeholder="api"
            />
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg border border-white/10 text-white/60 text-sm hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm transition-colors disabled:opacity-50"
            >
              {loading ? 'Submitting…' : 'Submit Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
