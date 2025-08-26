import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  TrendingUp, 
  RefreshCw, 
  Grid3X3,
  DollarSign,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Filter,
  ArrowUpDown
} from 'lucide-react'
import { dataAPI } from '../services/api'
import toast from 'react-hot-toast'

interface ConvertibleBond {
  code: string
  name: string
  price: number
  premium_rate: number
  conversion_value: number
  remaining_years: number
  rating: string
  ytm: number // Yield to Maturity
  score: number
  selected: boolean
}

interface GridStrategy {
  bond_code: string
  lower_price: number
  upper_price: number
  grid_count: number
  amount_per_grid: number
}

const ConvertibleBond: React.FC = () => {
  const [selectedBonds, setSelectedBonds] = useState<Set<string>>(new Set())
  const [gridStrategy, setGridStrategy] = useState<GridStrategy>({
    bond_code: '',
    lower_price: 100,
    upper_price: 130,
    grid_count: 5,
    amount_per_grid: 10000
  })
  const [filterCriteria, setFilterCriteria] = useState({
    maxPremium: 20,
    minRating: 'AA',
    maxRemainingYears: 5
  })
  const [sortBy, setSortBy] = useState<'score' | 'premium' | 'ytm'>('score')

  // Fetch convertible bonds
  const { data: bonds, isLoading, refetch } = useQuery({
    queryKey: ['convertibleBonds'],
    queryFn: async () => {
      const response = await dataAPI.getConvertibles()
      // Calculate scores for each bond
      const bondsWithScore = response.data.map((bond: any) => ({
        ...bond,
        score: calculateBondScore(bond)
      }))
      return bondsWithScore
    },
  })

  const calculateBondScore = (bond: any): number => {
    let score = 100
    
    // Premium rate scoring (lower is better)
    if (bond.premium_rate < 0) score += 20
    else if (bond.premium_rate < 5) score += 15
    else if (bond.premium_rate < 10) score += 10
    else if (bond.premium_rate < 20) score += 5
    else score -= 10
    
    // YTM scoring (higher is better)
    if (bond.ytm > 5) score += 15
    else if (bond.ytm > 3) score += 10
    else if (bond.ytm > 1) score += 5
    
    // Rating scoring
    const ratingScores: Record<string, number> = {
      'AAA': 15,
      'AA+': 12,
      'AA': 10,
      'AA-': 8,
      'A+': 5,
      'A': 3
    }
    score += ratingScores[bond.rating] || 0
    
    // Remaining years scoring (moderate is better)
    if (bond.remaining_years >= 2 && bond.remaining_years <= 4) score += 10
    else if (bond.remaining_years >= 1 && bond.remaining_years <= 5) score += 5
    
    // Price scoring (closer to par is better)
    const priceDeviation = Math.abs(bond.price - 100)
    if (priceDeviation < 5) score += 10
    else if (priceDeviation < 10) score += 5
    
    return score
  }

  const handleSelectBond = (code: string) => {
    const newSelected = new Set(selectedBonds)
    if (newSelected.has(code)) {
      newSelected.delete(code)
    } else {
      newSelected.add(code)
    }
    setSelectedBonds(newSelected)
  }

  const handleSetupGrid = (bond: ConvertibleBond) => {
    setGridStrategy({
      bond_code: bond.code,
      lower_price: Math.floor(bond.price * 0.9),
      upper_price: Math.ceil(bond.price * 1.1),
      grid_count: 5,
      amount_per_grid: 10000
    })
    toast.success(`设置${bond.name}的网格策略`)
  }

  const calculateGridLevels = () => {
    if (!gridStrategy.bond_code) return []
    
    const priceStep = (gridStrategy.upper_price - gridStrategy.lower_price) / gridStrategy.grid_count
    const levels = []
    
    for (let i = 0; i <= gridStrategy.grid_count; i++) {
      levels.push({
        price: gridStrategy.lower_price + priceStep * i,
        amount: gridStrategy.amount_per_grid
      })
    }
    
    return levels
  }

  const filteredAndSortedBonds = bonds?.filter((bond: ConvertibleBond) => {
    if (bond.premium_rate > filterCriteria.maxPremium) return false
    if (bond.remaining_years > filterCriteria.maxRemainingYears) return false
    // Add more filter conditions as needed
    return true
  }).sort((a: ConvertibleBond, b: ConvertibleBond) => {
    switch (sortBy) {
      case 'score':
        return b.score - a.score
      case 'premium':
        return a.premium_rate - b.premium_rate
      case 'ytm':
        return b.ytm - a.ytm
      default:
        return 0
    }
  })

  const getScoreBadge = (score: number) => {
    if (score >= 130) return { color: 'bg-green-100 text-green-800', label: '优秀' }
    if (score >= 110) return { color: 'bg-blue-100 text-blue-800', label: '良好' }
    if (score >= 90) return { color: 'bg-yellow-100 text-yellow-800', label: '一般' }
    return { color: 'bg-red-100 text-red-800', label: '较差' }
  }

  const formatPercent = (num: number) => `${num.toFixed(2)}%`
  const formatNumber = (num: number) => num.toFixed(2)

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
          <DollarSign className="w-8 h-8 text-green-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">可转债模块</h1>
            <p className="text-gray-500">可转债评分与网格策略</p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>刷新</span>
        </button>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <div className="flex items-center space-x-2 mb-3">
          <Filter className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-700">筛选条件</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">最大溢价率</label>
            <input
              type="number"
              value={filterCriteria.maxPremium}
              onChange={(e) => setFilterCriteria({...filterCriteria, maxPremium: Number(e.target.value)})}
              className="w-full px-3 py-1 border rounded"
              step="1"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">最低评级</label>
            <select
              value={filterCriteria.minRating}
              onChange={(e) => setFilterCriteria({...filterCriteria, minRating: e.target.value})}
              className="w-full px-3 py-1 border rounded"
            >
              <option value="AAA">AAA</option>
              <option value="AA+">AA+</option>
              <option value="AA">AA</option>
              <option value="AA-">AA-</option>
              <option value="A+">A+</option>
              <option value="A">A</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">最大剩余年限</label>
            <input
              type="number"
              value={filterCriteria.maxRemainingYears}
              onChange={(e) => setFilterCriteria({...filterCriteria, maxRemainingYears: Number(e.target.value)})}
              className="w-full px-3 py-1 border rounded"
              step="0.5"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">排序方式</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'score' | 'premium' | 'ytm')}
              className="w-full px-3 py-1 border rounded"
            >
              <option value="score">综合评分</option>
              <option value="premium">溢价率</option>
              <option value="ytm">到期收益率</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bonds List */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">可转债列表</h2>
                <span className="text-sm text-gray-500">
                  已选择 {selectedBonds.size} 只
                </span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      选择
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      债券
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      价格
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      溢价率
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      YTM
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      评级
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      评分
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredAndSortedBonds?.map((bond: ConvertibleBond) => {
                    const scoreBadge = getScoreBadge(bond.score)
                    return (
                      <tr key={bond.code} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedBonds.has(bond.code)}
                            onChange={() => handleSelectBond(bond.code)}
                            className="w-4 h-4 text-blue-600 rounded"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {bond.name}
                            </div>
                            <div className="text-xs text-gray-500">{bond.code}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-gray-900">
                          {formatNumber(bond.price)}
                        </td>
                        <td className={`px-4 py-3 text-right text-sm font-medium ${
                          bond.premium_rate < 10 ? 'text-green-600' : 
                          bond.premium_rate < 20 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {formatPercent(bond.premium_rate)}
                        </td>
                        <td className="px-4 py-3 text-right text-sm text-gray-900">
                          {formatPercent(bond.ytm || 0)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-xs font-medium text-gray-700">
                            {bond.rating}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${scoreBadge.color}`}>
                            {bond.score.toFixed(0)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => handleSetupGrid(bond)}
                            className="text-blue-600 hover:text-blue-800"
                            title="设置网格"
                          >
                            <Grid3X3 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Grid Strategy Panel */}
        <div className="space-y-4">
          {/* Selected Bonds Summary */}
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">选中组合</h3>
            {selectedBonds.size > 0 ? (
              <div className="space-y-2">
                {Array.from(selectedBonds).map(code => {
                  const bond = bonds?.find((b: ConvertibleBond) => b.code === code)
                  if (!bond) return null
                  return (
                    <div key={code} className="flex items-center justify-between text-sm">
                      <span className="text-gray-700">{bond.name}</span>
                      <button
                        onClick={() => handleSelectBond(code)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  )
                })}
                <div className="pt-2 mt-2 border-t">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">平均溢价率</span>
                    <span className="font-medium">
                      {formatPercent(
                        Array.from(selectedBonds).reduce((sum, code) => {
                          const bond = bonds?.find((b: ConvertibleBond) => b.code === code)
                          return sum + (bond?.premium_rate || 0)
                        }, 0) / selectedBonds.size
                      )}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">未选择任何可转债</p>
            )}
          </div>

          {/* Grid Strategy Setup */}
          {gridStrategy.bond_code && (
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">网格策略设置</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">目标债券</label>
                  <div className="text-sm font-medium text-gray-900">
                    {bonds?.find((b: ConvertibleBond) => b.code === gridStrategy.bond_code)?.name}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">下限价格</label>
                    <input
                      type="number"
                      value={gridStrategy.lower_price}
                      onChange={(e) => setGridStrategy({...gridStrategy, lower_price: Number(e.target.value)})}
                      className="w-full px-3 py-1 border rounded"
                      step="1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">上限价格</label>
                    <input
                      type="number"
                      value={gridStrategy.upper_price}
                      onChange={(e) => setGridStrategy({...gridStrategy, upper_price: Number(e.target.value)})}
                      className="w-full px-3 py-1 border rounded"
                      step="1"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">网格数量</label>
                  <input
                    type="number"
                    value={gridStrategy.grid_count}
                    onChange={(e) => setGridStrategy({...gridStrategy, grid_count: Number(e.target.value)})}
                    className="w-full px-3 py-1 border rounded"
                    min="3"
                    max="10"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">每格金额</label>
                  <input
                    type="number"
                    value={gridStrategy.amount_per_grid}
                    onChange={(e) => setGridStrategy({...gridStrategy, amount_per_grid: Number(e.target.value)})}
                    className="w-full px-3 py-1 border rounded"
                    step="1000"
                  />
                </div>
                
                {/* Grid Levels Preview */}
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">网格预览</h4>
                  <div className="space-y-1">
                    {calculateGridLevels().map((level, index) => (
                      <div key={index} className="flex justify-between text-xs">
                        <span className="text-gray-600">网格 {index + 1}</span>
                        <span className="text-gray-900">¥{level.price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">总投资额</span>
                      <span className="font-medium text-gray-900">
                        ¥{(gridStrategy.grid_count * gridStrategy.amount_per_grid).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ConvertibleBond