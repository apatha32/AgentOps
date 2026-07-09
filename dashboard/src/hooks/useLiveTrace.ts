import { useEffect, useRef, useState } from 'react'
import { openTraceStream } from '../api'
import type { AgentEvent } from '../types'

export function useLiveTrace(taskId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const closerRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!taskId) return
    setEvents([])
    closerRef.current?.()

    closerRef.current = openTraceStream(taskId, (raw) => {
      setEvents((prev) => [...prev, raw as AgentEvent])
    })

    return () => {
      closerRef.current?.()
    }
  }, [taskId])

  return events
}
