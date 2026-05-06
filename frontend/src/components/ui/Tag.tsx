import React from 'react'

interface TagProps {
  status?: 'success' | 'error' | 'warning' | 'info'
  children: React.ReactNode
}

export const Tag: React.FC<TagProps> = ({ status = 'info', children }) => {
  const statusClasses = {
    success: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    warning: 'bg-amber-100 text-amber-800',
    info: 'bg-blue-100 text-blue-800',
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-label font-medium ${statusClasses[status]}`}
    >
      {children}
    </span>
  )
}
