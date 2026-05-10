// AI Chat Panel Component
import { useState, useRef, useCallback, useEffect } from 'react'
import { Send, Bot, User, Loader2, Plus } from 'lucide-react'
import { api } from '../lib/api'
import { useStore } from '../stores/useStore'

interface Props {
  onClose: () => void
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface FileOption {
  path: string
  name: string
  content: string
}

// Auto-detect relevant files from workspace
async function detectContextFiles(query: string): Promise<FileOption[]> {
  try {
    const res = await api.post('/v1/files/context', {
      query,
      workspace_id: 'default',
      limit: 5000,
    })
    return (res.data.files || []).map((f: any) => ({
      path: f.path,
      name: f.path.split('/').pop() || f.path,
      content: f.content,
    }))
  } catch {
    return []
  }
}

// Detect symbols from the tab content
function detectSymbols(content: string): string[] {
  const symbols: string[] = []
  if (!content) return symbols

  const classRegex = /(?:class|interface|struct)\s+(\w+)/g
  let match
  while ((match = classRegex.exec(content)) !== null) {
    symbols.push(match[1])
  }

  const funcRegex = /(?:function|const\s+\w+\s*[:=]\s*(?:async\s*)?(?:function|\()|export\s+(?:function|const|class|interface|type|enum)\s+)(\w+)/g
  while ((match = funcRegex.exec(content)) !== null) {
    symbols.push(match[1])
  }

  return [...new Set(symbols)]
}

export default function AIChatPanel({ onClose }: Props) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [model, setModel] = useState('qwen2.5-coder:7b')
  const [showModels, setShowModels] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())
  const [showContextPicker, setShowContextPicker] = useState(false)
  const [contextFiles, setContextFiles] = useState<FileOption[]>([])

  const chatEndRef = useRef<HTMLDivElement>(null)
  const { activeTabId, tabs } = useStore()

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Auto-detect context files from current tab and query
  useEffect(() => {
    const detectFiles = async () => {
      if (input.length > 5) {
        const files = await detectContextFiles(input)
        setContextFiles(files)
      }
    }
    const timer = setTimeout(detectFiles, 500)
    return () => clearTimeout(timer)
  }, [input])

