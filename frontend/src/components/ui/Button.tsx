// Button component
import { type ReactNode } from 'react'

interface Props {
  variant?: 'default' | 'ghost'
  size?: 'default' | 'sm' | 'iconSm' | 'icon'
  children: ReactNode
  className?: string
  onClick?: () => void
  title?: string
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}

export function Button({
  variant = 'default',
  size = 'default',
  children,
  className = '',
  onClick,
  title,
  type = 'button',
  disabled = false,
}: Props) {
  const variants = {
    default: 'bg-[#2a2a35] hover:bg-[#3a3a45] text-[#c8c8d4]',
    ghost: 'hover:bg-[#2a2a35] text-[#8888a0] hover:text-[#c8c8d4]',
  }

  const sizes = {
    default: 'px-3 py-1.5 text-sm',
    sm: 'px-2 py-1 text-xs',
    iconSm: 'w-6 h-6 p-0',
    icon: 'w-8 h-8 p-0',
  }

  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center rounded transition-colors disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </button>
  )
}