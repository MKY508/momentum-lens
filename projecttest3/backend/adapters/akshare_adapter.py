"""
AkShare data adapter implementation
AkShare 数据适配器实现
"""
from typing import Optional, Dict, List, Any
from datetime import datetime, date, timedelta
import pandas as pd
import akshare as ak
from loguru import logger

from .base import DataAdapter, DataQuality


class AkShareAdapter(DataAdapter):
    """
    AkShare 数据适配器
    作为主数据源，提供高质量的市场数据
    """
    
    def __init__(self):
        super().__init__(name="AkShare", quality=DataQuality.HIGH)
        logger.info("Initialized AkShare adapter")
        
    def get_etf_price(self, code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取ETF历史价格数据
        
        Args:
            code: ETF代码（如510300）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key("etf_price", code, start_date, end_date)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
                
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=500)  # 默认获取500天数据
                
            # 转换日期格式
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            # 判断市场（上海或深圳）
            market = "sh" if code.startswith(("51", "58")) else "sz"
            symbol = f"{market}{code}"
            
            # 获取ETF历史数据
            logger.debug(f"Fetching ETF price data for {symbol} from {start_str} to {end_str}")
            df = ak.fund_etf_hist_sina(symbol=symbol, start_date=start_str, end_date=end_str)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for ETF {code}")
                return pd.DataFrame()
                
            # 重命名列以符合标准格式
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
            
            # 确保日期列为datetime类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 数据验证
            if self.validate_data(df):
                # 缓存数据
                self._save_to_cache(cache_key, df)
                logger.info(f"Successfully fetched {len(df)} rows of ETF price data for {code}")
                return df
            else:
                logger.error(f"Data validation failed for ETF {code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching ETF price data for {code}: {str(e)}")
            return pd.DataFrame()
            
    def get_etf_realtime(self, code: str) -> Dict[str, Any]:
        """
        获取ETF实时行情
        
        Args:
            code: ETF代码
            
        Returns:
            Dict containing: price, change, change_pct, volume, amount, time
        """
        try:
            # 生成缓存键（实时数据缓存时间更短）
            cache_key = self._get_cache_key("etf_realtime", code)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
                
            # 判断市场
            market = "sh" if code.startswith(("51", "58")) else "sz"
            symbol = f"{market}{code}"
            
            # 获取实时行情
            logger.debug(f"Fetching realtime data for ETF {symbol}")
            df = ak.fund_etf_spot_em()
            
            # 筛选特定ETF
            etf_data = df[df['代码'] == code]
            
            if etf_data.empty:
                logger.warning(f"No realtime data found for ETF {code}")
                return {}
                
            row = etf_data.iloc[0]
            
            result = {
                'code': code,
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'change': float(row.get('涨跌额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 缓存数据（实时数据缓存30秒）
            old_ttl = self.cache_ttl
            self.cache_ttl = 30
            self._save_to_cache(cache_key, result)
            self.cache_ttl = old_ttl
            
            logger.info(f"Successfully fetched realtime data for ETF {code}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching realtime data for ETF {code}: {str(e)}")
            return {}
            
    def get_convertible_bond_info(self, code: str) -> Dict[str, Any]:
        """
        获取可转债信息
        
        Args:
            code: 可转债代码
            
        Returns:
            Dict containing bond information
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key("cb_info", code)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
                
            # 获取可转债列表
            logger.debug(f"Fetching convertible bond info for {code}")
            df = ak.bond_zh_hs_cov_spot()
            
            # 筛选特定可转债
            cb_data = df[df['code'] == code]
            
            if cb_data.empty:
                logger.warning(f"No info found for convertible bond {code}")
                return {}
                
            row = cb_data.iloc[0]
            
            result = {
                'code': code,
                'name': row.get('名称', ''),
                'price': float(row.get('最新价', 0)),
                'premium_rate': float(row.get('转股溢价率', 0)),
                'stock_price': float(row.get('正股价', 0)),
                'conversion_price': float(row.get('转股价', 0)),
                'conversion_value': float(row.get('转股价值', 0)),
                'ytm': float(row.get('到期收益率', 0)) if '到期收益率' in row else 0,
                'rating': row.get('债券评级', ''),
                'remaining_years': float(row.get('剩余年限', 0)) if '剩余年限' in row else 0
            }
            
            # 缓存数据
            self._save_to_cache(cache_key, result)
            logger.info(f"Successfully fetched info for convertible bond {code}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching convertible bond info for {code}: {str(e)}")
            return {}
            
    def get_convertible_bond_price(self, code: str, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取可转债价格数据
        
        Args:
            code: 可转债代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with price data
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key("cb_price", code, start_date, end_date)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
                
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=250)
                
            # 转换日期格式
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            # 获取可转债历史数据
            logger.debug(f"Fetching convertible bond price data for {code}")
            df = ak.bond_zh_hs_cov_daily(symbol=code, start_date=start_str, end_date=end_str)
            
            if df is None or df.empty:
                logger.warning(f"No data returned for convertible bond {code}")
                return pd.DataFrame()
                
            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘价': 'open',
                '最高价': 'high',
                '最低价': 'low',
                '收盘价': 'close',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            # 确保日期列为datetime类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 缓存数据
            self._save_to_cache(cache_key, df)
            logger.info(f"Successfully fetched {len(df)} rows of convertible bond price data for {code}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching convertible bond price data for {code}: {str(e)}")
            return pd.DataFrame()
            
    def get_index_price(self, code: str, start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取指数价格数据
        
        Args:
            code: 指数代码（如000300表示沪深300）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with index price data
        """
        try:
            # 生成缓存键
            cache_key = self._get_cache_key("index_price", code, start_date, end_date)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
                
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=500)
                
            # 转换日期格式
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            # 获取指数历史数据
            logger.debug(f"Fetching index price data for {code}")
            
            # 根据指数代码选择合适的接口
            if code == "000300":  # 沪深300
                df = ak.index_zh_a_hist(symbol="000300", period="daily", 
                                       start_date=start_str, end_date=end_str)
            elif code == "000016":  # 上证50
                df = ak.index_zh_a_hist(symbol="000016", period="daily",
                                       start_date=start_str, end_date=end_str)
            else:
                df = ak.index_zh_a_hist(symbol=code, period="daily",
                                       start_date=start_str, end_date=end_str)
                                       
            if df is None or df.empty:
                logger.warning(f"No data returned for index {code}")
                return pd.DataFrame()
                
            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount'
            })
            
            # 确保日期列为datetime类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 数据验证
            if self.validate_data(df):
                # 缓存数据
                self._save_to_cache(cache_key, df)
                logger.info(f"Successfully fetched {len(df)} rows of index price data for {code}")
                return df
            else:
                logger.error(f"Data validation failed for index {code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error fetching index price data for {code}: {str(e)}")
            return pd.DataFrame()
            
    def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF列表
        
        Returns:
            DataFrame with ETF list
        """
        try:
            logger.debug("Fetching ETF list")
            df = ak.fund_etf_category_sina()
            logger.info(f"Successfully fetched {len(df)} ETFs")
            return df
        except Exception as e:
            logger.error(f"Error fetching ETF list: {str(e)}")
            return pd.DataFrame()