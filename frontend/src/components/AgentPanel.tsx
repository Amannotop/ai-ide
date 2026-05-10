// Agent Panel Component
import { useState, useCallback } from 'react'
import { Bot, Play, Square, Loader2, Send, CornerDownLeft } from 'lucide-react'

interface Props {
  onClose: () => void
}

interface AgentTask {
  id: string
  goal: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  result?: string
}

const TASK_TYPES = [
  { key: 'code', label: 'Write Code', desc: 'Generate or modify code files' },
  { key: 'fix', label: 'Fix Bugs', desc: 'Debug and fix code issues' },
  { key: 'refactor', label: 'Refactor', desc: 'Improve code structure' },
  { key: 'test', label: 'Tests', desc: 'Write or run tests' },
  { key: 'explain', label: 'Explain Code', desc: 'Analyze and explain code' },
  { key: 'review', label: 'Code Review', desc: 'Review code for issues' },
  { key: 'security', label: 'Security Check', desc: 'Scan for security issues' },
  { key: 'optimize', label: 'Optimize', desc: 'Optimize performance' },
]

export default function AgentPanel({ onClose }: Props) {
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [goal, setGoal] = useState('')
  const [taskType, setTaskType] = useState('code')
  const [isRunning, setIsRunning] = useState(false)
  const [agentOutput, setAgentOutput] = useState<Array<{ type: string; data: string }>>([])

  const handleExecute = useCallback(async () => {
    if (!goal.trim() || isRunning) return

    const taskId = `task-${Date.now()}`
    const newTask: AgentTask = { id: taskId, goal, status: 'running', progress: 0 }
    setTasks((prev) => [newTask, ...prev])
    setIsRunning(true)
    setAgentOutput([])

    // Check for WebSocket support first
    let wsAvailable = false
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/v1/agent/stream`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        wsAvailable = true
        ws.send(JSON.stringify({
          action: 'execute',
          task_type: taskType,
          goal: goal.trim(),
          workspace_root: '/workspace',
        }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setAgentOutput((prev) => [...prev, { type: data.type, data: JSON.stringify(data.data) }])

          if (data.type === 'step_start') {
            setTasks((prev) => prev.map((t) =>
              t.id === taskId ? { ...t, progress: Math.min(100, data.data.step * 14) } : t
            ))
          } else if (data.type === 'complete') {
            setTasks((prev) => prev.map((t) =>
              t.id === taskId ? { ...t, status: 'completed', progress: 100 } : t
            ))
            ws.close()
            setIsRunning(false)
          } else if (data.type === 'error') {
            setTasks((prev) => prev.map((t) =>
              t.id === taskId ? { ...t, status: 'failed', progress: 100 } : t
            ))
            ws.close()
            setIsRunning(false)
          } else if (data.type === 'cancelled') {
            setTasks((prev) => prev.map((t) =>
              t.id === taskId ? { ...t, status: 'failed' } : t
            ))
            ws.close()
            setIsRunning(false)
          }
        } catch {
          // Handle raw text
          setAgentOutput((prev) => [...prev, { type: 'raw', data: event.data as string }])
        }
      }

      ws.onerror = () => {
        setAgentOutput((prev) => [...prev, { type: 'error', data: 'WebSocket connection failed. Trying HTTP fallback...' }])
        // Fall back to HTTP
        fallbackExecute(taskId)
      }

      ws.onclose = () => {
        if (!wsAvailable) {
          fallbackExecute(taskId)
        }
      }
    } catch {
      // WebSocket not available, use HTTP fallback
      fallbackExecute(taskId)
    }
  }, [goal, taskType, isRunning])

  const fallbackExecute = async (taskId: string) => {
    try {
      const res = await fetch('/api/v1/agent/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: taskType,
          goal: goal.trim(),
          workspace_root: '/workspace',
        }),
      })
      const data = await res.json()
      setAgentOutput((prev) => [...prev, { type: 'complete', data: JSON.stringify(data) }])
      setTasks((prev) => prev.map((t) =>
        t.id === taskId ? { ...t, status: 'completed', progress: 100, result: JSON.stringify(data) } : t
      ))
    } catch (e: any) {
      setAgentOutput((prev) => [...prev, { type: 'error', data: e.message }])
      setTasks((prev) => prev.map((t) =>
        t.id === taskId ? { ...t, status: 'failed', progress: 100, error: e.message } : t
      ))
    } finally {
      setIsRunning(false)
    }
  }

  const statusColors = {
    pending: 'text-[#8888a0]',
    running: 'text-[#58a6ff] animate-pulse',
    completed: 'text-[#3fb950]',
    failed: 'text-[#ff7b72]',
  }

  const typeIcons = {
    code: '💻', fix: '🔧', refactor: '♻️', test: '🧪',
    explain: '📖', review: '🔍', security: '🛡️', optimize: '⚡',
  }

  return (
    <div className="h-full flex flex-col bg-[#0e0e14] relative">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#2a2a35] min-h-[34px]">
        <div className="flex items-center gap-1.5">
          <Bot className="w-4 h-4 text-[#8888a0]" />
          <span className="text-xs font-semibold text-[#8888a0] uppercase tracking-wider">Agent</span>
        </div>
        <button className="text-[#686880] hover:text-[#c8c8d4]" onClick={onClose}>
          <Square className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Task type selector */}
        <div className="grid grid-cols-2 gap-2">
          {TASK_TYPES.map((t) => (
            <button
              key={t.key}
              className={`p-2 rounded-lg border text-left transition-colors ${taskType === t.key
                ? 'border-[#58a6ff] bg-[#1a2a3a] text-[#58a6ff]'
                : 'border-[#2a2a35] bg-[#18181e] text-[#8888a0] hover:border-[#444455]'
                }`}
              onClick={() => setTaskType(t.key)}
            >
              <div className="text-lg">{t.icons?.[taskType === t.key ? 0 : 0] || t.label[0]}</div>
              <div className="text-xs font-medium mt-1">{t.label}</div>
              <div className="text-[10px] text-[#686880] mt-0.5">{t.desc}</div>
            </button>
          ))}
        </div>

        {/* Goal input */}
        <div>
          <label className="text-xs text-[#8888a0] mb-1 block">Task Goal</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe what you want the agent to do..."
            className="w-full bg-[#18181e] border border-[#2a2a35] rounded-lg px-3 py-2 text-sm text-[#c8c8d4] placeholder-[#555565] focus:border-[#444455] focus:outline-none resize-none"
            rows={3}
          />
          <button
            onClick={handleExecute}
            disabled={!goal.trim() || isRunning}
            className="mt-2 w-full flex items-center justify-center gap-2 bg-[#264f78] hover:bg-[#316290] disabled:bg-[#2a2a35] disabled:text-[#555565] text-white rounded-lg px-4 py-2 transition-colors text-sm font-medium"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" /> Execute Agent
              </>
            )}
          </button>
        </div>

        {/* Agent output */}
        {agentOutput.length > 0 && (
          <div>
            <div className="text-xs text-[#8888a0] mb-2 uppercase tracking-wider">Agent Output</div>
            <div className="bg-[#121218] border border-[#2a2a35] rounded-lg p-3 font-mono text-xs max-h-64 overflow-y-auto">
              {agentOutput.map((line, i) => (
                <div
                  key={i}
                  className={`mb-1 ${line.type === 'error' ? 'text-[#ff7b72]' : line.type === 'step_start' || line.type === 'step_result'
                    ? 'text-[#58a6ff]'
                    : line.type === 'complete'
                      ? 'text-[#3fb950]'
                      : 'text-[#8888a0]'
                    }`}
                >
                  {line.type === 'step_start' && <CornerDownLeft className="w-3 h-3 inline mr-1" />}
                  {line.type === 'step_result' && <CornerDownLeft className="w-3 h-3 inline mr-1" />}
                  {typeof line.data === 'string' ? line.data.substring(0, 200) : line.data}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Task history */}
        {tasks.length > 0 && (
          <div>
            <div className="text-xs text-[#8888a0] mb-2 uppercase tracking-wider">Task History</div>
            <div className="space-y-1">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between p-2 bg-[#18181e] border border-[#2a2a35] rounded text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${statusColors[task.status]}`} />
                    <span className="text-[#c8c8d4] truncate max-w-[200px]">{task.goal}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[#686880]">
                    {Math.round(task.progress)}%
                    <div className={`w-16 h-1 bg-[#2a2a35] rounded-full overflow-hidden`}>
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${task.status === 'completed' ? 'bg-[#3fb950]' : task.status === 'failed' ? 'bg-[#ff7b72]' : 'bg-[#58a6ff]'
                          }`}
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}