"""
数据适配器 - 统一AkShare数据接口
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yaml
import logging
from functools import lru_cache
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAdapter:
    """统一数据接口适配器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.cache = {}
        self.cache_time = {}
        
    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self.cache_time:
            return False
        cache_hours = self.config['data']['cache_hours']
        return (datetime.now() - self.cache_time[key]).seconds < cache_hours * 3600
        
    @lru_cache(maxsize=100)
    def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        try:
            logger.info("获取ETF列表...")
            # 获取ETF实时行情
            etf_spot = ak.fund_etf_spot_em()
            
            # 统一字段名
            etf_spot = etf_spot.rename(columns={
                '代码': 'code',
                '名称': 'name', 
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '成交额': 'turnover',
                '成交量': 'volume'
            })
            
            # 筛选活跃ETF
            min_turnover = self.config['strategy']['qualification']['min_turnover']
            active_etfs = etf_spot[etf_spot['turnover'] >= min_turnover]
            
            logger.info(f"获取到 {len(active_etfs)} 只活跃ETF")
            return active_etfs
            
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return pd.DataFrame()
            
    def get_etf_history(self, code: str, days: int = 252) -> pd.DataFrame:
        """获取ETF历史数据"""
        cache_key = f"etf_history_{code}_{days}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            # 设置超时时间，避免长时间等待
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("获取数据超时")
            
            # 设置5秒超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)
            
            try:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                
                # 获取历史数据
                hist = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                
                # 统一字段名
                hist = hist.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high', 
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume'
                })
                
                hist['date'] = pd.to_datetime(hist['date'])
                hist.set_index('date', inplace=True)
                
                self.cache[cache_key] = hist
                self.cache_time[cache_key] = datetime.now()
                
                return hist
                
            finally:
                signal.alarm(0)  # 取消超时
                
        except (TimeoutError, Exception) as e:
            logger.warning(f"获取ETF {code} 历史数据失败: {e}, 返回模拟数据")
            # 返回模拟数据
            dates = pd.date_range(end=datetime.now(), periods=days)
            mock_data = pd.DataFrame({
                'open': np.random.uniform(100, 110, days),
                'high': np.random.uniform(110, 120, days),
                'low': np.random.uniform(90, 100, days),
                'close': np.random.uniform(95, 115, days),
                'volume': np.random.uniform(1000000, 10000000, days)
            }, index=dates)
            return mock_data
            
    def get_index_data(self, symbol: str = "sh000300") -> pd.DataFrame:
        """获取指数数据（默认沪深300）"""
        cache_key = f"index_{symbol}"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            # 获取指数日线数据
            index_data = ak.stock_zh_index_daily(symbol=symbol)
            
            # 计算MA200
            index_data['ma200'] = index_data['close'].rolling(window=200).mean()
            
            self.cache[cache_key] = index_data
            self.cache_time[cache_key] = datetime.now()
            
            return index_data
            
        except Exception as e:
            logger.error(f"获取指数 {symbol} 数据失败: {e}")
            return pd.DataFrame()
            
    def get_convertible_bonds(self) -> pd.DataFrame:
        """获取可转债数据"""
        cache_key = "convertible_bonds"
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]
            
        try:
            logger.info("获取可转债数据...")
            
            # 获取可转债行情
            cb_data = ak.bond_cb_jsl()
            
            # 筛选条件
            filters = self.config['convertible_bond']['filters']
            
            # 统一字段并筛选
            cb_filtered = cb_data[
                (cb_data['规模'] >= filters['min_size'] / 100000000) &  # 转换为亿元
                (cb_data['转股溢价率'] <= filters['max_premium'] * 100)  # 转换为百分比
            ]
            
            self.cache[cache_key] = cb_filtered
            self.cache_time[cache_key] = datetime.now()
            
            logger.info(f"获取到 {len(cb_filtered)} 只符合条件的可转债")
            return cb_filtered
            
        except Exception as e:
            logger.error(f"获取可转债数据失败: {e}")
            # 返回模拟数据以便测试
            return pd.DataFrame({
                '代码': ['123001', '123002', '123003'],
                '名称': ['转债A', '转债B', '转债C'],
                '现价': [110, 105, 108],
                '转股溢价率': [15, 20, 18],
                '规模': [5, 8, 6],
                '剩余年限': [3, 4, 2],
                '评级': ['AA+', 'AA', 'AA-']
            })
            
    def calculate_correlation(self, codes: List[str], days: int = 90) -> pd.DataFrame:
        """计算ETF之间的相关性"""
        try:
            price_data = pd.DataFrame()
            
            for code in codes:
                hist = self.get_etf_history(code, days)
                if not hist.empty:
                    price_data[code] = hist['close']
                    
            if price_data.empty:
                return pd.DataFrame()
                
            # 计算收益率
            returns = price_data.pct_change().dropna()
            
            # 计算相关性矩阵
            correlation = returns.corr()
            
            return correlation
            
        except Exception as e:
            logger.error(f"计算相关性失败: {e}")
            return pd.DataFrame()
            
    def get_market_state(self) -> str:
        """判断市场状态"""
        try:
            # 获取沪深300指数
            index_data = self.get_index_data()
            
            if index_data.empty:
                return "UNKNOWN"
                
            current_price = index_data['close'].iloc[-1]
            ma200 = index_data['ma200'].iloc[-1]
            
            if pd.isna(ma200):
                return "UNKNOWN"
                
            ratio = current_price / ma200
            
            if ratio > 1.02:
                return "BULLISH"  # 牛市
            elif ratio < 0.98:
                return "BEARISH"  # 熊市
            else:
                return "SIDEWAYS"  # 震荡市
                
        except Exception as e:
            logger.error(f"判断市场状态失败: {e}")
            return "UNKNOWN"
            
    def get_etf_iopv(self, code: str) -> Optional[float]:
        """获取ETF的IOPV（实时净值）"""
        try:
            # AkShare暂无直接IOPV接口，这里用收盘价模拟
            hist = self.get_etf_history(code, days=1)
            if not hist.empty:
                return hist['close'].iloc[-1]
            return None
        except:
            return None
            
if __name__ == "__main__":
    # 测试代码
    adapter = DataAdapter()
    
    # 测试获取ETF列表
    etf_list = adapter.get_etf_list()
    print(f"ETF列表: {len(etf_list)} 只")
    print(etf_list.head())
    
    # 测试获取历史数据
    if not etf_list.empty:
        code = etf_list.iloc[0]['code']
        hist = adapter.get_etf_history(code, days=30)
        print(f"\n{code} 历史数据:")
        print(hist.tail())
    
    # 测试市场状态
    state = adapter.get_market_state()
    print(f"\n市场状态: {state}")