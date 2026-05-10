// Command Palette Component
import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, Terminal, Bot, Plus, FileText, Settings, RefreshCw } from 'lucide-react'

interface Props {
  isOpen: boolean
  onClose: () => void
  onOpenTerminal: () => void
}

interface Command {
  key: string
  title: string
  description: string
  icon: React.ElementType
  action: () => void
  category?: string
}

export default function CommandPalette({ isOpen, onClose, onOpenTerminal }: Props) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        onClose()
      }
      if (e.key === 'Escape') {
        onClose()
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const getCommands = (): Command[] => {
    const all: Command[] = [
      {
        key: 'new-file',
        title: 'New File',
        description: 'Create a new file',
        icon: Plus,
        action: () => {
          const path = prompt('File path:')
          if (path) {
            fetch('/api/v1/files/write', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ path, content: '' }),
            }).then(() => window.location.reload())
          }
        },
      },
      {
        key: 'terminal',
        title: 'Open Terminal',
        description: 'Open a new terminal session',
        icon: Terminal,
        action: onOpenTerminal,
      },
      {
        key: 'ai-chat',
        title: 'Open AI Chat',
        description: 'Open the AI chat panel',
        icon: Bot,
        action: () => {
          // Dispatch custom event to toggle AI panel
          window.dispatchEvent(new CustomEvent('toggle-ai-panel'))
        },
      },
      {
        key: 'refresh',
        title: 'Refresh Explorer',
        description: 'Reload the file explorer',
        icon: RefreshCw,
        action: () => window.location.reload(),
      },
      {
        key: 'settings',
        title: 'Settings',
        description: 'Open settings',
        icon: Settings,
        action: () => {
          const path = prompt('Enter setting key=value:')
          if (path) {
            console.log('Setting:', path)
          }
        },
      },
    ]

    if (!query) return all

    return all.filter(
      (c) =>
        c.title.toLowerCase().includes(query.toLowerCase()) ||
        c.description.toLowerCase().includes(query.toLowerCase())
    )
  }

  const commands = getCommands()

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected((s) => Math.min(s + 1, commands.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (commands[selected]) commands[selected].action()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-start justify-center pt-[20vh]" onClick={onClose}>
      <div
        className="bg-[#18181e] border border-[#3a3a45] rounded-lg w-[560px] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 px-3 py-3 border-b border-[#2a2a35]">
          <Search className="w-4 h-4 text-[#686880]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent outline-none text-sm text-[#c8c8d4] placeholder-[#555565]"
          />
          <kbd className="px-1.5 py-0.5 text-[10px] bg-[#2a2a35] rounded text-[#686880]">Esc</kbd>
        </div>
        <div className="max-h-[320px] overflow-y-auto">
          {commands.map((cmd, idx) => {
            const Icon = cmd.icon
            return (
              <button
                key={cmd.key}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-[#264f78] transition-colors ${idx === selected ? 'bg-[#264f78]' : ''}`}
                onClick={() => cmd.action()}
              >
                <Icon className="w-4 h-4 text-[#686880] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-[#c8c8d4]">{cmd.title}</div>
                  <div className="text-xs text-[#686880] truncate">{cmd.description}</div>
                </div>
              </button>
            )
          })}
          {commands.length === 0 && (
            <div className="px-3 py-8 text-center text-[#555565] text-sm">
              No matching commands found
            </div>
          )}
        </div>
      </div>
    </div>
  )
}