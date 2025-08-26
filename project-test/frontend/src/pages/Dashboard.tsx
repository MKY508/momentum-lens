import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  AlertCircle, 
  DollarSign,
  Activity,
  PieChart,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';

interface MarketData {
  top_gainers: Array<{
    代码: string;
    名称: string;
    最新价: number;
    涨跌幅: number;
    成交额: number;
  }>;
  major_etfs: Array<{
    code: string;
    name: string;
    price: number;
    change: number;
    volume: number;
  }>;
  total_count: number;
}

interface IndexData {
  current: number;
  ma200: number;
  ratio: number;
  market_state: string;
  state_text: string;
}

interface MomentumData {
  code: string;
  name: string;
  price: number;
  momentum_1m: number;
  momentum_3m: number;
  score: number;
}

const Dashboard: React.FC = () => {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [indexData, setIndexData] = useState<IndexData | null>(null);
  const [momentumRanking, setMomentumRanking] = useState<MomentumData[]>([]);
  const [suggestions, setSuggestions] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取实时市场数据
  const fetchMarketData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/market/realtime');
      const result = await response.json();
      if (result.status === 'success') {
        setMarketData(result.data);
      } else {
        console.error('市场数据响应错误:', result);
        setError('获取市场数据失败');
      }
    } catch (err) {
      console.error('获取市场数据失败:', err);
      setError('网络错误：无法获取市场数据');
    }
  };

  // 获取沪深300指数
  const fetchIndexData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/index/hs300');
      const result = await response.json();
      if (result.status === 'success') {
        setIndexData(result.data);
      }
    } catch (err) {
      console.error('获取指数数据失败:', err);
    }
  };

  // 获取动量排名
  const fetchMomentumRanking = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/momentum/ranking');
      const result = await response.json();
      if (result.status === 'success') {
        setMomentumRanking(result.data);
      }
    } catch (err) {
      console.error('获取动量排名失败:', err);
    }
  };

  // 获取组合建议
  const fetchSuggestions = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/portfolio/suggestions');
      const result = await response.json();
      if (result.status === 'success') {
        setSuggestions(result.suggestions);
      }
    } catch (err) {
      console.error('获取组合建议失败:', err);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      // 并行获取数据，但允许部分失败
      const promises = [
        fetchMarketData().catch(err => console.error('市场数据获取失败', err)),
        fetchIndexData().catch(err => console.error('指数数据获取失败', err)),
        fetchMomentumRanking().catch(err => console.error('动量排名获取失败', err)),
        fetchSuggestions().catch(err => console.error('组合建议获取失败', err))
      ];
      
      await Promise.allSettled(promises);
      setLoading(false);
    };

    loadData();
    // 每30秒刷新一次数据
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 获取市场状态颜色
  const getMarketStateColor = (state: string) => {
    switch (state) {
      case 'BULLISH': return 'text-green-600';
      case 'BEARISH': return 'text-red-600';
      default: return 'text-yellow-600';
    }
  };

  // 获取市场状态图标
  const getMarketStateIcon = (state: string) => {
    switch (state) {
      case 'BULLISH': return <TrendingUp className="w-6 h-6" />;
      case 'BEARISH': return <TrendingDown className="w-6 h-6" />;
      default: return <Activity className="w-6 h-6" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-xl mb-2">加载中...</div>
          <div className="text-sm text-gray-500">正在获取市场数据</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-xl text-red-600 mb-2">加载失败</div>
          <div className="text-sm text-gray-500">{error}</div>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* 顶部市场状态 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* 市场状态卡片 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">市场状态</p>
              <p className={`text-2xl font-bold ${indexData ? getMarketStateColor(indexData.market_state) : ''}`}>
                {indexData?.state_text || '加载中'}
              </p>
            </div>
            {indexData && getMarketStateIcon(indexData.market_state)}
          </div>
        </div>

        {/* 沪深300指数 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">沪深300</p>
              <p className="text-2xl font-bold">{indexData?.current.toFixed(2) || '-'}</p>
              <p className="text-sm text-gray-600">MA200: {indexData?.ma200.toFixed(2) || '-'}</p>
            </div>
            <BarChart3 className="w-6 h-6 text-blue-500" />
          </div>
        </div>

        {/* ETF总数 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">ETF总数</p>
              <p className="text-2xl font-bold">{marketData?.total_count || 0}</p>
            </div>
            <PieChart className="w-6 h-6 text-purple-500" />
          </div>
        </div>

        {/* 今日建议 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-sm">今日建议</p>
              <p className="text-xl font-bold text-green-600">
                {suggestions ? `${Object.keys(suggestions.satellite || {}).length}个机会` : '分析中'}
              </p>
            </div>
            <DollarSign className="w-6 h-6 text-green-500" />
          </div>
        </div>
      </div>

      {/* 主要内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 今日涨幅榜 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-green-500" />
            今日涨幅榜
          </h2>
          <div className="space-y-2">
            {marketData?.top_gainers.slice(0, 5).map((etf, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div>
                  <span className="font-medium">{etf.名称}</span>
                  <span className="text-gray-500 text-sm ml-2">({etf.代码})</span>
                </div>
                <div className="flex items-center">
                  <span className="font-bold text-green-600">+{etf.涨跌幅}%</span>
                  <ArrowUpRight className="w-4 h-4 ml-1 text-green-600" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 动量排名 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-blue-500" />
            动量排名Top5
          </h2>
          <div className="space-y-2">
            {momentumRanking.slice(0, 5).map((etf, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div>
                  <span className="font-medium">{etf.name}</span>
                  <span className="text-gray-500 text-sm ml-2">({etf.code})</span>
                </div>
                <div className="text-right">
                  <div className="font-bold text-blue-600">得分: {etf.score}</div>
                  <div className="text-xs text-gray-500">
                    1M: {etf.momentum_1m}% | 3M: {etf.momentum_3m}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Core资产配置建议 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold mb-4">Core资产配置建议</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {suggestions?.core && Object.entries(suggestions.core).map(([code, info]: [string, any]) => (
            <div key={code} className="border rounded-lg p-4">
              <div className="font-medium">{info.name}</div>
              <div className="text-sm text-gray-500">{code}</div>
              <div className="mt-2">
                <div className="text-lg font-bold">{(info.weight * 100).toFixed(0)}%</div>
                <div className={`text-sm ${
                  info.action === 'BUY' ? 'text-green-600' : 
                  info.action === 'REDUCE' ? 'text-red-600' : 
                  'text-gray-600'
                }`}>
                  {info.action === 'BUY' ? '建议买入' : 
                   info.action === 'REDUCE' ? '建议减持' : 
                   '继续持有'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 卫星策略建议 */}
      {suggestions?.satellite && suggestions.satellite.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4">卫星策略建议</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suggestions.satellite.map((etf: any, index: number) => (
              <div key={index} className="border rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium">{etf.name}</div>
                    <div className="text-sm text-gray-500">{etf.code}</div>
                    <div className="mt-2">
                      <span className="text-lg font-bold">动量得分: {etf.score}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold">{(etf.weight * 100).toFixed(0)}%</div>
                    <div className={`text-sm ${etf.action === 'BUY' ? 'text-green-600' : 'text-gray-600'}`}>
                      {etf.action === 'BUY' ? '建议买入' : '继续持有'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 风险提示 */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center">
          <AlertCircle className="w-5 h-5 text-yellow-600 mr-2" />
          <span className="text-yellow-800">
            提示：数据来源于免费接口，可能有15分钟延迟。投资有风险，决策需谨慎。
          </span>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;