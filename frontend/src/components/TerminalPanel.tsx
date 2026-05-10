// Terminal Panel Component
import { useState, useRef, useEffect, useCallback } from 'react'
import { Terminal as TerminalIcon, X, Square, Plus } from 'lucide-react'

interface Props {}

interface TerminalInstance {
  id: string
  name: string
}

export default function TerminalPanel() {
  const [terminals, setTerminals] = useState<TerminalInstance[]>([])
  const [activeTerminal, setActiveTerminal] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [outputs, setOutputs] = useState<Record<string, string[]>>({})
  const nextId = useRef(0)

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/v1/terminal/ws`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      const id = `terminal-${nextId.current++}`
      setTerminals([{ id, name: 'Terminal 1' }])
      setActiveTerminal(id)
      setOutputs((prev) => ({ ...prev, [id]: [] }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string)
        if (data.type === 'output' || data.type === 'exit' || data.type === 'error') {
          setOutputs((prev) => {
            const terminalId = activeTerminal || Object.keys(prev)[0]
            if (!terminalId) return prev
            const existing = (prev[terminalId] || []) as string[]
            const text = typeof data === 'object' && data.data ? (data.data.text || data.data || '') : event.data as string
            return { ...prev, [terminalId]: [...existing, text] }
          })
        }
      } catch {
        setOutputs((prev) => {
          const terminalId = activeTerminal || Object.keys(prev)[0]
          if (!terminalId) return prev
          const existing = (prev[terminalId] || []) as string[]
          const decoded = typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data as Blob as any)
          return { ...prev, [terminalId]: [...existing, decoded] }
        })
      }
    }

    ws.onerror = () => {
      setOutputs((prev) => {
        const terminalId = activeTerminal || 'default'
        const existing = (prev[terminalId] || []) as string[]
        return { ...prev, [terminalId]: [...existing, 'Terminal backend not available'] }
      })
    }

    return () => ws.close()
  }, [])

  const addTerminal = useCallback(() => {
    const id = `terminal-${nextId.current++}`
    setTerminals((prev) => [...prev, { id, name: `Terminal ${nextId.current}` }])
    setActiveTerminal(id)
    setOutputs((prev) => ({ ...prev, [id]: [] }))
  }, [])

  const removeTerminal = useCallback((id: string) => {
    setTerminals((prev) => prev.filter((t) => t.id !== id))
    setOutputs((prev) => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    if (activeTerminal === id) {
      const remaining = terminals.filter((t) => t.id !== id)
      setActiveTerminal(remaining[0]?.id || null)
    }
  }, [activeTerminal, terminals])

  const handleCommand = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    const command = input.trim()
    setOutputs((prev) => {
      const existing = (prev[activeTerminal!] || []) as string[]
      return { ...prev, [activeTerminal!]: [...existing, `$ ${command}`] }
    })

    wsRef.current.send(JSON.stringify({ type: 'exec', command, cwd: '/workspace' }))
    setInput('')
  }, [input, activeTerminal])

  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [outputs, activeTerminal])

  return (
    <div className="h-64 bg-[#0a0a0e] border-t border-[#2a2a35] flex flex-col">
      <div className="flex items-center bg-[#121218] border-b border-[#2a2a35] overflow-x-auto h-7 flex-shrink-0">
        {terminals.map((term) => (
          <button
            key={term.id}
            className={`flex items-center gap-1.5 px-3 text-xs hover:bg-[#2a2a35] transition-colors ${activeTerminal === term.id
              ? 'bg-[#0a0a0e] text-[#c8c8d4]'
              : 'text-[#686880]'
              }`}
            onClick={() => setActiveTerminal(term.id)}
          >
            <TerminalIcon className="w-3 h-3" />
            <span>{term.name}</span>
            <button
              className="hover:text-[#ff7b72] ml-1"
              onClick={(e) => {
                e.stopPropagation()
                removeTerminal(term.id)
              }}
            >
              <X className="w-3 h-3" />
            </button>
          </button>
        ))}
        <button
          className="text-[#686880] hover:text-[#c8c8d4] px-2 transition-colors"
          onClick={addTerminal}
          title="New terminal"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-3 font-mono text-sm leading-relaxed"
      >
        {(outputs[activeTerminal || ''] || []).map((line, i) => (
          <div key={i} className="text-[#8888a0]">{line}</div>
        ))}
        {(!outputs[activeTerminal || ''] || outputs[activeTerminal || '']?.length === 0) && (
          <div className="text-[#555565] text-sm py-4">
            Terminal ready. Commands will execute in the workspace directory.
          </div>
        )}
      </div>

      <form onSubmit={handleCommand} className="flex-shrink-0 border-t border-[#2a2a35] bg-[#121218]">
        <div className="flex items-center px-3 py-1.5">
          <span className="text-[#58a6ff] mr-2 text-sm font-bold select-none">→</span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a command..."
            className="flex-1 bg-transparent outline-none text-sm text-[#c8c8d4] placeholder-[#555565]"
          />
          <button
            type="submit"
            className="text-[#8888a0] hover:text-[#c8c8d4] px-2 transition-colors text-xs"
          >
            Run
          </button>
          <button
            type="button"
            onClick={() => wsRef.current?.send(JSON.stringify({ type: 'kill' }))}
            className="text-[#686880] hover:text-[#ff7b72] px-2 transition-colors"
            title="Kill process"
          >
            <Square className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </div>
  )
}