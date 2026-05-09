import React from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  date: string
  tokens: number
}

interface TokenTrendChartProps {
  data: DataPoint[]
}

export const TokenTrendChart: React.FC<TokenTrendChartProps> = ({ data }) => {
  return (
    <div className="bg-surface-card rounded-2xl shadow-elevated p-5">
      <div className="text-heading font-semibold text-content-primary mb-4">Token 用量趋势</div>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#d97706" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#d97706" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#a8a29e' }}
            axisLine={{ stroke: '#e7e5e4' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#a8a29e' }}
            axisLine={false}
            tickLine={false}
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
          <Area
            type="monotone"
            dataKey="tokens"
            stroke="#d97706"
            strokeWidth={2.5}
            fill="url(#tokenGradient)"
            dot={{ fill: '#fff', stroke: '#d97706', strokeWidth: 2, r: 4 }}
            activeDot={{ fill: '#d97706', stroke: '#fff', strokeWidth: 2, r: 6 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
