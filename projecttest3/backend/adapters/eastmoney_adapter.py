"""
East Money data adapter implementation
东方财富数据适配器实现
"""
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
import requests
import json
from loguru import logger

from .base import DataAdapter, DataQuality


class EastmoneyAdapter(DataAdapter):
    """
    东方财富数据适配器
    作为第二备用数据源
    """
    
    def __init__(self):
        super().__init__(name="Eastmoney", quality=DataQuality.LOW)
        self.base_url = "http://push2his.eastmoney.com"
        self.realtime_url = "http://push2.eastmoney.com"
        logger.info("Initialized Eastmoney adapter")
        
    def get_etf_price(self, code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取ETF历史价格数据
        """
        try:
            # 判断市场
            secid = f"0.{code}" if code.startswith("15") else f"1.{code}"
            
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=250)
                
            # 构建请求参数
            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101',  # 日K线
                'fqt': '1',
                'beg': start_date.strftime("%Y%m%d"),
                'end': end_date.strftime("%Y%m%d"),
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            url = f"{self.base_url}/api/qt/stock/kline/get"
            
            logger.debug(f"Fetching ETF price from Eastmoney for {code}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Eastmoney API returned status code {response.status_code}")
                return pd.DataFrame()
                
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                
                # 解析K线数据
                records = []
                for kline in klines:
                    fields = kline.split(',')
                    if len(fields) >= 11:
                        records.append({
                            'date': pd.to_datetime(fields[0]),
                            'open': float(fields[1]),
                            'close': float(fields[2]),
                            'high': float(fields[3]),
                            'low': float(fields[4]),
                            'volume': float(fields[5]),
                            'amount': float(fields[6]) if len(fields) > 6 else 0
                        })
                        
                df = pd.DataFrame(records)
                
                if self.validate_data(df):
                    logger.info(f"Successfully fetched {len(df)} rows from Eastmoney for {code}")
                    return df
                    
            logger.warning(f"No valid data from Eastmoney for {code}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching ETF price from Eastmoney for {code}: {str(e)}")
            return pd.DataFrame()
            
    def get_etf_realtime(self, code: str) -> Dict[str, Any]:
        """
        获取ETF实时行情
        """
        try:
            # 判断市场
            secid = f"0.{code}" if code.startswith("15") else f"1.{code}"
            
            # 构建请求参数
            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'invt': '2',
                'fltt': '2',
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18',
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            url = f"{self.realtime_url}/api/qt/stock/get"
            
            logger.debug(f"Fetching realtime data from Eastmoney for {code}")
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code != 200:
                logger.error(f"Eastmoney API returned status code {response.status_code}")
                return {}
                
            data = response.json()
            
            if data.get('data'):
                stock_data = data['data']
                
                result = {
                    'code': code,
                    'name': stock_data.get('f58', ''),
                    'price': float(stock_data.get('f2', 0)) / 1000 if stock_data.get('f2') else 0,
                    'change': float(stock_data.get('f4', 0)) / 1000 if stock_data.get('f4') else 0,
                    'change_pct': float(stock_data.get('f3', 0)) / 100 if stock_data.get('f3') else 0,
                    'volume': float(stock_data.get('f5', 0)),
                    'amount': float(stock_data.get('f6', 0)),
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                logger.info(f"Successfully fetched realtime data from Eastmoney for {code}")
                return result
                
            logger.warning(f"No realtime data from Eastmoney for {code}")
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching realtime data from Eastmoney for {code}: {str(e)}")
            return {}
            
    def get_convertible_bond_info(self, code: str) -> Dict[str, Any]:
        """
        获取可转债信息
        """
        logger.warning(f"Eastmoney adapter has limited convertible bond data for {code}")
        return {}
        
    def get_convertible_bond_price(self, code: str, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取可转债价格数据
        """
        logger.warning(f"Eastmoney adapter has limited convertible bond historical data for {code}")
        return pd.DataFrame()
        
    def get_index_price(self, code: str, start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取指数价格数据
        """
        try:
            # 指数代码映射
            index_map = {
                "000300": "1.000300",  # 沪深300
                "000016": "1.000016",  # 上证50
                "000905": "1.000905",  # 中证500
            }
            
            secid = index_map.get(code, f"1.{code}")
            
            # 设置默认日期范围
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=250)
                
            # 构建请求参数
            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                'klt': '101',
                'fqt': '1',
                'beg': start_date.strftime("%Y%m%d"),
                'end': end_date.strftime("%Y%m%d"),
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            url = f"{self.base_url}/api/qt/stock/kline/get"
            
            logger.debug(f"Fetching index price from Eastmoney for {code}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Eastmoney API returned status code {response.status_code}")
                return pd.DataFrame()
                
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                
                # 解析K线数据
                records = []
                for kline in klines:
                    fields = kline.split(',')
                    if len(fields) >= 11:
                        records.append({
                            'date': pd.to_datetime(fields[0]),
                            'open': float(fields[1]),
                            'close': float(fields[2]),
                            'high': float(fields[3]),
                            'low': float(fields[4]),
                            'volume': float(fields[5]),
                            'amount': float(fields[6]) if len(fields) > 6 else 0
                        })
                        
                df = pd.DataFrame(records)
                
                if self.validate_data(df):
                    logger.info(f"Successfully fetched {len(df)} rows of index data from Eastmoney for {code}")
                    return df
                    
            logger.warning(f"No valid index data from Eastmoney for {code}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching index price from Eastmoney for {code}: {str(e)}")
            return pd.DataFrame()