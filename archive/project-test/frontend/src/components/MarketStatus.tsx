import React from 'react'
import { Activity, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

interface MarketStatusProps {
  data: {
    state: string
    ma200_ratio: number
    atr20: number
    chop: number
    vix_level: string
    metadata?: any
  }
}

const MarketStatus: React.FC<MarketStatusProps> = ({ data }) => {
  const getStateColor = (state: string) => {
    switch (state) {
      case 'bull':
        return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400'
      case 'bear':
        return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400'
      case 'sideways':
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400'
      default:
        return 'text-gray-600 bg-gray-100 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'bull':
        return <TrendingUp size={20} />
      case 'bear':
        return <TrendingDown size={20} />
      case 'sideways':
        return <Activity size={20} />
      default:
        return <AlertCircle size={20} />
    }
  }

  const getStateLabel = (state: string) => {
    switch (state) {
      case 'bull':
        return '牛市'
      case 'bear':
        return '熊市'
      case 'sideways':
        return '震荡市'
      default:
        return '不确定'
    }
  }

  const getVixColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'text-green-600'
      case 'medium':
        return 'text-yellow-600'
      case 'high':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getMA200Status = (ratio: number) => {
    if (ratio > 1.05) return { label: '强势站上', color: 'text-green-600' }
    if (ratio > 1.0) return { label: '弱势站上', color: 'text-green-400' }
    if (ratio > 0.95) return { label: '弱势跌破', color: 'text-red-400' }
    return { label: '强势跌破', color: 'text-red-600' }
  }

  const ma200Status = getMA200Status(data.ma200_ratio)

  return (
    <div className="space-y-4">
      {/* Market State */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">市场状态</span>
        <div className={clsx('flex items-center space-x-2 px-3 py-1 rounded-full', getStateColor(data.state))}>
          {getStateIcon(data.state)}
          <span className="font-semibold">{getStateLabel(data.state)}</span>
        </div>
      </div>

      {/* MA200 Status */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">年线状态</span>
        <div className="text-right">
          <span className={clsx('font-semibold', ma200Status.color)}>
            {ma200Status.label}
          </span>
          <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
            ({(data.ma200_ratio * 100).toFixed(2)}%)
          </span>
        </div>
      </div>

      {/* ATR20 */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">ATR20波动率</span>
        <span className="font-semibold text-gray-900 dark:text-white">
          {(data.atr20 * 100).toFixed(2)}%
        </span>
      </div>

      {/* CHOP */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">CHOP震荡指数</span>
        <div className="flex items-center space-x-2">
          <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${Math.min(data.chop, 100)}%` }}
            />
          </div>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {data.chop.toFixed(1)}
          </span>
        </div>
      </div>

      {/* VIX Level */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500 dark:text-gray-400">VIX级别</span>
        <span className={clsx('font-semibold uppercase', getVixColor(data.vix_level))}>
          {data.vix_level === 'low' ? '低' : data.vix_level === 'medium' ? '中' : '高'}
        </span>
      </div>

      {/* Environment Light */}
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
        <div className="flex items-center justify-center space-x-4">
          <div className="text-center">
            <div className={clsx(
              'w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center',
              data.state === 'bull' ? 'bg-green-500 animate-pulse' :
              data.state === 'bear' ? 'bg-red-500 animate-pulse' :
              data.state === 'sideways' ? 'bg-yellow-500 animate-pulse' :
              'bg-gray-500'
            )}>
              {getStateIcon(data.state)}
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400">环境灯</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MarketStatus