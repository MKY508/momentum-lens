"""
Base data adapter interface
数据适配器基类
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime, date
import pandas as pd
from loguru import logger


class DataQuality(Enum):
    """数据质量标记"""
    HIGH = "HIGH"     # 高质量（主数据源）
    MEDIUM = "MEDIUM" # 中等质量（备用源）
    LOW = "LOW"       # 低质量（降级源）
    UNKNOWN = "UNKNOWN"  # 未知质量


class DataAdapter(ABC):
    """
    数据适配器抽象基类
    定义统一的数据获取接口
    """
    
    def __init__(self, name: str, quality: DataQuality = DataQuality.UNKNOWN):
        """
        初始化适配器
        
        Args:
            name: 适配器名称
            quality: 数据质量等级
        """
        self.name = name
        self.quality = quality
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self.cache_ttl = 300  # 默认缓存5分钟
        
    @abstractmethod
    def get_etf_price(self, code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> pd.DataFrame:
        """
        获取ETF价格数据
        
        Args:
            code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        pass
        
    @abstractmethod
    def get_etf_realtime(self, code: str) -> Dict[str, Any]:
        """
        获取ETF实时行情
        
        Args:
            code: ETF代码
            
        Returns:
            Dict containing: price, change, change_pct, volume, amount, time
        """
        pass
        
    @abstractmethod
    def get_convertible_bond_info(self, code: str) -> Dict[str, Any]:
        """
        获取可转债信息
        
        Args:
            code: 可转债代码
            
        Returns:
            Dict containing bond information
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
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
        pass
        
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        验证数据质量
        
        Args:
            df: 待验证的数据
            
        Returns:
            bool: 数据是否有效
        """
        if df is None or df.empty:
            return False
            
        # 检查必要列
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logger.warning(f"Missing required columns in data from {self.name}")
            return False
            
        # 检查数据完整性
        if df.isnull().any().any():
            null_counts = df.isnull().sum()
            logger.warning(f"Null values found in data from {self.name}: {null_counts[null_counts > 0].to_dict()}")
            
        # 检查价格合理性
        if (df['high'] < df['low']).any():
            logger.error(f"Invalid price data: high < low in {self.name}")
            return False
            
        if (df['close'] <= 0).any() or (df['open'] <= 0).any():
            logger.error(f"Invalid price data: zero or negative prices in {self.name}")
            return False
            
        return True
        
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """生成缓存键"""
        args_str = "_".join(str(arg) for arg in args)
        kwargs_str = "_".join(f"{k}_{v}" for k, v in sorted(kwargs.items()))
        return f"{method}_{args_str}_{kwargs_str}"
        
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if key in self._cache:
            cache_time = self._cache_time.get(key)
            if cache_time and (datetime.now() - cache_time).seconds < self.cache_ttl:
                logger.debug(f"Cache hit for {key}")
                return self._cache[key]
            else:
                # 缓存过期
                del self._cache[key]
                del self._cache_time[key]
        return None
        
    def _save_to_cache(self, key: str, data: Any) -> None:
        """保存数据到缓存"""
        self._cache[key] = data
        self._cache_time[key] = datetime.now()
        logger.debug(f"Data cached for {key}")
        
    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._cache_time.clear()
        logger.info(f"Cache cleared for {self.name}")