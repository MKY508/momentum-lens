import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts'
import { 
  TrendingUp,
  TrendingDown,
  Activity,
  Award,
  Target,
  AlertTriangle,
  RefreshCw,
  Calendar,
  Download
} from 'lucide-react'
import { portfolioAPI } from '../services/api'
import toast from 'react-hot-toast'

interface PerformanceData {
  date: string
  value: number
  benchmark: number
  drawdown: number
}

interface TradeStats {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  sharpe_ratio: number
  max_drawdown: number
  recovery_days: number
}

interface MonthlyReturn {
  month: string
  return: number
  benchmark_return: number
  alpha: number
}

const KPILog: React.FC = () => {
  const [dateRange, setDateRange] = useState('1M')
  const [selectedMetric, setSelectedMetric] = useState<'return' | 'drawdown'>('return')

  // Mock data for demonstration - replace with actual API calls
  const performanceData: PerformanceData[] = generateMockPerformanceData()
  const tradeStats: TradeStats = generateMockTradeStats()
  const monthlyReturns: MonthlyReturn[] = generateMockMonthlyReturns()

  function generateMockPerformanceData(): PerformanceData[] {
    const data = []
    const startDate = new Date()
    startDate.setMonth(startDate.getMonth() - 12)
    
    let value = 100000
    let benchmark = 100000
    
    for (let i = 0; i < 365; i++) {
      const date = new Date(startDate)
      date.setDate(date.getDate() + i)
      
      // Simulate random walk with slight upward bias
      const dailyReturn = (Math.random() - 0.48) * 0.02
      const benchmarkReturn = (Math.random() - 0.49) * 0.015
      
      value *= (1 + dailyReturn)
      benchmark *= (1 + benchmarkReturn)
      
      const peak = Math.max(...data.map(d => d.value), value)
      const drawdown = ((peak - value) / peak) * 100
      
      data.push({
        date: date.toISOString().split('T')[0],
        value: Math.round(value),
        benchmark: Math.round(benchmark),
        drawdown: -drawdown
      })
    }
    
    return data
  }

  function generateMockTradeStats(): TradeStats {
    return {
      total_trades: 156,
      winning_trades: 92,
      losing_trades: 64,
      win_rate: 58.97,
      avg_win: 2.34,
      avg_loss: -1.87,
      profit_factor: 1.82,
      sharpe_ratio: 1.45,
      max_drawdown: -12.3,
      recovery_days: 23
    }
  }

  function generateMockMonthlyReturns(): MonthlyReturn[] {
    const months = [
      '2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06',
      '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12'
    ]
    
    return months.map(month => {
      const ret = (Math.random() - 0.4) * 10
      const benchmarkRet = (Math.random() - 0.45) * 8
      return {
        month,
        return: Number(ret.toFixed(2)),
        benchmark_return: Number(benchmarkRet.toFixed(2)),
        alpha: Number((ret - benchmarkRet).toFixed(2))
      }
    })
  }

  const getFilteredData = () => {
    if (!performanceData) return []
    
    const now = new Date()
    let startDate = new Date()
    
    switch (dateRange) {
      case '1M':
        startDate.setMonth(now.getMonth() - 1)
        break
      case '3M':
        startDate.setMonth(now.getMonth() - 3)
        break
      case '6M':
        startDate.setMonth(now.getMonth() - 6)
        break
      case '1Y':
        startDate.setFullYear(now.getFullYear() - 1)
        break
      case 'YTD':
        startDate = new Date(now.getFullYear(), 0, 1)
        break
      default:
        return performanceData
    }
    
    return performanceData.filter(d => new Date(d.date) >= startDate)
  }

  const calculateTotalReturn = () => {
    const data = getFilteredData()
    if (data.length < 2) return 0
    
    const startValue = data[0].value
    const endValue = data[data.length - 1].value
    return ((endValue - startValue) / startValue * 100).toFixed(2)
  }

  const calculateBenchmarkReturn = () => {
    const data = getFilteredData()
    if (data.length < 2) return 0
    
    const startValue = data[0].benchmark
    const endValue = data[data.length - 1].benchmark
    return ((endValue - startValue) / startValue * 100).toFixed(2)
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num)
  }

  const formatPercent = (num: number) => `${num.toFixed(2)}%`

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Award className="w-8 h-8 text-purple-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">KPI 日志</h1>
            <p className="text-gray-500">策略表现与风险分析</p>
          </div>
        </div>
        <div className="flex space-x-3">
          <button
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>导出报告</span>
          </button>
          <button
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>刷新</span>
          </button>
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            {['1M', '3M', '6M', 'YTD', '1Y', 'ALL'].map(range => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className={`px-3 py-1 rounded ${
                  dateRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          <div className="flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-600">
              {new Date().toLocaleDateString('zh-CN')}
            </span>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">总收益率</span>
            <TrendingUp className="w-4 h-4 text-green-500" />
          </div>
          <div className={`text-2xl font-bold ${
            Number(calculateTotalReturn()) >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {calculateTotalReturn()}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            基准: {calculateBenchmarkReturn()}%
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">胜率</span>
            <Target className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {tradeStats.win_rate}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {tradeStats.winning_trades}W / {tradeStats.losing_trades}L
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">夏普比率</span>
            <Activity className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {tradeStats.sharpe_ratio}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            风险调整后收益
          </div>
        </div>

        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">最大回撤</span>
            <AlertTriangle className="w-4 h-4 text-orange-500" />
          </div>
          <div className="text-2xl font-bold text-orange-600">
            {tradeStats.max_drawdown}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            恢复天数: {tradeStats.recovery_days}
          </div>
        </div>
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">收益曲线</h2>
          <div className="flex space-x-2">
            <button
              onClick={() => setSelectedMetric('return')}
              className={`px-3 py-1 text-sm rounded ${
                selectedMetric === 'return'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              收益率
            </button>
            <button
              onClick={() => setSelectedMetric('drawdown')}
              className={`px-3 py-1 text-sm rounded ${
                selectedMetric === 'drawdown'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              回撤
            </button>
          </div>
        </div>
        
        <ResponsiveContainer width="100%" height={300}>
          {selectedMetric === 'return' ? (
            <LineChart data={getFilteredData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(date) => new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
              />
              <YAxis />
              <Tooltip 
                formatter={(value: number) => `¥${formatNumber(value)}`}
                labelFormatter={(date) => new Date(date).toLocaleDateString('zh-CN')}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#3B82F6" 
                strokeWidth={2}
                dot={false}
                name="策略"
              />
              <Line 
                type="monotone" 
                dataKey="benchmark" 
                stroke="#9CA3AF" 
                strokeWidth={2}
                dot={false}
                name="基准"
              />
            </LineChart>
          ) : (
            <AreaChart data={getFilteredData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(date) => new Date(date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
              />
              <YAxis />
              <Tooltip 
                formatter={(value: number) => `${formatPercent(value)}`}
                labelFormatter={(date) => new Date(date).toLocaleDateString('zh-CN')}
              />
              <Legend />
              <Area 
                type="monotone" 
                dataKey="drawdown" 
                stroke="#EF4444" 
                fill="#FEE2E2"
                name="回撤"
              />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Monthly Returns */}
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">月度收益</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={monthlyReturns}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="month" 
              tickFormatter={(month) => month.slice(5)}
            />
            <YAxis />
            <Tooltip formatter={(value: number) => `${formatPercent(value)}`} />
            <Legend />
            <Bar dataKey="return" fill="#3B82F6" name="策略收益" />
            <Bar dataKey="benchmark_return" fill="#9CA3AF" name="基准收益" />
            <Bar dataKey="alpha" fill="#10B981" name="超额收益" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Trade Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">交易统计</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">总交易次数</span>
              <span className="font-medium">{tradeStats.total_trades}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">盈利次数</span>
              <span className="font-medium text-green-600">{tradeStats.winning_trades}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">亏损次数</span>
              <span className="font-medium text-red-600">{tradeStats.losing_trades}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">平均盈利</span>
              <span className="font-medium text-green-600">+{formatPercent(tradeStats.avg_win)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">平均亏损</span>
              <span className="font-medium text-red-600">{formatPercent(tradeStats.avg_loss)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">盈亏比</span>
              <span className="font-medium">{tradeStats.profit_factor}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">风险指标</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">夏普比率</span>
              <span className="font-medium">{tradeStats.sharpe_ratio}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">最大回撤</span>
              <span className="font-medium text-orange-600">{formatPercent(tradeStats.max_drawdown)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">回撤恢复天数</span>
              <span className="font-medium">{tradeStats.recovery_days} 天</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">波动率 (年化)</span>
              <span className="font-medium">15.23%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Beta</span>
              <span className="font-medium">0.86</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Alpha (年化)</span>
              <span className="font-medium text-green-600">+3.45%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default KPILog