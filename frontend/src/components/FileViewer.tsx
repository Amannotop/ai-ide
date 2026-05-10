// File Viewer - shows binary files, images, etc.
import { useMemo } from 'react'

interface Props {
  content: string
  path: string
}

export default function FileViewer({ content, path }: Props) {
  const ext = path.split('.').pop()?.toLowerCase()

  const isImage = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'bmp'].includes(ext || '')
  const isBinary = !content || content.length === 0 || content.includes('\u0000')

  if (isImage) {
    return (
      <div className="flex items-center justify-center h-full bg-[#121218]">
        <img src={content} alt={path} className="max-w-full max-h-full" />
      </div>
    )
  }

  if (isBinary) {
    return (
      <div className="flex items-center justify-center h-full text-[#555565]">
        <div className="text-center">
          <div className="text-3xl mb-2">📦</div>
          <p className="text-sm">Binary file</p>
          <p className="text-xs text-[#555565]">{path}</p>
        </div>
      </div>
    )
  }

  return null
}