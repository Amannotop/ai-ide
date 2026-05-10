// Main App Layout Component
import { useState, useEffect, useCallback } from 'react'
import { useStore } from './stores/useStore'
import { api } from './lib/api'
import Editor from './components/Editor'
import FileExplorer from './components/FileExplorer'
import AIChatPanel from './components/AIChatPanel'
import TerminalPanel from './components/TerminalPanel'
import StatusBar from './components/StatusBar'
import ActivityBar from './components/ActivityBar'
import CommandPalette from './components/CommandPalette'
import AgentPanel from './components/AgentPanel'

function App() {
  const {
    tabs,
    activeTabId,
    sidebarOpen,
    aiPanelOpen,
    terminalPanelOpen,
    agentPanelOpen,
    workspace,
    gitStatus,
    commandPaletteOpen,
    addTab,
    setActiveTab,
    closeTab,
    setSidebarOpen,
    setAiPanelOpen,
    setTerminalPanelOpen,
    setAgentPanelOpen,
    setCommandPaletteOpen,
    setWorkspace,
    updateGitStatus,
  } = useStore()

  const [connected, setConnected] = useState(false)
  const [fileExplorerData, setFileExplorerData] = useState<any[]>([])

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await api.get('/v1/health')
        setConnected(res.data.status === 'ok')
      } catch {
        setConnected(false)
      }
    }
    checkBackend()
    const interval = setInterval(checkBackend, 5000)
    return () => clearInterval(interval)
  }, [])

  // Load file tree
  const loadFileTree = useCallback(async () => {
    try {
      // First ensure a workspace directory exists
      await api.post('/v1/git/init', {}, { params: { repo_path: '.' } }).catch(() => {})
      const res = await api.get('/v1/files/tree')
      if (res.data && res.data.children) {
        setFileExplorerData(res.data.children)
        setWorkspace({ root: res.data.path || '.', files: res.data.children || [] })
      }
    } catch (err) {
      console.error('Failed to load file tree:', err)
    }
  }, [setWorkspace])

  useEffect(() => {
    loadFileTree()
  }, [loadFileTree])

  // Load git status periodically
  useEffect(() => {
    const loadGitStatus = async () => {
      try {
        const res = await api.get('/v1/git/status')
        if (res.data.is_repo) {
          updateGitStatus({
            branch: res.data.branch,
            ahead: res.data.ahead,
            behind: res.data.behind,
            files: (res.data.changes || []).map((c: any) => ({
              path: c.file,
              status: c.status,
            })),
          })
        }
      } catch {
        // Not a git repo - that's fine
      }
    }
    loadGitStatus()
    const interval = setInterval(loadGitStatus, 10000)
    return () => clearInterval(interval)
  }, [updateGitStatus])

  // Handle file open from explorer
  const handleFileOpen = useCallback(async (path: string) => {
    try {
      const res = await api.get('/v1/files/read', { params: { path } })
      const file = res.data
      if (file.exists) {
        const language = getLanguageFromPath(path)
        const tabId = `file-${path}`
        addTab({
          id: tabId,
          path,
          name: path.split('/').pop() || path,
          content: file.content,
          language,
          modified: false,
        })
        setActiveTab(tabId)
      }
    } catch (err) {
      console.error('Failed to open file:', err)
    }
  }, [addTab, setActiveTab])

  // Save file
  const handleSave = useCallback(async (tabId: string) => {
    const tab = tabs.find((t) => t.id === tabId)
    if (tab) {
      try {
        await api.post('/v1/files/write', {
          path: tab.path,
          content: tab.content,
        })
      } catch (err) {
        console.error('Failed to save file:', err)
      }
    }
  }, [tabs])

  // Refresh files
  const handleRefresh = useCallback(async () => {
    await loadFileTree()
  }, [loadFileTree])

  // Open terminal
  const handleOpenTerminal = useCallback(() => {
    setTerminalPanelOpen(true)
  }, [setTerminalPanelOpen])

  // Get active tab content
  const activeTab = tabs.find((t) => t.id === activeTabId) || null

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#0e0e14] text-[#c8c8d4]">
      {/* Activity Bar (left side) */}
      <ActivityBar
        aiPanelOpen={aiPanelOpen}
        terminalPanelOpen={terminalPanelOpen}
        agentPanelOpen={agentPanelOpen}
        onToggleAi={() => setAiPanelOpen(!aiPanelOpen)}
        onToggleTerminal={() => setTerminalPanelOpen(!terminalPanelOpen)}
        onToggleAgent={() => setAgentPanelOpen(!agentPanelOpen)}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        connected={connected}
        gitStatus={gitStatus}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar - File Explorer */}
        <aside
          className={`transition-all duration-150 ease-in-out overflow-hidden border-r border-[#2a2a35] flex-shrink-0
            ${sidebarOpen ? 'w-[260px]' : 'w-[48px]'}`}
        >
          <div className="h-full flex flex-col">
            <div className="px-3 py-2 border-b border-[#2a2a35] flex items-center justify-between min-h-[28px]">
              <span className="text-xs font-semibold text-[#8888a0] uppercase tracking-wider">
                {sidebarOpen ? 'Explorer' : ''}
              </span>
              {sidebarOpen && (
                <div className="flex gap-0.5">
                  <Button
                    variant="ghost"
                    size="iconSm"
                    onClick={handleRefresh}
                    title="Refresh"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3.05 12A9 9 0 0 1 12 3.05M21 12a9 9 0 0 1-9 9" />
                      <circle cx="12" cy="12" r="2" />
                    </svg>
                  </Button>
                </div>
              )}
            </div>
            {sidebarOpen && (
              <div className="flex-1 overflow-y-auto">
                <FileExplorer
                  data={fileExplorerData}
                  onFileClick={handleFileOpen}
                  onRefresh={handleRefresh}
                />
              </div>
            )}
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Editor Tabs */}
          <div className="flex-shrink-0 bg-[#18181e] border-b border-[#2a2a35] flex items-center overflow-x-auto h-[34px]">
            {tabs.map((tab) => (
              <div
                key={tab.id}
                className={`flex items-center gap-1.5 px-3 h-full cursor-pointer border-r border-[#2a2a35] text-xs min-w-[120px] max-w-[200px] truncate
                  ${tab.id === activeTabId
                    ? 'bg-[#0e0e14] text-[#c8c8d4] border-b-2 border-b-[#8888a0]'
                    : 'bg-[#18181e] text-[#686880] hover:bg-[#1e1e28]'
                  }`}
                onClick={() => setActiveTab(tab.id)}
                onDoubleClick={() => handleSave(tab.id)}
              >
                <span className="truncate">{tab.name}</span>
                {tab.modified && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />}
                <button
                  className="ml-auto hover:text-[#c8c8d4] opacity-0 group-hover/tab:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation()
                    closeTab(tab.id)
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 15 15" fill="currentColor">
                    <path d="M11.78 2.78a.75.75 0 0 1 0 1.06L8.56 7.5l3.22 3.22a.75.75 0 1 1-1.06 1.06L7.5 8.56l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.44 7.5 3.22 4.28a.75.75 0 0 1 1.06-1.06L7.5 6.44l3.22-3.22a.75.75 0 0 1 1.06 0z" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Editor Area */}
          <div className="flex-1 overflow-hidden">
            {activeTab ? (
              <Editor
                tab={activeTab}
                onContentChange={(content) => {
                  const existing = tabs.find((t) => t.id === activeTabId)
                  if (existing && existing.content !== content) {
                    // Update store but don't save yet
                  }
                }}
              />
            ) : (
              <div className="h-full flex items-center justify-center text-[#555565] text-sm">
                <div className="text-center">
                  <div className="text-3xl mb-2 opacity-50">📄</div>
                  <p>Open a file from the explorer to start editing</p>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Panel */}
          {terminalPanelOpen && (
            <TerminalPanel onClose={() => setTerminalPanelOpen(false)} />
          )}
        </main>

        {/* Right Side Panels */}
        <div className={`flex-shrink-0 border-l border-[#2a2a35] flex flex-col overflow-hidden transition-all duration-150 ease-in-out
          ${aiPanelOpen ? 'w-[400px]' : 'w-[40px]'}`}
        >
          {/* AI Chat Panel */}
          {aiPanelOpen && (
            <AIChatPanel onClose={() => setAiPanelOpen(false)} />
          )}
          {/* Agent Panel */}
          {agentPanelOpen && (
            <AgentPanel onClose={() => setAgentPanelOpen(false)} />
          )}
        </div>
      </div>

      {/* Status Bar */}
      <StatusBar
        connected={connected}
        workspace={workspace}
        gitStatus={gitStatus}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
      />

      {/* Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onOpenTerminal={handleOpenTerminal}
      />
    </div>
  )
}

function getLanguageFromPath(path: string): string {
  const ext = '.' + path.split('.').pop()?.toLowerCase()
  const map: Record<string, string> = {
    '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript',
    '.py': 'python', '.go': 'go', '.rs': 'rust',
    '.html': 'html', '.css': 'css', '.scss': 'scss',
    '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml', '.md': 'markdown', '.sql': 'sql',
    '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
    '.dockerfile': 'dockerfile', '.env': 'properties',
    '.xml': 'xml', '.svg': 'xml',
  }
  return map[ext] || 'plaintext'
}

export default App