// Shared API client
import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// WebSocket connection helper
export function createWsConnection(endpoint: string, onMessage: (data: any) => void, onError?: (err: any) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}${endpoint}`)

  ws.onopen = () => console.debug('[ws] connected:', endpoint)
  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch {
      onMessage(event.data)
    }
  }
  ws.onerror = (err) => onError?.(err)
  ws.onclose = () => console.debug('[ws] disconnected:', endpoint)

  return ws
}