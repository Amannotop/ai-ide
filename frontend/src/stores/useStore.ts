import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

// ── Types ────────────────────────────────────────────────────

export interface EditorTab {
  id: string
  path: string
  name: string
  content: string
  language: string
  modified: boolean
  cursor?: { line: number; column: number }
}

export interface TerminalSession {
  id: string
  name: string
  pid?: number
}

export interface AIProvider {
  name: string
  model: string
  baseUrl: string
  status: 'connected' | 'disconnected' | 'connecting'
}

export interface WorkspaceState {
  root: string
  files: FileSystemNode[]
}

export interface FileSystemNode {
  name: string
  path: string
  isDir: boolean
  size?: number
  children?: FileSystemNode[]
}

export interface Conversation {
  id: string
  title: string
  model: string
  messages: ChatMessage[]
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: number
}

export interface AgentTask {
  id: string
  goal: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  result?: string
  error?: string
}

export interface AppState {
  // Tabs & Editor
  tabs: EditorTab[]
  activeTabId: string | null
  sidebarOpen: boolean
  sidebarWidth: number

  // Terminal
  terminals: TerminalSession[]
  activeTerminalId: string | null
  terminalPanelOpen: boolean

  // AI Chat
  conversations: Conversation[]
  activeConversationId: string | null
  aiPanelOpen: boolean
  streamingMessage: string
  isStreaming: boolean

  // Agent
  agentTasks: AgentTask[]
  agentPanelOpen: boolean
  agentRunning: boolean

  // Workspace
  workspace: WorkspaceState | null
  gitStatus: GitStatus | null

  // Settings
  theme: 'dark' | 'light'
  fontSize: number
  modelProvider: string
  defaultModel: string

  // Layout
  splitRatio: number
  commandPaletteOpen: boolean

  // Actions
  setTabs: (tabs: EditorTab[]) => void
  addTab: (tab: EditorTab) => void
  closeTab: (tabId: string) => void
  setActiveTab: (tabId: string) => void
  updateTabContent: (tabId: string, content: string, modified: boolean) => void
  setSidebarOpen: (open: boolean) => void
  setAiPanelOpen: (open: boolean) => void
  setTerminalPanelOpen: (open: boolean) => void
  setAgentPanelOpen: (open: boolean) => void
  setCommandPaletteOpen: (open: boolean) => void
  setTheme: (theme: 'dark' | 'light') => void
  setFontSize: (size: number) => void
  addConversation: (conversation: Conversation) => void
  setActiveConversation: (id: string | null) => void
  addMessageToConversation: (conversationId: string, message: ChatMessage) => void
  setStreamingMessage: (msg: string) => void
  setIsStreaming: (streaming: boolean) => void
  setWorkspace: (workspace: WorkspaceState | null) => void
  updateGitStatus: (status: GitStatus | null) => void
  addAgentTask: (task: AgentTask) => void
  updateAgentTask: (id: string, task: Partial<AgentTask>) => void
  setSplitRatio: (ratio: number) => void
  clearAll: () => void
}

export interface GitStatus {
  branch: string | null
  ahead: number
  behind: number
  files: { path: string; status: string }[]
}

// ── Store ───────────────────────────────────────────────────

export const useStore = create<AppState>()(
  devtools(
    (set) => ({
      // Initial state
      tabs: [],
      activeTabId: null,
      sidebarOpen: true,
      sidebarWidth: 260,
      terminals: [],
      activeTerminalId: null,
      terminalPanelOpen: false,
      conversations: [],
      activeConversationId: null,
      aiPanelOpen: true,
      streamingMessage: '',
      isStreaming: false,
      agentTasks: [],
      agentPanelOpen: false,
      agentRunning: false,
      workspace: null,
      gitStatus: null,
      theme: 'dark',
      fontSize: 13,
      modelProvider: 'ollama',
      defaultModel: 'qwen2.5-coder:7b',
      splitRatio: 0.6,
      commandPaletteOpen: false,

      // Actions
      setTabs: (tabs) => set({ tabs }),
      addTab: (tab) =>
        set((state) => ({
          tabs: state.tabs.some((t) => t.id === tab.id) ? state.tabs : [...state.tabs, tab],
          activeTabId: tab.id,
        })),
      closeTab: (tabId) =>
        set((state) => {
          const tabs = state.tabs.filter((t) => t.id !== tabId)
          return {
            tabs,
            activeTabId: tabs.length > 0 ? tabs[Math.min(tabs.length - 1, state.tabs.findIndex((t) => t.id === tabId) - 1)]?.id ?? null : null,
          }
        }),
      setActiveTab: (tabId) => set({ activeTabId: tabId }),
      updateTabContent: (tabId, content, modified) =>
        set((state) => ({
          tabs: state.tabs.map((t) => (t.id === tabId ? { ...t, content, modified } as EditorTab : t)),
        })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setAiPanelOpen: (open) => set({ aiPanelOpen: open }),
      setTerminalPanelOpen: (open) => set({ terminalPanelOpen: open }),
      setAgentPanelOpen: (open) => set({ agentPanelOpen: open }),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      setTheme: (theme) => set({ theme }),
      setFontSize: (fontSize) => set({ fontSize }),
      addConversation: (conversation) =>
        set((state) => ({
          conversations: [conversation, ...state.conversations.filter((c) => c.id !== conversation.id)],
        })),
      setActiveConversation: (id) => set({ activeConversationId: id }),
      addMessageToConversation: (conversationId, message) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId ? { ...c, messages: [...c.messages, message] } : c
          ),
        })),
      setStreamingMessage: (msg) => set({ streamingMessage: msg }),
      setIsStreaming: (streaming) => set({ isStreaming: streaming }),
      setWorkspace: (workspace) => set({ workspace }),
      updateGitStatus: (status) => set({ gitStatus: status }),
      addAgentTask: (task) =>
        set((state) => ({
          agentTasks: [task, ...state.agentTasks.filter((t) => t.id !== task.id)],
        })),
      updateAgentTask: (id, task) =>
        set((state) => ({
          agentTasks: state.agentTasks.map((t) => (t.id === id ? { ...t, ...task } : t)),
        })),
      setSplitRatio: (ratio) => set({ splitRatio: ratio }),
      clearAll: () =>
        set({
          tabs: [],
          activeTabId: null,
          conversations: [],
          activeConversationId: null,
          streamingMessage: '',
          isStreaming: false,
          agentTasks: [],
          workspace: null,
          gitStatus: null,
        }),
    }),
    { name: 'ai-ide-store' }
  )
)