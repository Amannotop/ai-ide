// Monaco Editor Component
import { useRef, useEffect, useState } from 'react'
import Editor, { type Monaco } from '@monaco-editor/react'
import { useStore } from '../stores/useStore'
import { EditorTab } from '../shared/types'

interface Props {
  tab: EditorTab
  onContentChange?: (content: string) => void
}

export default function MonacoEditor({ tab, onContentChange }: Props) {
  const editorRef = useRef<any>(null)
  const { updateTabContent } = useStore()
  const [mounted, setMounted] = useState(false)

  const handleEditorDidMount = useCallback((editor: any, monaco: Monaco) => {
    editorRef.current = editor

    // Configure editor defaults
    editor.updateOptions({
      fontSize: 13,
      fontFamily: '"JetBrains Mono", "Fira Code", "SF Mono", Menlo, monospace',
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      cursorBlinking: 'smooth',
      renderWhitespace: 'selection',
      renderIndentGuides: true,
      lineNumbersMinChars: 3,
      tabSize: 2,
      insertSpaces: true,
      detectIndentation: true,
      wordWrap: 'on',
      wordWrapColumn: 120,
      wrappingIndent: 'indent',
    })

    // Add custom command for save
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Will be handled by the app
    })

    setMounted(true)
  }, [])

  const handleChange = useCallback(
    (value: string | undefined) => {
      if (value !== undefined && mounted) {
        onContentChange?.(value)
        updateTabContent(tab.id, value, true)
      }
    },
    [tab.id, onContentChange, updateTabContent, mounted]
  )

  // Theme configuration
  useEffect(() => {
    if (editorRef.current) {
      const { monaco } = editorRef.current
      monaco.editor.defineTheme('ai-ide-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
          { token: '', foreground: 'c9d1d9', background: '0d1117' },
          { token: 'comment', foreground: '8b949e', fontStyle: 'italic' },
          { token: 'keyword', foreground: 'ff7b72' },
          { token: 'string', foreground: 'a5d6ff' },
          { token: 'number', foreground: '79c0ff' },
          { token: 'type', foreground: 'ffa657' },
          { token: 'function', foreground: 'd2a8ff' },
          { token: 'operator', foreground: '7ee787' },
        ],
        colors: {
          'editor.background': '#0e0e14',
          'editor.foreground': '#c9d1d9',
          'editor.lineHighlightBackground': '#16161d',
          'editor.selectionBackground': '#264f78',
          'editorCursor.foreground': '#58a6ff',
          'editorIndentGuide.background': '#21262d',
          'editorIndentGuide.activeBackground': '#388bfd20',
          'editorGutter.background': '#0e0e14',
          'scrollbarSlider.background': '#484f58',
          'scrollbarSlider.hoverBackground': '#5a6270',
          'scrollbarSlider.activeBackground': '#7a8290',
          'tab.activeBorder': '#58a6ff',
          'editorBracketMatch.background': '#2a4a7f40',
        },
      })
      editorRef.current.updateOptions({ theme: 'ai-ide-dark' })
    }
  }, [])

  return (
    <Editor
      key={tab.id}
      height="100%"
      language={tab.language}
      value={tab.content}
      onChange={handleChange}
      onMount={handleEditorDidMount}
      options={{
        fontSize: 13,
        fontFamily: '"JetBrains Mono", "Fira Code", monospace',
        minimap: { enabled: true, scale: 4 },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        renderWhitespace: 'selection' as const,
        renderIndentGuides: true,
        lineNumbersMinChars: 3,
        tabSize: 2,
        insertSpaces: true,
        detectIndentation: true,
        wordWrap: 'on' as const,
        wordWrapColumn: 120,
        wrappingIndent: 'indent' as const,
        padding: { top: 12 },
      }}
    />
  )
}