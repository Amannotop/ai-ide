// Status Bar Component
import { GitBranch, Terminal, Bot } from 'lucide-react'
import { useStore } from '../stores/useStore'

interface Props {
  connected: boolean
  workspace: { root: string; files: any[] } | null
  gitStatus: { branch: string | null; ahead: number; behind: number; files: { path: string; status: string }[] } | null
  onOpenCommandPalette: () => void
}

export default function StatusBar({ connected, workspace, gitStatus, onOpenCommandPalette }: Props) {
  const { terminalPanelOpen, setTerminalPanelOpen, aiPanelOpen, setAiPanelOpen } = useStore()

  return (
    <div className="h-[24px] bg-[#0e0e14] border-t border-[#2a2a35] flex items-center justify-between px-3 text-[11px] text-[#686880] select-none shrink-0">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          {connected ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
              <span className="text-[#8ec88e]">Backend</span>
            </>
          ) : (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
              <span className="text-[#ff7b72]">Disconnected</span>
            </>
          )}
          <span className="text-[#3a3a45]">·</span>
          {gitStatus?.branch && (
            <>
              <GitBranch className="w-3 h-3 text-[#8888a0]" />
              <span className="text-[#8888a0]">{gitStatus.branch}</span>
              {gitStatus.ahead > 0 && <span className="text-[#58a6ff]">↑{gitStatus.ahead}</span>}
              {gitStatus.behind > 0 && <span className="text-[#ff7b72]">↓{gitStatus.behind}</span>}
              <span className="text-[#3a3a45]">·</span>
            </>
          )}
          {workspace && (
            <span className="text-[#8888a0] truncate max-w-[200px]" title={workspace.root}>
              {workspace.root.split('/').pop() || workspace.root}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <Bot className="w-3 h-3 text-[#8888a0]" />
          <span className="text-[#8888a0]">AI Ready</span>
        </div>

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