// Status Bar Component
import { GitBranch, Terminal, Bot, CheckCircle, AlertCircle, Wifi, WifiOff, ChevronUp } from 'lucide-react'
import { useStore } from '../stores/useStore'

interface Props {
  connected: boolean
  workspace: { root: string; files: any[] } | null
  gitStatus: { branch: string | null; ahead: number; behind: number; files: { path: string; status: string }[] } | null
  onOpenCommandPalette: () => void
}

export default function StatusBar({ connected, workspace, gitStatus, onOpenCommandPalette }: Props) {
  const { splitRatio, setSplitRatio, terminalPanelOpen, setTerminalPanelOpen, aiPanelOpen, setAiPanelOpen } = useStore()

  const handleResize = (e: React.MouseEvent) => {
    e.preventDefault()
    const handleMouseMove = (ev: MouseEvent) => {
      const container = document.querySelector('.main-layout')
      if (!container) return
      const rect = container.getBoundingClientRect()
      const ratio = Math.max(0.15, Math.min(0.85, ev.clientX / rect.width))
      setSplitRatio(ratio)
    }
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }

  return (
    <div className="h-[24px] bg-[#0e0e14] border-t border-[#2a2a35] flex items-center justify-between px-3 text-[11px] text-[#686880] select-none shrink-0">
      <div className="flex items-center gap-3">
        {/* Status indicators */}
        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <CheckCircle className="w-3 h-3 text-green-400" />
              <span className="text-[#8ec88e]">Backend Connected</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-3 h-3 text-red-400" />
              <span className="text-[#ff7b72]">Backend Disconnected</span>
            </>
          )}
          <span className="text-[#3a3a45]">·</span>
          {/* Git status */}
          {gitStatus?.branch && (
            <>
              <GitBranch className="w-3 h-3 text-[#8888a0]" />
              <span className="text-[#8888a0]">{gitStatus.branch}</span>
              {gitStatus.ahead > 0 && (
                <span className="text-[#58a6ff]">↑{gitStatus.ahead}</span>
              )}
              {gitStatus.behind > 0 && (
                <span className="text-[#ff7b72]">↓{gitStatus.behind}</span>
              )}
              <span className="text-[#3a3a45]">·</span>
            </>
          )}
          {/* Workspace */}
          {workspace && (
            <span className="text-[#8888a0] truncate max-w-[200px]" title={workspace.root}>
              {workspace.root.split('/').pop() || workspace.root}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* AI status */}
        <div className="flex items-center gap-1.5">
          <Bot className="w-3 h-3 text-[#8888a0]" />
          <span className="text-[#8888a0]">AI Ready</span>
        </div>

        {/* Panel toggles */}
        <div className="flex items-center gap-2">
          <button
            className={`text-xs px-1.5 py-0.5 rounded ${terminalPanelOpen ? 'bg-[#2a2a35] text-[#c8c8d4]' : 'text-[#686880] hover:text-[#c8c8d4]'
              }`}
            onClick={() => setTerminalPanelOpen(!terminalPanelOpen)}
          >
            <Terminal className="w-3 h-3 inline mr-0.5" />
            Terminal
          </button>
          <button
            className={`text-xs px-1.5 py-0.5 rounded ${aiPanelOpen ? 'bg-[#2a2a35] text-[#c8c8d4]' : 'text-[#686880] hover:text-[#c8c8d4]'
              }`}
            onClick={() => setAiPanelOpen(!aiPanelOpen)}
          >
            <Bot className="w-3 h-3 inline mr-0.5" />
            AI
          </button>
        </div>

        {/* Resize handle indicator */}
        <div className="text-[#3a3a45] flex items-center gap-1">
          <button
            className="hover:text-[#8888a0]"
            onClick={() => setSplitRatio((r) => Math.max(0.15, r - 0.05))}
            title="Shrink sidebar"
          >
            ◀
          </button>
          <button
            className="hover:text-[#8888a0]"
            onClick={() => setSplitRatio((r) => Math.min(0.85, r + 0.05))}
            title="Expand sidebar"
          >
            ▶
          </button>
        </div>

        {/* Command palette shortcut */}
        <div
          className="hidden sm:flex items-center gap-1 text-[#555565] cursor-pointer hover:text-[#8888a0]"
          onClick={onOpenCommandPalette}
        >
          <kbd className="px-1.5 py-0.5 text-[10px] bg-[#2a2a35] rounded border border-[#3a3a45]">
            ⌘K
          </kbd>
        </div>
      </div>
    </div>
  )
}