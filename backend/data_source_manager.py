"""
统一数据源管理器
支持多数据源切换和实时数据获取
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import requests
import json

# 尝试导入各种数据源
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ AkShare not available")

try:
    from core.data_fetcher import get_data_fetcher
    CORE_FETCHER_AVAILABLE = True
except ImportError:
    CORE_FETCHER_AVAILABLE = False
    print("⚠️ Core DataFetcher not available")


class DataSource(Enum):
    """数据源枚举"""
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"
    SINA = "sina"
    TUSHARE = "tushare"
    YAHOO = "yahoo"
    MOCK = "mock"  # 模拟数据


class DataSourceManager:
    """统一数据源管理器"""
    
    def __init__(self):
        self.current_source = DataSource.AKSHARE if AKSHARE_AVAILABLE else DataSource.MOCK
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 60  # 缓存60秒
        self.last_refresh = datetime.now()
        self.auto_refresh_interval = 300  # 5分钟自动刷新
        
        # ETF基本信息
        self.ETF_INFO = {
            '510300': {'name': '沪深300ETF', 'type': 'Core'},
            '588000': {'name': '科创50ETF', 'type': 'Growth'},
            '512760': {'name': '半导体ETF', 'type': 'Growth'},
            '512720': {'name': '计算机ETF', 'type': 'Growth'},
            '516010': {'name': '游戏动漫ETF', 'type': 'Growth'},
            '159869': {'name': '游戏ETF', 'type': 'Growth'},
            '516160': {'name': '新能源ETF', 'type': 'NewEnergy'},
            '515790': {'name': '光伏ETF', 'type': 'NewEnergy'},
            '515030': {'name': '新能源车ETF', 'type': 'NewEnergy'},
            '512400': {'name': '有色金属ETF', 'type': 'Industry'},
            '512800': {'name': '银行ETF', 'type': 'Industry'},
            '512000': {'name': '券商ETF', 'type': 'Industry'},
            '512170': {'name': '医疗ETF', 'type': 'Industry'},
        }
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """获取可用的数据源列表"""
        sources = []
        
        # AkShare
        sources.append({
            "id": DataSource.AKSHARE.value,
            "name": "AkShare",
            "type": "free",
            "available": AKSHARE_AVAILABLE,
            "requiresKey": False,
            "latency": "medium",
            "reliability": "high",
            "description": "免费开源数据接口，数据全面"
        })
        
        # East Money
        sources.append({
            "id": DataSource.EASTMONEY.value,
            "name": "东方财富",
            "type": "free",
            "available": True,
            "requiresKey": False,
            "latency": "low",
            "reliability": "high",
            "description": "东方财富实时行情"
        })
        
        # Sina Finance
        sources.append({
            "id": DataSource.SINA.value,
            "name": "新浪财经",
            "type": "free",
            "available": True,
            "requiresKey": False,
            "latency": "low",
            "reliability": "medium",
            "description": "新浪财经实时数据"
        })
        
        # Tushare
        sources.append({
            "id": DataSource.TUSHARE.value,
            "name": "Tushare",
            "type": "freemium",
            "available": False,
            "requiresKey": True,
            "latency": "medium",
            "reliability": "high",
            "description": "需要注册获取Token"
        })
        
        # Yahoo Finance
        sources.append({
            "id": DataSource.YAHOO.value,
            "name": "Yahoo Finance",
            "type": "free",
            "available": False,
            "requiresKey": False,
            "latency": "high",
            "reliability": "low",
            "description": "国际数据源，可能不稳定"
        })
        
        # Mock Data
        sources.append({
            "id": DataSource.MOCK.value,
            "name": "模拟数据",
            "type": "mock",
            "available": True,
            "requiresKey": False,
            "latency": "instant",
            "reliability": "always",
            "description": "测试用模拟数据"
        })
        
        return sources
    
    def set_data_source(self, source_id: str) -> bool:
        """切换数据源"""
        try:
            new_source = DataSource(source_id)
            
            # 检查数据源是否可用
            if new_source == DataSource.AKSHARE and not AKSHARE_AVAILABLE:
                return False
            
            self.current_source = new_source
            # 清空缓存，强制刷新
            self.cache.clear()
            self.cache_time.clear()
            return True
            
        except ValueError:
            return False
    
    def should_auto_refresh(self) -> bool:
        """检查是否需要自动刷新"""
        return (datetime.now() - self.last_refresh).seconds >= self.auto_refresh_interval
    
    async def fetch_etf_data(self, code: str) -> Optional[Dict]:
        """根据当前数据源获取ETF数据"""
        
        # 检查缓存
        cache_key = f"{self.current_source.value}_{code}"
        if cache_key in self.cache:
            if (datetime.now() - self.cache_time[cache_key]).seconds < self.cache_duration:
                return self.cache[cache_key]
        
        # 根据数据源获取数据
        data = None
        
        if self.current_source == DataSource.AKSHARE:
            data = await self._fetch_from_akshare(code)
        elif self.current_source == DataSource.EASTMONEY:
            data = await self._fetch_from_eastmoney(code)
        elif self.current_source == DataSource.SINA:
            data = await self._fetch_from_sina(code)
        elif self.current_source == DataSource.MOCK:
            data = self._get_mock_data(code)
        
        # 更新缓存
        if data:
            self.cache[cache_key] = data
            self.cache_time[cache_key] = datetime.now()
            self.last_refresh = datetime.now()
        
        return data
    
    async def _fetch_from_akshare(self, code: str) -> Optional[Dict]:
        """从AkShare获取数据"""
        if not AKSHARE_AVAILABLE:
            return None
        
        try:
            # 获取实时行情
            df = ak.fund_etf_spot_em()
            etf_data = df[df['代码'] == code]
            
            if etf_data.empty:
                return None
            
            row = etf_data.iloc[0]
            
            # 获取历史数据计算动量
            symbol = f"sh{code}" if code.startswith('5') else f"sz{code}"
            hist_df = ak.fund_etf_hist_sina(symbol=symbol)
            
            r60, r120, score = self._calculate_momentum(hist_df)
            
            return {
                'code': code,
                'name': self.ETF_INFO.get(code, {}).get('name', row.get('名称', '')),
                'type': self.ETF_INFO.get(code, {}).get('type', 'Other'),
                'score': score,
                'r60': r60,
                'r120': r120,
                'current_price': float(row.get('最新价', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交额', 0)) / 100000000,  # 转亿元
                'timestamp': datetime.now().isoformat(),
                'source': 'akshare'
            }
            
        except Exception as e:
            print(f"AkShare获取{code}失败: {e}")
            return None
    
    async def _fetch_from_eastmoney(self, code: str) -> Optional[Dict]:
        """从东方财富获取数据"""
        try:
            # 东方财富API
            market = "1" if code.startswith('6') else "0"
            url = f"http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": f"{market}.{code}",
                "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100,f101,f102,f103,f104,f105,f106,f107,f108,f109,f110,f111,f112,f113,f114,f115,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150,f151,f152,f153,f154,f155,f156,f157,f158,f159,f160,f161,f162,f163,f164,f165,f166,f167,f168,f169,f170"
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    stock_data = data['data']
                    
                    return {
                        'code': code,
                        'name': self.ETF_INFO.get(code, {}).get('name', stock_data.get('f58', '')),
                        'type': self.ETF_INFO.get(code, {}).get('type', 'Other'),
                        'current_price': stock_data.get('f43', 0) / 1000,
                        'change_pct': stock_data.get('f170', 0) / 100,
                        'volume': stock_data.get('f47', 0) / 100000000,
                        'r60': 0,  # 需要另外计算
                        'r120': 0,
                        'score': 0,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'eastmoney'
                    }
            
        except Exception as e:
            print(f"东方财富获取{code}失败: {e}")
        
        return None
    
    async def _fetch_from_sina(self, code: str) -> Optional[Dict]:
        """从新浪财经获取数据"""
        try:
            sina_code = f"sh{code}" if code.startswith('5') or code.startswith('6') else f"sz{code}"
            url = f"http://hq.sinajs.cn/list={sina_code}"
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'gbk'
            
            if response.status_code == 200:
                data_str = response.text.split('"')[1]
                if data_str:
                    parts = data_str.split(',')
                    if len(parts) >= 32:
                        current = float(parts[3])
                        prev_close = float(parts[2])
                        
                        return {
                            'code': code,
                            'name': self.ETF_INFO.get(code, {}).get('name', parts[0]),
                            'type': self.ETF_INFO.get(code, {}).get('type', 'Other'),
                            'current_price': current,
                            'change_pct': ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0,
                            'volume': float(parts[9]) / 100000000,
                            'r60': 0,
                            'r120': 0,
                            'score': 0,
                            'timestamp': datetime.now().isoformat(),
                            'source': 'sina'
                        }
            
        except Exception as e:
            print(f"新浪财经获取{code}失败: {e}")
        
        return None
    
    def _get_mock_data(self, code: str) -> Dict:
        """获取模拟数据"""
        # 基于2025-08-25的真实数据
        mock_data = {
            '512400': {'score': 31.9, 'r60': 31.03, 'r120': 33.2, 'volume': 7.1},
            '516010': {'score': 27.16, 'r60': 30.77, 'r120': 21.74, 'volume': 2.62},
            '159869': {'score': 27.03, 'r60': 30.84, 'r120': 21.32, 'volume': 7.61},
            '512760': {'score': 26.46, 'r60': 31.13, 'r120': 19.46, 'volume': 14.05},
            '588000': {'score': 24.36, 'r60': 28.45, 'r120': 18.23, 'volume': 112.08},
            '512720': {'score': 19.13, 'r60': 25.59, 'r120': 9.43, 'volume': 1.07},
            '515790': {'score': 18.73, 'r60': 26.25, 'r120': 7.45, 'volume': 8.16},
            '516160': {'score': 17.54, 'r60': 23.56, 'r120': 8.51, 'volume': 1.52},
            '512170': {'score': 14.94, 'r60': 17.38, 'r120': 11.27, 'volume': 9.92},
            '515030': {'score': 12.57, 'r60': 18.14, 'r120': 4.2, 'volume': 1.35},
            '512000': {'score': -37.36, 'r60': -35.91, 'r120': -39.55, 'volume': 28.86},
            '512800': {'score': -45.41, 'r60': -47.24, 'r120': -42.66, 'volume': 9.6},
        }
        
        data = mock_data.get(code, {
            'score': np.random.uniform(-10, 30),
            'r60': np.random.uniform(-20, 35),
            'r120': np.random.uniform(-25, 30),
            'volume': np.random.uniform(1, 50)
        })
        
        return {
            'code': code,
            'name': self.ETF_INFO.get(code, {}).get('name', 'Unknown ETF'),
            'type': self.ETF_INFO.get(code, {}).get('type', 'Other'),
            'score': data['score'],
            'r60': data['r60'],
            'r120': data['r120'],
            'current_price': 1.0 + data['r60'] / 100,
            'change_pct': np.random.uniform(-3, 3),
            'volume': data['volume'],
            'timestamp': datetime.now().isoformat(),
            'source': 'mock'
        }
    
    def _calculate_momentum(self, df: pd.DataFrame) -> tuple:
        """计算动量指标"""
        if df is None or df.empty:
            return 0, 0, 0
        
        try:
            df = df.sort_values('date')
            df = df.tail(150)
            
            if len(df) < 60:
                return 0, 0, 0
            
            current_price = df['close'].iloc[-1]
            price_60d_ago = df['close'].iloc[-60]
            r60 = ((current_price / price_60d_ago) - 1) * 100
            
            if len(df) >= 120:
                price_120d_ago = df['close'].iloc[-120]
                r120 = ((current_price / price_120d_ago) - 1) * 100
            else:
                r120 = r60 * 0.8
            
            score = 0.6 * r60 + 0.4 * r120
            
            return round(r60, 2), round(r120, 2), round(score, 2)
            
        except Exception as e:
            print(f"计算动量失败: {e}")
            return 0, 0, 0
    
    async def get_all_satellite_rankings(self) -> List[Dict]:
        """获取所有卫星ETF排名"""
        satellite_codes = [
            '588000', '512760', '512720', '516010', '159869',  # 成长线
            '516160', '515790', '515030',  # 电新链
            '512400', '512800', '512000', '512170'  # 其他行业
        ]
        
        rankings = []
        for code in satellite_codes:
            data = await self.fetch_etf_data(code)
            if data:
                rankings.append(data)
        
        # 按评分排序
        rankings.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 标记持仓
        if len(rankings) >= 2:
            rankings[1]['isHolding'] = True
            rankings[1]['holdingStartDate'] = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        
        return rankings
    
    def force_refresh(self):
        """强制刷新所有缓存"""
        self.cache.clear()
        self.cache_time.clear()
        self.last_refresh = datetime.now()
        return {"status": "success", "message": "缓存已清空，数据将刷新"}
    
    def get_status(self) -> Dict:
        """获取数据源状态"""
        return {
            "current_source": self.current_source.value,
            "available_sources": self.get_available_sources(),
            "last_refresh": self.last_refresh.isoformat(),
            "cache_size": len(self.cache),
            "auto_refresh_enabled": True,
            "auto_refresh_interval": self.auto_refresh_interval,
            "next_auto_refresh": (self.last_refresh + timedelta(seconds=self.auto_refresh_interval)).isoformat()
        }


# 全局实例
data_source_manager = DataSourceManager()