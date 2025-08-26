import React, { useState } from 'react'
import { 
  Settings as SettingsIcon,
  Save,
  AlertTriangle,
  Database,
  Shield,
  Zap,
  Globe,
  Bell,
  Mail,
  Smartphone,
  ChevronRight
} from 'lucide-react'
import toast from 'react-hot-toast'

interface StrategyConfig {
  // Core模块配置
  core_rebalance_threshold: number
  core_max_position: number
  core_dca_amount: number
  
  // Satellite模块配置
  satellite_top_n: number
  satellite_momentum_window: number
  satellite_ma_period: number
  satellite_min_volume: number
  
  // 可转债配置
  cb_max_premium: number
  cb_min_rating: string
  cb_max_years: number
  cb_grid_count: number
  cb_amount_per_grid: number
}

interface RiskConfig {
  max_position_size: number
  max_leverage: number
  stop_loss_percent: number
  max_drawdown_alert: number
  position_limit: number
  concentration_limit: number
}

interface DataSourceConfig {
  provider: string
  api_key: string
  update_frequency: number
  cache_ttl: number
  enable_fallback: boolean
}

interface NotificationConfig {
  enable_email: boolean
  email_address: string
  enable_sms: boolean
  phone_number: string
  enable_webhook: boolean
  webhook_url: string
  alert_types: {
    rebalance: boolean
    risk_warning: boolean
    trade_execution: boolean
    system_error: boolean
  }
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'strategy' | 'risk' | 'data' | 'notification'>('strategy')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  
  const [strategyConfig, setStrategyConfig] = useState<StrategyConfig>({
    core_rebalance_threshold: 2,
    core_max_position: 80,
    core_dca_amount: 10000,
    satellite_top_n: 2,
    satellite_momentum_window: 20,
    satellite_ma_period: 200,
    satellite_min_volume: 50000000,
    cb_max_premium: 20,
    cb_min_rating: 'AA',
    cb_max_years: 5,
    cb_grid_count: 5,
    cb_amount_per_grid: 10000
  })
  
  const [riskConfig, setRiskConfig] = useState<RiskConfig>({
    max_position_size: 30,
    max_leverage: 1.5,
    stop_loss_percent: 10,
    max_drawdown_alert: 15,
    position_limit: 20,
    concentration_limit: 40
  })
  
  const [dataConfig, setDataConfig] = useState<DataSourceConfig>({
    provider: 'akshare',
    api_key: '',
    update_frequency: 60,
    cache_ttl: 300,
    enable_fallback: true
  })
  
  const [notificationConfig, setNotificationConfig] = useState<NotificationConfig>({
    enable_email: false,
    email_address: '',
    enable_sms: false,
    phone_number: '',
    enable_webhook: false,
    webhook_url: '',
    alert_types: {
      rebalance: true,
      risk_warning: true,
      trade_execution: false,
      system_error: true
    }
  })

  const handleSave = async () => {
    try {
      // Here you would make API calls to save the configurations
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
      
      toast.success('设置已保存')
      setHasUnsavedChanges(false)
    } catch (error) {
      toast.error('保存设置失败')
    }
  }

  const handleStrategyChange = (field: keyof StrategyConfig, value: any) => {
    setStrategyConfig(prev => ({ ...prev, [field]: value }))
    setHasUnsavedChanges(true)
  }

  const handleRiskChange = (field: keyof RiskConfig, value: any) => {
    setRiskConfig(prev => ({ ...prev, [field]: value }))
    setHasUnsavedChanges(true)
  }

  const handleDataChange = (field: keyof DataSourceConfig, value: any) => {
    setDataConfig(prev => ({ ...prev, [field]: value }))
    setHasUnsavedChanges(true)
  }

  const handleNotificationChange = (field: keyof NotificationConfig, value: any) => {
    setNotificationConfig(prev => ({ ...prev, [field]: value }))
    setHasUnsavedChanges(true)
  }

  const tabs = [
    { id: 'strategy', label: '策略参数', icon: Zap },
    { id: 'risk', label: '风险控制', icon: Shield },
    { id: 'data', label: '数据源', icon: Database },
    { id: 'notification', label: '通知设置', icon: Bell }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <SettingsIcon className="w-8 h-8 text-gray-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">系统设置</h1>
            <p className="text-gray-500">配置策略参数和系统选项</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={!hasUnsavedChanges}
          className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
            hasUnsavedChanges
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          <Save className="w-4 h-4" />
          <span>保存设置</span>
        </button>
      </div>

      {/* Unsaved Changes Warning */}
      {hasUnsavedChanges && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-yellow-600" />
          <span className="text-sm text-yellow-800">您有未保存的更改</span>
        </div>
      )}

