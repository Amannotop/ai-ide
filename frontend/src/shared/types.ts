// Types
export interface FileSystemNode {
  name: string
  path: string
  isDir: boolean
  size?: number
  children?: FileSystemNode[]
}

export interface EditorTab {
  id: string
  path: string
  name: string
  content: string
  language: string
  modified: boolean
}

export const SUPPORTED_LANGUAGES: Record<string, string> = {
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.py': 'python',
  '.go': 'go',
  '.rs': 'rust',
  '.html': 'html',
  '.css': 'css',
  '.scss': 'scss',
  '.json': 'json',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.toml': 'toml',
  '.md': 'markdown',
  '.sql': 'sql',
  '.sh': 'shell',
  '.bash': 'shell',
  '.zsh': 'shell',
  '.dockerfile': 'dockerfile',
  '.env': 'properties',
}

export function getLanguage(filePath: string): string {
  const ext = '.' + filePath.split('.').pop()
  return SUPPORTED_LANGUAGES[ext] || 'plaintext'
}