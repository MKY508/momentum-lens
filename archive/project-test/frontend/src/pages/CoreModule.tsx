import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Shield, 
  RefreshCw, 
  TrendingUp, 
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Settings,
  PieChart
} from 'lucide-react'
import { portfolioAPI, dataAPI } from '../services/api'
import toast from 'react-hot-toast'

interface CoreAsset {
  code: string
  name: string
  current_weight: number
  target_weight: number
  current_value: number
  deviation: number
  action: 'buy' | 'sell' | 'hold'
  amount_to_adjust: number
}

const CoreModule: React.FC = () => {
  const [rebalanceThreshold, setRebalanceThreshold] = useState(0.02)
  const [showRebalanceModal, setShowRebalanceModal] = useState(false)

  // Fetch core positions
  const { data: positions, isLoading, refetch } = useQuery({
    queryKey: ['corePositions'],
    queryFn: async () => {
      const response = await portfolioAPI.getPositions()
      // Filter for core positions
      return response.data.filter((pos: any) => pos.module === 'core')
    },
  })

  // Fetch rebalance suggestions
  const { data: rebalanceSuggestions, refetch: refetchRebalance } = useQuery({
    queryKey: ['rebalanceSuggestions', rebalanceThreshold],
    queryFn: () => portfolioAPI.generateRebalance(rebalanceThreshold, true),
    enabled: false, // Manual trigger
  })

  const handleGenerateRebalance = async () => {
    try {
      await refetchRebalance()
      setShowRebalanceModal(true)
      toast.success('再平衡建议已生成')
    } catch (error) {
      toast.error('生成再平衡建议失败')
    }
  }

  const handleExecuteRebalance = async () => {
    try {
      await portfolioAPI.generateRebalance(rebalanceThreshold, false)
      toast.success('再平衡执行成功')
      setShowRebalanceModal(false)
      refetch()
    } catch (error) {
      toast.error('执行再平衡失败')
    }
  }

  const getDeviationColor = (deviation: number) => {
    const absDeviation = Math.abs(deviation)
    if (absDeviation < 0.02) return 'text-green-600'
    if (absDeviation < 0.05) return 'text-yellow-600'
    return 'text-red-600'
  }

  const calculateTotalValue = () => {
    if (!positions) return 0
    return positions.reduce((sum: number, pos: any) => sum + pos.current_value, 0)
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(num)
  }

  const formatPercent = (num: number) => {
    return `${(num * 100).toFixed(2)}%`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Shield className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Core 核心资产</h1>
            <p className="text-gray-500">长期持有的核心资产配置</p>
          </div>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>刷新</span>
          </button>
          <button
            onClick={handleGenerateRebalance}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
          >
            <PieChart className="w-4 h-4" />
            <span>生成再平衡</span>
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">总价值</div>
          <div className="text-2xl font-bold text-gray-900">
            ¥{formatNumber(calculateTotalValue())}
          </div>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">持仓数量</div>
          <div className="text-2xl font-bold text-gray-900">
            {positions?.length || 0}
          </div>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">平均偏离度</div>
          <div className="text-2xl font-bold text-gray-900">
            {positions && positions.length > 0
              ? formatPercent(
                  positions.reduce((sum: number, pos: any) => 
                    sum + Math.abs(pos.current_weight - pos.target_weight), 0
                  ) / positions.length
                )
              : '0.00%'}
          </div>
        </div>
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="text-sm text-gray-500 mb-1">再平衡阈值</div>
          <div className="flex items-center space-x-2">
            <input
              type="number"
              value={rebalanceThreshold * 100}
              onChange={(e) => setRebalanceThreshold(Number(e.target.value) / 100)}
              className="w-20 px-2 py-1 border rounded"
              step="0.5"
              min="0.5"
              max="10"
            />
            <span className="text-gray-600">%</span>
          </div>
        </div>
      </div>

      {/* Core Assets Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">核心资产配置</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  资产
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  当前权重
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  目标权重
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  偏离度
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  当前价值
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  建议操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {positions?.map((asset: any) => (
                <tr key={asset.code} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {asset.name}
                      </div>
                      <div className="text-xs text-gray-500">{asset.code}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                    {formatPercent(asset.current_weight)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                    {formatPercent(asset.target_weight)}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-right text-sm font-medium ${
                    getDeviationColor(asset.current_weight - asset.target_weight)
                  }`}>
                    {asset.current_weight > asset.target_weight ? '+' : ''}
                    {formatPercent(asset.current_weight - asset.target_weight)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                    ¥{formatNumber(asset.current_value)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    {Math.abs(asset.current_weight - asset.target_weight) > rebalanceThreshold ? (
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        asset.current_weight > asset.target_weight
                          ? 'bg-red-100 text-red-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {asset.current_weight > asset.target_weight ? (
                          <>
                            <ArrowDownRight className="w-3 h-3 mr-1" />
                            卖出
                          </>
                        ) : (
                          <>
                            <ArrowUpRight className="w-3 h-3 mr-1" />
                            买入
                          </>
                        )}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">持有</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Weight Distribution Chart */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">权重分布</h2>
        <div className="space-y-4">
          {positions?.map((asset: any) => (
            <div key={asset.code}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">{asset.name}</span>
                <span className="text-gray-900 font-medium">
                  {formatPercent(asset.current_weight)}
                </span>
              </div>
              <div className="relative">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${asset.current_weight * 100}%` }}
                  />
                </div>
                <div 
                  className="absolute top-0 w-0.5 h-4 bg-red-500 -mt-1"
                  style={{ left: `${asset.target_weight * 100}%` }}
                  title={`目标: ${formatPercent(asset.target_weight)}`}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Rebalance Modal */}
      {showRebalanceModal && rebalanceSuggestions && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">再平衡建议</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {rebalanceSuggestions.data.orders?.map((order: any, index: number) => (
                <div key={index} className="border rounded p-3">
                  <div className="flex justify-between">
                    <span className="font-medium">{order.name} ({order.code})</span>
                    <span className={`font-bold ${
                      order.action === 'buy' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {order.action === 'buy' ? '买入' : '卖出'} 
                      {order.quantity}股
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    金额: ¥{formatNumber(order.amount)}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowRebalanceModal(false)}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                取消
              </button>
              <button
                onClick={handleExecuteRebalance}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                执行再平衡
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CoreModule