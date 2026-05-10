// File Explorer Component
import { useState, useCallback, useEffect } from 'react'
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from 'lucide-react'
import { FileSystemNode } from '../shared/types'

interface Props {
  data: FileSystemNode[]
  onFileClick: (path: string) => void
  onRefresh: () => void
}

interface TreeNodeProps {
  node: FileSystemNode
  depth: number
  onFileClick: (path: string) => void
  openFolders: Set<string>
  toggleFolder: (path: string) => void
}

function TreeNode({ node, depth, onFileClick, openFolders, toggleFolder }: TreeNodeProps) {
  const isOpen = openFolders.has(node.path)
  const paddingLeft = (depth + 1) * 12

  if (node.isDir) {
    const sortedChildren = [...(node.children || [])].sort((a, b) => {
      if (a.isDir && !b.isDir) return -1
      if (!a.isDir && b.isDir) return 1
      return a.name.localeCompare(b.name)
    })

    return (
      <div>
        <div
          className="flex items-center gap-1 px-2 py-1 cursor-pointer hover:bg-[#2a2a35] text-sm"
          style={{ paddingLeft: `${paddingLeft}px` }}
          onClick={() => toggleFolder(node.path)}
        >
          <span className="w-4 flex-shrink-0">
            {isOpen ? (
              <ChevronDown className="w-3 h-3 text-[#686880]" />
            ) : (
              <ChevronRight className="w-3 h-3 text-[#686880]" />
            )}
          </span>
          {isOpen ? (
            <FolderOpen className="w-3.5 h-3.5 text-[#a0b0c0] shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-[#a0b0c0] shrink-0" />
          )}
          <span className="ml-1 truncate">{node.name}</span>
        </div>
        {isOpen && sortedChildren.length > 0 && (
          <div>
            {sortedChildren.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
                openFolders={openFolders}
                toggleFolder={toggleFolder}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className="flex items-center gap-1 px-2 py-1 cursor-pointer hover:bg-[#2a2a35] text-sm"
      style={{ paddingLeft: `${paddingLeft}px` }}
      onClick={() => onFileClick(node.path)}
    >
      <span className="w-4 flex-shrink-0">
        <ChevronRight className="w-3 h-3 text-transparent" />
      </span>
      <File className="w-3.5 h-3.5 text-[#686880] shrink-0" />
      <span className="ml-1 truncate">{node.name}</span>
    </div>
  )
}

export default function FileExplorer({ data, onFileClick }: { data: FileSystemNode[]; onFileClick: (path: string) => void }) {
  const [openFolders, setOpenFolders] = useState<Set<string>>(new Set())

  const toggleFolder = useCallback((path: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  // Auto-open root folders
  useEffect(() => {
    const roots = data.filter((n) => n.isDir).map((n) => n.path)
    setOpenFolders(new Set(roots))
  }, [data])

  return (
    <div className="text-[#a0b0c0] text-sm">
      {data.length === 0 ? (
        <div className="px-4 py-8 text-center text-[#555565] text-xs">
          No files yet. Create a file to get started.
        </div>
      ) : (
        data.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            depth={-1}
            onFileClick={onFileClick}
            openFolders={openFolders}
            toggleFolder={toggleFolder}
          />
        ))
      )}
    </div>
  )
}