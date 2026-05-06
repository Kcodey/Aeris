import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'text'
  size?: 'sm' | 'md' | 'lg'
  children: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...props
}) => {
  const baseClasses =
    'inline-flex items-center justify-center font-medium transition-all duration-200 ease-out rounded-sm focus:outline-none focus:ring-2 focus:ring-brand/20'

  const variantClasses = {
    primary:
      'bg-brand text-white hover:bg-brand-dark hover:-translate-y-px hover:shadow-glow active:translate-y-0',
    secondary:
      'bg-surface-page text-content-primary border border-border hover:bg-[#f5f5f4] hover:border-[#d6d3d1]',
    text: 'bg-transparent text-brand hover:bg-brand-light',
  }

  const sizeClasses = {
    sm: 'h-8 px-3 text-caption',
    md: 'h-9 px-4 text-body',
    lg: 'h-11 px-6 text-body',
  }

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