  // Get symbols from current tab
  const handleSend = useCallback(
    async (e?: React.FormEvent) => {
      if (e) e.preventDefault()
      if (!input.trim() || isLoading) return

      const userMessage = input.trim()
      const activeTab = tabs.find((t) => t.id === activeTabId)

      // Build context-aware prompt
      let prompt = userMessage

      // Add file context mentions
      if (selectedFiles.size > 0) {
        const filesContext = Array.from(selectedFiles)
          .map((fp) => {
            const f = contextFiles.find((cf) => cf.path === fp)
            return f ? `File: ${f.path}\n\`\`\`\n${f.content.substring(0, 3000)}\n\`\`\`` : ''
          })
          .join('\n\n')
        if (filesContext) {
          prompt = `[Context files provided above]\n\nUser query: ${userMessage}`
        }
      }

      // Add current tab context
      if (activeTab) {
        const symbols = detectSymbols(activeTab.content)
        prompt = `[Active file: ${activeTab.path} (${activeTab.language})]\n${symbols.length > 0 ? `[Symbols: ${symbols.join(', ')}]\n` : ''}\n\n${prompt}`
      }

      const newMessages = [
        ...messages,
        { role: 'user' as const, content: userMessage },
        { role: 'assistant' as const, content: '' },
      ]
      const assistantIndex = newMessages.length - 1
      setMessages(newMessages)
      setInput('')
      setIsLoading(true)

      try {
        // Check if Ollama is available first
        let ollamaAvailable = false
        try {
          const health = await api.get('/v1/health', { timeout: 2000 })
          ollamaAvailable = health.data.status === 'ok'
        } catch {
          ollamaAvailable = false
        }

        if (ollamaAvailable) {
          // Try streaming first via WebSocket
          try {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/v1/agent/chat-stream`

            const ws = new WebSocket(wsUrl)

            ws.onopen = () => {
              ws.send(
                JSON.stringify({
                  model,
                  messages: newMessages.filter((m) => m.role !== 'assistant').map((m) => ({
                    role: m.role === 'user' ? 'user' : 'system',
                    content: m.content,
                  })),
                  stream: true,
                  temperature: 0.7,
                  max_tokens: 2048,
                })
              )
            }

            ws.onmessage = (event) => {
              try {
                const data = JSON.parse(event.data)
                if (data.type === 'chunk') {
                  setMessages((prev) => {
                    const updated = [...prev]
                    const last = updated[updated.length - 1]
                    if (last && last.role === 'assistant') {
                      last.content += data.content || ''
                    }
                    return updated
                  })
                } else if (data.type === 'complete') {
                  ws.close()
                  setIsLoading(false)
                } else if (data.type === 'error') {
                  setMessages((prev) => {
                    const updated = [...prev]
                    updated[assistantIndex] = { ...updated[assistantIndex], content: `Error: ${data.error}` }
                    return updated
                  })
                  ws.close()
                  setIsLoading(false)
                }
              } catch {
                // Non-JSON frame, append raw content
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last && last.role === 'assistant') {
                    last.content += (event.data as string)
                  }
                  return updated
                })
              }
            }

            ws.onerror = () => {
              setIsLoading(false)
              fallbackStreaming()
            }

            ws.onclose = () => {
              const lastMsg = messages[assistantIndex]
              if (lastMsg && lastMsg.content === '') {
                setIsLoading(false)
              }
            }
          } catch {
            fallbackStreaming()
          }
        } else {
          fallbackStreaming()
        }
      } catch (error) {
        setMessages((prev) => {
          const updated = [...prev]
          updated[assistantIndex] = {
            ...updated[assistantIndex],
            content: `Error: ${error instanceof Error ? error.message : 'Failed to connect to AI backend'}`,
          }
          return updated
        })
        setIsLoading(false)
      }
    },
    [input, messages, isLoading, model, activeTabId, tabs, contextFiles, selectedFiles]
  )

  // Fallback: non-streaming HTTP request
  const fallbackStreaming = useCallback(async () => {
    try {
      const result = await api.post('/v1/agent/chat', {
        model,
        messages: messages.filter((m) => m.role !== 'assistant').map((m) => ({
          role: m.role === 'user' ? 'user' : 'system',
          content: m.content,
        })),
        stream: false,
        temperature: 0.7,
        max_tokens: 2048,
      })

      const content =
        result.data?.message?.content ||
        result.data?.choices?.[0]?.message?.content ||
        'No response from AI backend. Ensure Ollama is running.'

      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { ...updated[updated.length - 1], content }
        return updated
      })
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: `Error: ${error instanceof Error ? error.message : 'Connection failed'}`,
        }
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }, [model, messages])

  // Handle Enter to send, Shift+Enter for newline
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  const availableModels = ['qwen2.5-coder:7b', 'qwen2.5-coder:14b', 'qwen2.5-coder:32b', 'deepseek-coder-v2', 'gemma2:9b', 'phi3:mini']

  return (
    <div className="h-full flex flex-col bg-[#0e0e14] relative">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#2a2a35] min-h-[34px]">
        <div className="flex items-center gap-1.5">
          <Bot className="w-4 h-4 text-[#8888a0]" />
          <span className="text-xs font-semibold text-[#8888a0] uppercase tracking-wider">
            AI Chat
          </span>
        </div>
        <div className="flex items-center gap-1">
          {/* Model selector */}
          <div className="relative">
            <button
              className="text-xs px-2 py-0.5 bg-[#1e1e28] hover:bg-[#2a2a35] text-[#8888a0] rounded border border-[#2a2a35]"
              onClick={() => setShowModels(!showModels)}
            >
              {model}
            </button>
            {showModels && (
              <div className="absolute right-0 top-full mt-1 w-60 bg-[#18181e] border border-[#2a2a35] rounded shadow-lg z-50 max-h-48 overflow-y-auto">
                {availableModels.map((m) => (
                  <button
                    key={m}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-[#2a2a35] text-[#c8c8d4]"
                    onClick={() => {
                      setModel(m)
                      setShowModels(false)
                    }}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* Close button */}
          <button
            className="text-[#686880] hover:text-[#c8c8d4]"
            onClick={onClose}
          >
            <svg width="14" height="14" viewBox="0 0 15 15" fill="currentColor">
              <path d="M11.78 2.78a.75.75 0 0 1 0 1.06L8.56 7.5l3.22 3.22a.75.75 0 1 1-1.06 1.06L7.5 8.56l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.44 7.5 3.22 4.28a.75.75 0 0 1 1.06-1.06L7.5 6.44l3.22-3.22a.75.75 0 0 1 1.06 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#555565] text-sm space-y-2">
            <Bot className="w-10 h-10 opacity-30" />
            <p>Ask me anything about your codebase</p>
            <p className="text-xs text-[#444455]">
              I can read files, search your codebase, write code, and more
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex gap-2.5 ${msg.role === 'assistant' ? '' : 'flex-row-reverse'
                }`}
            >
              <div className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center mt-0.5
                bg-[#1e1e28] border border-[#2a2a35]"
              >
                {msg.role === 'assistant' ? (
                  <Bot className="w-3.5 h-3.5 text-[#8888a0]" />
                ) : (
                  <User className="w-3.5 h-3.5 text-[#8888a0]" />
                )}
              </div>
              <div
                className={`max-w-[calc(100%-44px)] prose prose-invert prose-sm leading-relaxed
                  ${msg.role === 'assistant'
                    ? 'bg-[#18181e] border border-[#2a2a35]'
                    : 'bg-[#1a2a1a] border border-[#2a3a2a]'
                  } rounded-lg px-3 py-2 text-[#c8c8d4]`}
              >
                <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex gap-2.5">
            <div className="w-7 h-7 rounded-lg flex-shrink-0 flex items-center justify-center
              bg-[#1e1e28] border border-[#2a2a35]"
            >
              <Loader2 className="w-3.5 h-3.5 text-[#8888a0] animate-spin" />
            </div>
            <div className="bg-[#18181e] border border-[#2a2a35] rounded-lg px-3 py-2">
              <div className="flex gap-1.5">
                <span className="text-sm">●</span>
                <span className="text-sm animate-pulse">●</span>
                <span className="text-sm">●</span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#2a2a35] p-3">
        {/* Context pills */}
        {selectedFiles.size > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {Array.from(selectedFiles).map((fp) => (
              <span
                key={fp}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-[#1e2a1e] text-[#8ec88e] rounded border border-[#2a3a2a]"
              >
                {fp.split('/').pop()}
                <button
                  className="ml-1 hover:text-[#ff7b72]"
                  onClick={() => setSelectedFiles((prev) => {
                    const next = new Set(prev)
                    next.delete(fp)
                    return next
                  })}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <form onSubmit={handleSend} className="flex gap-2">
          <button
            type="button"
            className="text-[#686880] hover:text-[#a0b0c0] flex-shrink-0 mt-1.5 transition-colors"
            onClick={() => setShowContextPicker(!showContextPicker)}
            title="Add context files"
          >
            <Plus className="w-5 h-5" />
          </button>
          {showContextPicker && contextFiles.length > 0 && (
            <div className="absolute bottom-16 left-3 right-3 bg-[#18181e] border border-[#2a2a35] rounded-lg shadow-xl max-h-48 overflow-y-auto z-50 p-2">
              <p className="text-xs text-[#686880] mb-1 px-2">Relevant files</p>
              {contextFiles.slice(0, 20).map((f) => (
                <button
                  key={f.path}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded flex items-center gap-2 hover:bg-[#2a2a35] ${selectedFiles.has(f.path) ? 'text-[#8ec88e]' : 'text-[#c8c8d4]'
                    }`}
                  onClick={() => setSelectedFiles((prev) => {
                    const next = new Set(prev)
                    if (next.has(f.path)) next.delete(f.path)
                    else next.add(f.path)
                    return next
                  })}
                >
                  <span>📄</span>
                  {f.path.split('/').pop()}
                </button>
              ))}
            </div>
          )}
          <textarea
            ref={null}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your codebase... (Ctrl+K for commands)"
            className="flex-1 resize-none bg-[#18181e] border border-[#2a2a35] rounded-lg px-3 py-2 text-sm text-[#c8c8d4] placeholder-[#555565] focus:border-[#444455] focus:outline-none max-h-32 leading-relaxed"
            rows={1}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement
              target.style.height = 'auto'
              target.style.height = Math.min(target.scrollHeight, 128) + 'px'
            }}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="text-white bg-[#264f78] hover:bg-[#316290] disabled:bg-[#2a2a35] disabled:text-[#555565] rounded-lg px-4 py-2 flex-shrink-0 transition-colors text-sm font-medium"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  )
}