// Activity Bar Component
import { Terminal, Bot, Settings } from 'lucide-react'

interface Props {
  aiPanelOpen: boolean
  terminalPanelOpen: boolean
  agentPanelOpen: boolean
  onToggleAi: () => void
  onToggleTerminal: () => void
  onToggleAgent: () => void
  onOpenCommandPalette: () => void
  connected: boolean
  gitStatus: { branch: string | null; ahead: number; behind: number; files: { path: string; status: string }[] } | null
}

export default function ActivityBar({
  aiPanelOpen,
  terminalPanelOpen,
  agentPanelOpen,
  onToggleAi,
  onToggleTerminal,
  onToggleAgent,
  onOpenCommandPalette,
  connected,
  gitStatus,
}: Props) {
  return (
    <nav className="ai-activity-bar flex flex-col items-center pt-2 pb-1 gap-1 w-[48px] shrink-0 bg-[#121218] border-r border-[#2a2a35]">
      {/* Search */}
      <button
        className="w-10 h-10 flex items-center justify-center text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35] rounded transition-colors"
        title="Search"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </button>

      {/* Git */}
      <button
        className="w-10 h-10 flex items-center justify-center text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35] rounded transition-colors relative"
        title="Git"
      >
        <GitBranchIcon hasChanges={!!gitStatus?.files?.length} />
      </button>

      {/* Extensions */}
      <button
        className="w-10 h-10 flex items-center justify-center text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35] rounded transition-colors"
        title="Extensions"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      </button>

      {/* AI button */}
      <button
        className={`w-10 h-10 flex items-center justify-center rounded transition-colors ${aiPanelOpen
          ? 'bg-[#2a2a35] text-[#58a6ff]'
          : 'text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35]'
          }`}
        onClick={onToggleAi}
        title="AI Chat"
      >
        <Bot className="w-5 h-5" />
      </button>

      {/* Agent button */}
      <button
        className={`w-10 h-10 flex items-center justify-center rounded transition-colors ${agentPanelOpen
          ? 'bg-[#2a2a35] text-[#ffa657]'
          : 'text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35]'
          }`}
        onClick={onToggleAgent}
        title="Agent"
      >
        🤖
      </button>

      <div className="my-1 h-px bg-[#2a2a35]" />

      {/* Terminal button */}
      <div className="relative">
        <button
          className={`w-10 h-10 flex items-center justify-center rounded transition-colors ${terminalPanelOpen
            ? 'bg-[#2a2a35] text-[#58a6ff]'
            : 'text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35]'
            }`}
          onClick={onToggleTerminal}
          title="Terminal"
        >
          <Terminal className="w-5 h-5" />
        </button>
        {connected && (
          <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-green-400" />
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <button
        className="w-10 h-10 flex items-center justify-center text-[#686880] hover:text-[#c8c8d4] hover:bg-[#2a2a35] rounded transition-colors"
        title="Settings"
        onClick={onOpenCommandPalette}
      >
        <Settings className="w-5 h-5" />
      </button>
    </nav>
  )
}

function GitBranchIcon({ hasChanges }: { hasChanges: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 3v12l4-4 4 4 4-10-4 4-4-4-4 4z" />
      {hasChanges && <circle cx="12" cy="4" r="2" fill="#ff7b72" />}
    </svg>
  )
}