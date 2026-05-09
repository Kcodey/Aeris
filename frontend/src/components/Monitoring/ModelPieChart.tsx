import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface ModelData {
  name: string
  value: number
}

interface ModelPieChartProps {
  data: ModelData[]
}

const COLORS = ['#d97706', '#fbbf24', '#fde68a', '#e7e5e4']

export const ModelPieChart: React.FC<ModelPieChartProps> = ({ data }) => {
  return (
    <div className="bg-surface-card rounded-2xl shadow-elevated p-5">
      <div className="text-heading font-semibold text-content-primary mb-4">模型用量占比</div>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
            stroke="none"
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
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
          <Legend
            verticalAlign="bottom"
            align="center"
            layout="horizontal"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: '12px', color: '#57534e' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
