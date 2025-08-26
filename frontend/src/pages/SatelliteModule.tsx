import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Satellite, 
  TrendingUp, 
  RefreshCw, 
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { momentumAPI, decisionAPI } from '../services/api'
import toast from 'react-hot-toast'

const SatelliteModule: React.FC = () => {
  const [selectedCount, setSelectedCount] = useState(2)

  // Fetch momentum ranking
  const { data: ranking, isLoading, refetch } = useQuery({
    queryKey: ['momentumRanking'],
    queryFn: () => momentumAPI.getRanking(20),
  })

  // Fetch satellite selections
  const { data: selections, refetch: refetchSelections } = useQuery({
    queryKey: ['satelliteSelections', selectedCount],
    queryFn: () => decisionAPI.getSatelliteSelections(selectedCount),
  })

  const handleGenerateSelections = async () => {
    try {
      await refetchSelections()
      toast.success('卫星ETF选择已更新')
    } catch (error) {
      toast.error('生成选择失败')
    }
  }

  const getScoreColor = (score: number) => {
    if (score > 0.15) return 'text-green-600'
    if (score > 0.05) return 'text-blue-600'
    if (score > 0) return 'text-gray-600'
    return 'text-red-600'
  }

  const getMA200Badge = (state: string) => {
    const badges: Record<string, { color: string; label: string }> = {
      above_strong: { color: 'bg-green-100 text-green-800', label: '强势站上' },
      above_weak: { color: 'bg-blue-100 text-blue-800', label: '弱势站上' },
      below_weak: { color: 'bg-orange-100 text-orange-800', label: '弱势跌破' },
      below_strong: { color: 'bg-red-100 text-red-800', label: '强势跌破' },
    }
    return badges[state] || { color: 'bg-gray-100 text-gray-800', label: '未知' }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
            <Satellite className="text-purple-600" />
            <span>卫星模块</span>
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            基于动量策略的行业主题ETF选择
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
        >
          <RefreshCw size={18} />
          <span>刷新数据</span>
        </button>
      </div>

      {/* Selection Control */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              卫星ETF选择
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              选择前{selectedCount}个高动量ETF
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <select
              value={selectedCount}
              onChange={(e) => setSelectedCount(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value={1}>1只</option>
              <option value={2}>2只</option>
              <option value={3}>3只</option>
              <option value={4}>4只</option>
            </select>
            <button
              onClick={handleGenerateSelections}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              生成选择
            </button>
          </div>
        </div>

        {/* Selected ETFs */}
        {selections?.data.decisions && selections.data.decisions.length > 0 && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {selections.data.decisions.map((decision: any) => (
              <div
                key={decision.code}
                className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {decision.code} - {decision.name}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      目标权重: {(decision.target_weight * 100).toFixed(1)}%
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {decision.reason}
                    </p>
                  </div>
                  <TrendingUp className="text-purple-600" size={20} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Momentum Ranking Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            动量排名榜
          </h3>
          
          {isLoading ? (
            <div className="animate-pulse space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
          ) : ranking?.data.ranking ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      排名
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      代码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      名称
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      3月动量
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      6月动量
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      综合得分
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      年线状态
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      成交量比
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {ranking.data.ranking.map((item: any) => {
                    const ma200Badge = getMA200Badge(item.ma200_state)
                    return (
                      <tr key={item.code} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                          {item.rank}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                          {item.code}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                          {item.name}
                        </td>
                        <td className={`px-4 py-3 text-sm text-right font-medium ${getScoreColor(item.r3m)}`}>
                          <div className="flex items-center justify-end space-x-1">
                            {item.r3m > 0 ? (
                              <ArrowUpRight size={16} />
                            ) : (
                              <ArrowDownRight size={16} />
                            )}
                            <span>{(item.r3m * 100).toFixed(2)}%</span>
                          </div>
                        </td>
                        <td className={`px-4 py-3 text-sm text-right font-medium ${getScoreColor(item.r6m)}`}>
                          <div className="flex items-center justify-end space-x-1">
                            {item.r6m > 0 ? (
                              <ArrowUpRight size={16} />
                            ) : (
                              <ArrowDownRight size={16} />
                            )}
                            <span>{(item.r6m * 100).toFixed(2)}%</span>
                          </div>
                        </td>
                        <td className={`px-4 py-3 text-sm text-right font-bold ${getScoreColor(item.total_score)}`}>
                          {(item.total_score * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-sm text-center">
                          <span className={`inline-flex px-2 py-1 text-xs rounded-full ${ma200Badge.color}`}>
                            {ma200Badge.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-white">
                          {item.volume_ratio?.toFixed(2) || '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">暂无数据</p>
          )}
        </div>
      </div>

      {/* Strategy Rules */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-6">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4">
          卫星策略规则
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">动量权重:</span> 3月(60%) + 6月(40%)
            </p>
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">最小成交额:</span> 5000万
            </p>
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">相关性上限:</span> 0.8
            </p>
          </div>
          <div className="space-y-2">
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">最小持有期:</span> 2周
            </p>
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">止损线:</span> -12%
            </p>
            <p className="text-blue-800 dark:text-blue-200">
              <span className="font-medium">缓冲区:</span> 3%
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SatelliteModule