      <div className="flex space-x-6">
        {/* Sidebar Navigation */}
        <div className="w-64">
          <nav className="space-y-1">
            {tabs.map(tab => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-600 border-l-4 border-blue-600'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </div>
                  <ChevronRight className="w-4 h-4" />
                </button>
              )
            })}
          </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            {activeTab === 'strategy' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">策略参数配置</h2>
                
                {/* Core Module Settings */}
                <div>
                  <h3 className="text-md font-medium text-gray-700 mb-3">Core 模块</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        再平衡阈值 (%)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.core_rebalance_threshold}
                        onChange={(e) => handleStrategyChange('core_rebalance_threshold', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        step="0.5"
                        min="0.5"
                        max="10"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        最大仓位 (%)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.core_max_position}
                        onChange={(e) => handleStrategyChange('core_max_position', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="50"
                        max="100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        定投金额 (¥)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.core_dca_amount}
                        onChange={(e) => handleStrategyChange('core_dca_amount', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        step="1000"
                      />
                    </div>
                  </div>
                </div>

                {/* Satellite Module Settings */}
                <div>
                  <h3 className="text-md font-medium text-gray-700 mb-3">Satellite 模块</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        选择Top N
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.satellite_top_n}
                        onChange={(e) => handleStrategyChange('satellite_top_n', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="1"
                        max="5"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        动量窗口 (天)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.satellite_momentum_window}
                        onChange={(e) => handleStrategyChange('satellite_momentum_window', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="5"
                        max="60"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        MA周期 (天)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.satellite_ma_period}
                        onChange={(e) => handleStrategyChange('satellite_ma_period', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="50"
                        max="250"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        最小成交额 (¥)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.satellite_min_volume}
                        onChange={(e) => handleStrategyChange('satellite_min_volume', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        step="10000000"
                      />
                    </div>
                  </div>
                </div>

                {/* Convertible Bond Settings */}
                <div>
                  <h3 className="text-md font-medium text-gray-700 mb-3">可转债模块</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        最大溢价率 (%)
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.cb_max_premium}
                        onChange={(e) => handleStrategyChange('cb_max_premium', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="0"
                        max="50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        最低评级
                      </label>
                      <select
                        value={strategyConfig.cb_min_rating}
                        onChange={(e) => handleStrategyChange('cb_min_rating', e.target.value)}
                        className="w-full px-3 py-2 border rounded-lg"
                      >
                        <option value="AAA">AAA</option>
                        <option value="AA+">AA+</option>
                        <option value="AA">AA</option>
                        <option value="AA-">AA-</option>
                        <option value="A+">A+</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        最大剩余年限
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.cb_max_years}
                        onChange={(e) => handleStrategyChange('cb_max_years', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        step="0.5"
                        min="0.5"
                        max="10"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        网格数量
                      </label>
                      <input
                        type="number"
                        value={strategyConfig.cb_grid_count}
                        onChange={(e) => handleStrategyChange('cb_grid_count', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="3"
                        max="10"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'risk' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">风险控制参数</h2>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      单个仓位上限 (%)
                    </label>
                    <input
                      type="number"
                      value={riskConfig.max_position_size}
                      onChange={(e) => handleRiskChange('max_position_size', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      min="10"
                      max="50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      最大杠杆倍数
                    </label>
                    <input
                      type="number"
                      value={riskConfig.max_leverage}
                      onChange={(e) => handleRiskChange('max_leverage', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      step="0.1"
                      min="1"
                      max="3"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      止损比例 (%)
                    </label>
                    <input
                      type="number"
                      value={riskConfig.stop_loss_percent}
                      onChange={(e) => handleRiskChange('stop_loss_percent', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      min="5"
                      max="20"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      最大回撤警戒 (%)
                    </label>
                    <input
                      type="number"
                      value={riskConfig.max_drawdown_alert}
                      onChange={(e) => handleRiskChange('max_drawdown_alert', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      min="10"
                      max="30"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      持仓数量限制
                    </label>
                    <input
                      type="number"
                      value={riskConfig.position_limit}
                      onChange={(e) => handleRiskChange('position_limit', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      min="5"
                      max="50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      行业集中度限制 (%)
                    </label>
                    <input
                      type="number"
                      value={riskConfig.concentration_limit}
                      onChange={(e) => handleRiskChange('concentration_limit', Number(e.target.value))}
                      className="w-full px-3 py-2 border rounded-lg"
                      min="20"
                      max="60"
                    />
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start space-x-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <div>
                      <p className="text-sm text-yellow-800 font-medium">风险提示</p>
                      <p className="text-xs text-yellow-700 mt-1">
                        修改风险参数可能影响策略表现，请谨慎调整。建议在回测环境中验证参数效果。
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'data' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">数据源配置</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      数据提供商
                    </label>
                    <select
                      value={dataConfig.provider}
                      onChange={(e) => handleDataChange('provider', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg"
                    >
                      <option value="akshare">AKShare</option>
                      <option value="tushare">Tushare</option>
                      <option value="eastmoney">东方财富</option>
                      <option value="custom">自定义</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">
                      API密钥
                    </label>
                    <input
                      type="password"
                      value={dataConfig.api_key}
                      onChange={(e) => handleDataChange('api_key', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="如果需要的话"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        更新频率 (秒)
                      </label>
                      <input
                        type="number"
                        value={dataConfig.update_frequency}
                        onChange={(e) => handleDataChange('update_frequency', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="10"
                        max="3600"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        缓存时间 (秒)
                      </label>
                      <input
                        type="number"
                        value={dataConfig.cache_ttl}
                        onChange={(e) => handleDataChange('cache_ttl', Number(e.target.value))}
                        className="w-full px-3 py-2 border rounded-lg"
                        min="60"
                        max="7200"
                      />
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="enable_fallback"
                      checked={dataConfig.enable_fallback}
                      onChange={(e) => handleDataChange('enable_fallback', e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <label htmlFor="enable_fallback" className="text-sm text-gray-700">
                      启用备用数据源
                    </label>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start space-x-2">
                    <Globe className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="text-sm text-blue-800 font-medium">数据质量</p>
                      <p className="text-xs text-blue-700 mt-1">
                        系统会自动验证数据质量，并在检测到异常时切换到备用数据源。
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notification' && (
              <div className="space-y-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">通知设置</h2>
                
                {/* Email Notifications */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="enable_email"
                      checked={notificationConfig.enable_email}
                      onChange={(e) => handleNotificationChange('enable_email', e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <label htmlFor="enable_email" className="text-sm font-medium text-gray-700">
                      <Mail className="w-4 h-4 inline mr-1" />
                      启用邮件通知
                    </label>
                  </div>
                  {notificationConfig.enable_email && (
                    <input
                      type="email"
                      value={notificationConfig.email_address}
                      onChange={(e) => handleNotificationChange('email_address', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="your@email.com"
                    />
                  )}
                </div>

                {/* SMS Notifications */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="enable_sms"
                      checked={notificationConfig.enable_sms}
                      onChange={(e) => handleNotificationChange('enable_sms', e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <label htmlFor="enable_sms" className="text-sm font-medium text-gray-700">
                      <Smartphone className="w-4 h-4 inline mr-1" />
                      启用短信通知
                    </label>
                  </div>
                  {notificationConfig.enable_sms && (
                    <input
                      type="tel"
                      value={notificationConfig.phone_number}
                      onChange={(e) => handleNotificationChange('phone_number', e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg"
                      placeholder="+86 138 0000 0000"
                    />
                  )}
                </div>

                {/* Alert Types */}
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-3">通知类型</h3>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="alert_rebalance"
                        checked={notificationConfig.alert_types.rebalance}
                        onChange={(e) => handleNotificationChange('alert_types', {
                          ...notificationConfig.alert_types,
                          rebalance: e.target.checked
                        })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="alert_rebalance" className="text-sm text-gray-700">
                        再平衡提醒
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="alert_risk"
                        checked={notificationConfig.alert_types.risk_warning}
                        onChange={(e) => handleNotificationChange('alert_types', {
                          ...notificationConfig.alert_types,
                          risk_warning: e.target.checked
                        })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="alert_risk" className="text-sm text-gray-700">
                        风险预警
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="alert_trade"
                        checked={notificationConfig.alert_types.trade_execution}
                        onChange={(e) => handleNotificationChange('alert_types', {
                          ...notificationConfig.alert_types,
                          trade_execution: e.target.checked
                        })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="alert_trade" className="text-sm text-gray-700">
                        交易执行
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="alert_error"
                        checked={notificationConfig.alert_types.system_error}
                        onChange={(e) => handleNotificationChange('alert_types', {
                          ...notificationConfig.alert_types,
                          system_error: e.target.checked
                        })}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <label htmlFor="alert_error" className="text-sm text-gray-700">
                        系统错误
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings