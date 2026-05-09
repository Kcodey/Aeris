import React from 'react'

interface StatCardProps {
  label: string
  value: string | number
  suffix?: string
  trend?: {
    value: number
    isPositive: boolean
    label: string
  }
  highlight?: boolean
  onClick?: () => void
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  suffix,
  trend,
  highlight = false,
  onClick,
}) => {
  const clickableClass = onClick
    ? 'cursor-pointer hover:shadow-lg active:scale-[0.98]'
    : ''

  return (
    <div
      onClick={onClick}
      className={`bg-surface-card rounded-2xl shadow-elevated p-5 transition-all duration-250 hover:-translate-y-0.5 ${clickableClass}`}
    >
      <div className="text-label text-content-secondary mb-2">{label}</div>
      <div className={`text-display ${highlight ? 'text-brand' : 'text-content-primary'}`}>
        {value}
        {suffix && <span className="text-lg font-normal text-content-secondary ml-1">{suffix}</span>}
      </div>
      {trend && (
        <div className={`text-label mt-2 ${trend.isPositive ? 'text-red-600' : 'text-green-600'}`}>
          {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}% {trend.label}
        </div>
      )}
    </div>
  )
}
