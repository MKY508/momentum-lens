import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface PositionChartProps {
  data: {
    core: {
      weight: number
      value: number
      count: number
    }
    satellite: {
      weight: number
      value: number
      count: number
    }
    convertible: {
      weight: number
      value: number
      count: number
    }
    cash: {
      weight: number
      value: number
    }
  }
}

const COLORS = {
  core: '#3B82F6',       // blue
  satellite: '#8B5CF6',  // purple
  convertible: '#10B981', // green
  cash: '#6B7280',       // gray
}

const PositionChart: React.FC<PositionChartProps> = ({ data }) => {
  const chartData = [
    { name: 'Core资产', value: data.core.weight * 100, amount: data.core.value },
    { name: '卫星资产', value: data.satellite.weight * 100, amount: data.satellite.value },
    { name: '可转债', value: data.convertible.weight * 100, amount: data.convertible.value },
    { name: '现金', value: data.cash.weight * 100, amount: data.cash.value },
  ].filter(item => item.value > 0)

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div className="bg-white dark:bg-gray-800 p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <p className="font-semibold text-gray-900 dark:text-white">
            {payload[0].name}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            权重: {payload[0].value.toFixed(2)}%
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            金额: {formatCurrency(payload[0].payload.amount)}
          </p>
        </div>
      )
    }
    return null
  }

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, value }: any) => {
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    if (value < 5) return null // Don't show label for small slices

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        className="font-semibold"
      >
        {`${value.toFixed(1)}%`}
      </text>
    )
  }

  return (
    <div className="flex flex-col lg:flex-row items-center">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={
                  entry.name === 'Core资产' ? COLORS.core :
                  entry.name === '卫星资产' ? COLORS.satellite :
                  entry.name === '可转债' ? COLORS.convertible :
                  COLORS.cash
                }
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend and Stats */}
      <div className="mt-6 lg:mt-0 lg:ml-8 space-y-3">
        <div className="flex items-center space-x-3">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.core }}></div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">Core资产</span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {data.core.count}只 · {(data.core.weight * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.satellite }}></div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">卫星资产</span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {data.satellite.count}只 · {(data.satellite.weight * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.convertible }}></div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">可转债</span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {data.convertible.count}只 · {(data.convertible.weight * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.cash }}></div>
          <div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">现金</span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {(data.cash.weight * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PositionChart