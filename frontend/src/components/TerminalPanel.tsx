// Terminal Panel Component
import { useState, useRef, useEffect, useCallback } from 'react'
import { Terminal as TerminalIcon, X, Square, ChevronDown, Plus } from 'lucide-react'

interface Props {
  onClose: () => void
}

interface TerminalInstance {
  id: string
  name: string
  pid?: number
  process?: any
}

export default function TerminalPanel({ onClose }: Props) {
  const [terminals, setTerminals] = useState<TerminalInstance[]>([])
  const [activeTerminal, setActiveTerminal] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [outputs, setOutputs] = useState<Record<string, Array<{ type: string; data: string }>>>({})
  const [wsConnected, setWsConnected] = useState(false)
  const [wsError, setWsError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const outputRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const nextId = useRef(0)

  // WebSocket connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/v1/terminal/ws`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setWsConnected(true)
      wsError && setWsError(null)
      // Create default terminal
      addTerminal()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string)
        if (data.type === 'output') {
          setOutputs((prev) => {
            const terminalId = activeTerminal || Object.keys(prev)[0]
            if (!terminalId) return prev
            const existing = (prev[terminalId] || [])
            return {
              ...prev,
              [terminalId]: [...existing, data.data],
            }
          })
        } else if (data.type === 'exit') {
          // Process exited
        } else if (data.type === 'error') {
          setOutputs((prev) => {
            const terminalId = activeTerminal || Object.keys(prev)[0]
            if (!terminalId) return prev
            const existing = (prev[terminalId] || [])
            return {
              ...prev,
              [terminalId]: [...existing, { type: 'error', data: `Error: ${data.data.error}` }],
            }
          })
        }
      } catch {
        // Handle raw data
        setOutputs((prev) => {
          const terminalId = activeTerminal || Object.keys(prev)[0]
          if (!terminalId) return prev
          const existing = (prev[terminalId] || [])
          const decoded = typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data)
          return {
            ...prev,
            [terminalId]: [...existing, decoded],
          }
        })
      }
    }

    ws.onerror = () => {
      setWsConnected(false)
      setWsError('Failed to connect to terminal backend')
    }

    ws.onclose = () => {
      setWsConnected(false)
    }

    return () => ws.close()
  }, [activeTerminal])

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
    setHistory((prev) => [command, ...prev])
    setOutputs((prev) => {
      const existing = (prev[activeTerminal!] || [])
      return {
        ...prev,
        [activeTerminal!]: [...existing, { type: 'input', data: `$ ${command}` }],
      }
    })

    wsRef.current.send(JSON.stringify({
      type: 'exec',
      command,
      cwd: '/',
    }))

    setInput('')
  }, [input, activeTerminal])

  const scrollToBottom = useCallback(() => {
    const el = outputRefs.current[activeTerminal || '']
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [activeTerminal])

  useEffect(() => {
    scrollToBottom()
  }, [outputs, activeTerminal, scrollToBottom])

  if (!wsConnected) {
    return (
      <div className="h-48 bg-[#0a0a0e] border-t border-[#2a2a35] flex flex-col items-center justify-center text-[#555565] text-sm">
        <TerminalIcon className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-[#8888a0]">Terminal backend not available</p>
        <p className="text-xs mt-1 text-[#555565]">Ensure the backend server is running</p>
      </div>
    )
  }

  return (
    <div className="h-64 bg-[#0a0a0e] border-t border-[#2a2a35] flex flex-col">
      {/* Tab bar */}
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

      {/* Output area */}
      <div
        ref={(el) => { outputRefs.current[activeTerminal || ''] = el }}
        className="flex-1 overflow-y-auto p-3 font-mono text-sm leading-relaxed"
      >
        {(outputs[activeTerminal || ''] || []).map((line, i) => (
          <div key={i} className={typeof line === 'string' ? 'text-[#8888a0]' : line.type === 'input'
            ? 'text-[#58a6ff]'
            : 'text-[#c8c8d4]'
          }>
            {typeof line === 'string' ? line : line.data}
          </div>
        ))}
        {(!outputs[activeTerminal || ''] || outputs[activeTerminal || '']?.length === 0) && (
          <div className="text-[#555565] text-sm py-4">
            Terminal ready. Commands will execute in the workspace directory.
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleCommand} className="flex-shrink-0 border-t border-[#2a2a35] bg-[#121218]">
        <div className="flex items-center px-3 py-1.5">
          <span className="text-[#58a6ff] mr-2 text-sm font-bold select-none">→</span>
          <input
            ref={inputRef}
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