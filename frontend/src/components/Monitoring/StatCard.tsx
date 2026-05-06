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
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  suffix,
  trend,
  highlight = false,
}) => {
  return (
    <div className="bg-surface-card rounded-2xl border border-border shadow-subtle p-5 transition-all duration-250 hover:shadow-elevated hover:-translate-y-0.5 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-brand/20" />
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
