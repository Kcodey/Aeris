import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface LatencyData {
  range: string
  count: number
}

interface LatencyBarChartProps {
  data: LatencyData[]
}

export const LatencyBarChart: React.FC<LatencyBarChartProps> = ({ data }) => {
  return (
    <div className="bg-surface-card rounded-2xl shadow-elevated p-5">
      <div className="text-heading font-semibold text-content-primary mb-4">延迟分布</div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="range"
            tick={{ fontSize: 12, fill: '#a8a29e' }}
            axisLine={{ stroke: '#e7e5e4' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#a8a29e' }}
            axisLine={false}
            tickLine={false}
            width={35}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(255,255,255,0.9)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255,255,255,0.6)',
              borderRadius: '12px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
              fontSize: '12px',
            }}
          />
          <Bar
            dataKey="count"
            fill="#d97706"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
