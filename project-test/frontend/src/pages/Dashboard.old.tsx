import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  AlertTriangle,
  DollarSign,
  PieChart,
  RefreshCw,
  Download
} from 'lucide-react'
import { marketAPI, portfolioAPI, decisionAPI, exportAPI } from '../services/api'
import MarketStatus from '../components/MarketStatus'
import PositionChart from '../components/PositionChart'
import toast from 'react-hot-toast'

const Dashboard: React.FC = () => {
  // Fetch market environment
  const { data: marketEnv, isLoading: marketLoading, refetch: refetchMarket } = useQuery({
    queryKey: ['marketEnvironment'],
    queryFn: () => marketAPI.getEnvironment(),
  })

  // Fetch portfolio summary
  const { data: portfolio, isLoading: portfolioLoading, refetch: refetchPortfolio } = useQuery({
    queryKey: ['portfolioSummary'],
    queryFn: () => portfolioAPI.getSummary(),
  })

  // Fetch risk warnings
  const { data: risks, isLoading: risksLoading } = useQuery({
    queryKey: ['portfolioRisks'],
    queryFn: () => portfolioAPI.checkRisks(),
  })

  const handleGenerateDecisions = async () => {
    try {
      const result = await decisionAPI.generate()
      toast.success(`生成了${result.data.summary.total_decisions}个决策`)
      refetchMarket()
      refetchPortfolio()
    } catch (error) {
      toast.error('生成决策失败')
    }
  }

  const handleExportOrders = () => {
    exportAPI.downloadOrdersCSV()
    toast.success('开始下载订单文件')
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            决策控制台
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            实时监控市场环境和投资组合状态
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={handleGenerateDecisions}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <RefreshCw size={18} />
            <span>生成决策</span>
          </button>
          <button
            onClick={handleExportOrders}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Download size={18} />
            <span>导出订单</span>
          </button>
        </div>
      </div>

      {/* Market Environment Card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            市场环境
          </h3>
          {marketLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
            </div>
          ) : marketEnv ? (
            <MarketStatus data={marketEnv.data} />
          ) : null}
        </div>
      </div>

      {/* Portfolio Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Value Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">总市值</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {portfolio ? formatCurrency(portfolio.data.overview.total_value) : '---'}
              </p>
            </div>
            <DollarSign className="text-blue-500" size={32} />
          </div>
        </div>

        {/* P&L Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">总收益</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {portfolio ? formatCurrency(portfolio.data.overview.total_pnl) : '---'}
              </p>
              <p className={`text-sm mt-1 ${
                portfolio?.data.overview.total_pnl_pct >= 0 
                  ? 'text-green-600' 
                  : 'text-red-600'
              }`}>
                {portfolio ? formatPercent(portfolio.data.overview.total_pnl_pct) : '---'}
              </p>
            </div>
            {portfolio?.data.overview.total_pnl_pct >= 0 ? (
              <TrendingUp className="text-green-500" size={32} />
            ) : (
              <TrendingDown className="text-red-500" size={32} />
            )}
          </div>
        </div>

        {/* Positions Count Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">持仓数量</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {portfolio?.data.overview.positions_count || 0}
              </p>
            </div>
            <PieChart className="text-purple-500" size={32} />
          </div>
        </div>

        {/* Risk Warnings Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">风险警告</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {risks?.data.count || 0}
              </p>
            </div>
            <AlertTriangle className={`${
              risks?.data.count > 0 ? 'text-orange-500' : 'text-gray-400'
            }`} size={32} />
          </div>
        </div>
      </div>

      {/* Portfolio Allocation */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            资产配置
          </h3>
          {portfolioLoading ? (
            <div className="animate-pulse h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
          ) : portfolio ? (
            <PositionChart data={portfolio.data.allocation} />
          ) : null}
        </div>
      </div>

      {/* Risk Warnings List */}
      {risks?.data.warnings && risks.data.warnings.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-4">
              风险提示
            </h3>
            <div className="space-y-3">
              {risks.data.warnings.map((warning: any, index: number) => (
                <div 
                  key={index}
                  className="flex items-start space-x-3 p-3 bg-white dark:bg-gray-800 rounded-lg"
                >
                  <AlertTriangle className="text-orange-500 mt-0.5" size={18} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {warning.message}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      类型: {warning.type}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top Positions */}
      {portfolio?.data.top_positions && portfolio.data.top_positions.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              主要持仓
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      代码
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      名称
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      模块
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      权重
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      收益率
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {portfolio.data.top_positions.map((position: any) => (
                    <tr key={position.code}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                        {position.code}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                        {position.name}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                          position.module === 'core' 
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
                            : position.module === 'satellite'
                            ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400'
                            : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        }`}>
                          {position.module}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-white">
                        {formatPercent(position.weight)}
                      </td>
                      <td className={`px-4 py-3 text-sm text-right font-medium ${
                        position.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercent(position.pnl_pct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard