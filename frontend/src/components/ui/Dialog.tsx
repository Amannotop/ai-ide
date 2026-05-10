// Dialog components
import * as React from 'react'

interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps {
  children: React.ReactNode
  className?: string
}

interface DialogHeaderProps {
  children: React.ReactNode
  className?: string
}

interface DialogTitleProps {
  children: React.ReactNode
}

export function Dialog({ children }: DialogProps) {
  return <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">{children}</div>
}

export function DialogContent({ children, className = '' }: DialogContentProps) {
  return (
    <div className={`bg-[#18181e] border border-[#2a2a35] rounded-lg shadow-xl ${className}`}>
      {children}
    </div>
  )
}

export function DialogHeader({ children, className = '' }: DialogHeaderProps) {
  return <div className={`px-6 py-4 border-b border-[#2a2a35] ${className}`}>{children}</div>
}

export function DialogTitle({ children }: DialogTitleProps) {
  return <h2 className="text-sm font-semibold text-[#c8c8d4]">{children}</h2>
}