import React from 'react'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean
  children: React.ReactNode
}

export const Card: React.FC<CardProps> = ({
  hoverable = false,
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`
        bg-surface-card rounded-lg shadow-elevated p-5
        transition-all duration-250
        ${hoverable ? 'hover:shadow-elevated hover:-translate-y-0.5 cursor-pointer' : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  )
}
