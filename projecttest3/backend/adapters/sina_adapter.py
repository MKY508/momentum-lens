"""
Sina Finance data adapter implementation
新浪财经数据适配器实现
"""
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
import pandas as pd
import requests
from loguru import logger

from .base import DataAdapter, DataQuality


class SinaAdapter(DataAdapter):
    """
    新浪财经数据适配器
    作为备用数据源
    """
    
    def __init__(self):
        super().__init__(name="Sina", quality=DataQuality.MEDIUM)
        self.base_url = "http://hq.sinajs.cn"
        logger.info("Initialized Sina adapter")
        
    def _parse_sina_response(self, response_text: str) -> Dict[str, Any]:
        """解析新浪财经响应数据"""
        try:
            # 新浪返回格式: var hq_str_sh510300="沪深300ETF,3.721,3.725,..."
            if "hq_str" not in response_text:
                return {}
                
            data_str = response_text.split('"')[1]
            if not data_str or data_str == "":
                return {}
                
            fields = data_str.split(',')
            if len(fields) < 32:
                return {}
                
            return {
                'name': fields[0],
                'open': float(fields[1]),
                'prev_close': float(fields[2]),
                'price': float(fields[3]),
                'high': float(fields[4]),
                'low': float(fields[5]),
                'volume': float(fields[8]) if fields[8] else 0,
                'amount': float(fields[9]) if fields[9] else 0,
                'date': fields[30],
                'time': fields[31]
            }
        except Exception as e:
            logger.error(f"Error parsing Sina response: {str(e)}")
            return {}
            
    def get_etf_price(self, code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取ETF历史价格数据
        注：新浪财经主要提供实时数据，历史数据能力有限
        """
        logger.warning(f"Sina adapter has limited historical data capability for ETF {code}")
        
        # 新浪财经历史数据接口有限，这里返回空DataFrame
        # 实际使用中应该降级到其他数据源
        return pd.DataFrame()
        
    def get_etf_realtime(self, code: str) -> Dict[str, Any]:
        """
        获取ETF实时行情
        """
        try:
            # 判断市场
            market = "sh" if code.startswith(("51", "58")) else "sz"
            symbol = f"{market}{code}"
            
            # 构建请求URL
            url = f"{self.base_url}/list={symbol}"
            
            logger.debug(f"Fetching realtime data from Sina for {symbol}")
            response = requests.get(url, timeout=5)
            response.encoding = 'gbk'
            
            if response.status_code != 200:
                logger.error(f"Sina API returned status code {response.status_code}")
                return {}
                
            # 解析响应
            data = self._parse_sina_response(response.text)
            
            if not data:
                return {}
                
            # 计算涨跌额和涨跌幅
            change = data['price'] - data.get('prev_close', data['price'])
            change_pct = (change / data.get('prev_close', data['price'])) * 100 if data.get('prev_close', 0) != 0 else 0
            
            result = {
                'code': code,
                'name': data.get('name', ''),
                'price': data.get('price', 0),
                'change': change,
                'change_pct': change_pct,
                'volume': data.get('volume', 0),
                'amount': data.get('amount', 0),
                'time': f"{data.get('date', '')} {data.get('time', '')}"
            }
            
            logger.info(f"Successfully fetched realtime data from Sina for {code}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching realtime data from Sina for {code}: {str(e)}")
            return {}
            
    def get_convertible_bond_info(self, code: str) -> Dict[str, Any]:
        """
        获取可转债信息
        注：新浪财经可转债数据有限
        """
        logger.warning(f"Sina adapter has limited convertible bond data for {code}")
        return {}
        
    def get_convertible_bond_price(self, code: str, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取可转债价格数据
        """
        logger.warning(f"Sina adapter has limited convertible bond historical data for {code}")
        return pd.DataFrame()
        
    def get_index_price(self, code: str, start_date: Optional[date] = None,
                       end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取指数价格数据
        """
        logger.warning(f"Sina adapter has limited index historical data for {code}")
        return pd.DataFrame()