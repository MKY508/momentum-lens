"""数据源适配器模块 - 支持多数据源的统一接口"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from functools import lru_cache
import akshare as ak
import logging
from enum import Enum
import asyncio
import json
import hashlib

logger = logging.getLogger(__name__)


class DataQuality(Enum):
    """数据质量枚举"""
    HIGH = "high"       # 高质量，无异常
    MEDIUM = "medium"   # 中等质量，有少量缺失
    LOW = "low"         # 低质量，需要清洗
    INVALID = "invalid" # 无效数据


class DataSourceInterface(ABC):
    """数据源接口抽象类"""
    
    @abstractmethod
    async def get_etf_list(self) -> pd.DataFrame:
        """获取ETF列表"""
        pass
    
    @abstractmethod
    async def get_etf_price(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取ETF价格数据"""
        pass
    
    @abstractmethod
    async def get_etf_iopv(self, code: str) -> Dict[str, float]:
        """获取ETF的IOPV数据"""
        pass
    
    @abstractmethod
    async def get_convertible_bonds(self) -> pd.DataFrame:
        """获取可转债列表"""
        pass
    
    @abstractmethod
    async def get_cb_price(self, code: str) -> Dict[str, Any]:
        """获取可转债价格数据"""
        pass
    
    @abstractmethod
    async def get_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指数数据"""
        pass
    
    @abstractmethod
    def validate_data_quality(self, data: pd.DataFrame) -> DataQuality:
        """验证数据质量"""
        pass


class AKShareAdapter(DataSourceInterface):
    """AKShare数据源适配器"""
    
    def __init__(self, cache_ttl: int = 300):
        """
        初始化AKShare适配器
        
        Args:
            cache_ttl: 缓存时间(秒)
        """
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}
        
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{method}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache_timestamps:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamps[cache_key]).seconds
        return elapsed < self.cache_ttl
    
    async def get_etf_list(self) -> pd.DataFrame:
        """
        获取ETF列表
        
        Returns:
            ETF列表DataFrame，包含代码、名称、成交额等信息
        """
        cache_key = self._get_cache_key("get_etf_list")
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 获取ETF列表
            df = await asyncio.to_thread(ak.fund_etf_spot_em)
            
            # 数据清洗和转换
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '最高': 'high',
                '最低': 'low',
                '开盘': 'open',
                '昨收': 'prev_close'
            })
            
            # 转换数据类型
            numeric_columns = ['price', 'change_pct', 'volume', 'turnover', 
                              'amplitude', 'high', 'low', 'open', 'prev_close']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 过滤无效数据
            df = df.dropna(subset=['code', 'name', 'price'])
            
            # 缓存数据
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.info(f"成功获取{len(df)}只ETF数据")
            return df
            
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            raise
    
    async def get_etf_price(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取ETF价格数据
        
        Args:
            code: ETF代码
            start_date: 开始日期(YYYY-MM-DD)
            end_date: 结束日期(YYYY-MM-DD)
            
        Returns:
            价格数据DataFrame
        """
        cache_key = self._get_cache_key("get_etf_price", code, start_date, end_date)
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 获取ETF历史数据
            df = await asyncio.to_thread(
                ak.fund_etf_hist_em,
                symbol=code,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"  # 前复权
            )
            
            # 重命名列
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover_rate'
            })
            
            # 设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            # 数据质量检查
            quality = self.validate_data_quality(df)
            if quality == DataQuality.INVALID:
                raise ValueError(f"ETF {code} 数据质量无效")
            
            # 缓存数据
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = datetime.now()
            
            return df
            
        except Exception as e:
            logger.error(f"获取ETF {code} 价格数据失败: {e}")
            raise
    
    async def get_etf_iopv(self, code: str) -> Dict[str, float]:
        """
        获取ETF的IOPV数据
        
        Args:
            code: ETF代码
            
        Returns:
            包含IOPV和溢价率的字典
        """
        try:
            # 获取实时数据
            spot_data = await asyncio.to_thread(ak.fund_etf_spot_em)
            etf_row = spot_data[spot_data['代码'] == code]
            
            if etf_row.empty:
                raise ValueError(f"未找到ETF {code}")
            
            # 获取IOPV数据（这里需要根据实际情况调整）
            # AKShare可能没有直接的IOPV接口，需要从其他来源获取或计算
            current_price = float(etf_row.iloc[0]['最新价'])
            
            # 模拟IOPV计算（实际应该从数据源获取）
            iopv = current_price * 0.998  # 临时模拟值
            premium_rate = (current_price - iopv) / iopv
            
            return {
                'code': code,
                'price': current_price,
                'iopv': iopv,
                'premium_rate': premium_rate,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取ETF {code} IOPV数据失败: {e}")
            raise
    
    async def get_convertible_bonds(self) -> pd.DataFrame:
        """
        获取可转债列表
        
        Returns:
            可转债列表DataFrame
        """
        cache_key = self._get_cache_key("get_convertible_bonds")
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 获取可转债数据
            df = await asyncio.to_thread(ak.bond_zh_hs_cov_spot)
            
            # 重命名列
            df = df.rename(columns={
                'symbol': 'code',
                'name': 'name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '成交量': 'volume',
                '成交额': 'turnover',
                '转股溢价率': 'premium_rate',
                '转股价': 'conversion_price',
                '转股价值': 'conversion_value',
                '债券余额': 'balance',
                '剩余年限': 'remaining_years',
                '债券评级': 'rating'
            })
            
            # 数据类型转换 - 只处理存在的列
            numeric_cols = ['price', 'change_pct', 'volume', 'turnover', 
                           'premium_rate', 'conversion_price', 'conversion_value',
                           'balance', 'remaining_years']
            
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 过滤无效数据 - 检查列是否存在
            required_cols = ['code', 'name', 'price']
            existing_required = [col for col in required_cols if col in df.columns]
            
            if existing_required:
                # 只对存在的必需列进行筛选
                df = df.dropna(subset=existing_required)
            else:
                # 如果没有必需列，至少保留有数据的行
                df = df.dropna(how='all')
            
            # 缓存数据
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.info(f"成功获取{len(df)}只可转债数据")
            return df
            
        except Exception as e:
            logger.error(f"获取可转债列表失败: {e}")
            raise
    
    async def get_cb_price(self, code: str) -> Dict[str, Any]:
        """
        获取可转债价格数据
        
        Args:
            code: 可转债代码
            
        Returns:
            可转债价格信息字典
        """
        try:
            # 获取可转债列表
            cb_list = await self.get_convertible_bonds()
            cb_row = cb_list[cb_list['code'] == code]
            
            if cb_row.empty:
                raise ValueError(f"未找到可转债 {code}")
            
            cb_data = cb_row.iloc[0].to_dict()
            cb_data['timestamp'] = datetime.now().isoformat()
            
            return cb_data
            
        except Exception as e:
            logger.error(f"获取可转债 {code} 价格数据失败: {e}")
            raise
    
    async def get_index_data(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指数数据
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指数数据DataFrame
        """
        cache_key = self._get_cache_key("get_index_data", index_code, start_date, end_date)
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 获取指数历史数据
            df = await asyncio.to_thread(
                ak.stock_zh_index_daily,
                symbol=index_code
            )
            
            # 过滤日期范围
            df['date'] = pd.to_datetime(df['date'])
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
            
            # 重命名列
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # 设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            # 缓存数据
            self._cache[cache_key] = df
            self._cache_timestamps[cache_key] = datetime.now()
            
            return df
            
        except Exception as e:
            logger.error(f"获取指数 {index_code} 数据失败: {e}")
            raise
    
    def validate_data_quality(self, data: pd.DataFrame) -> DataQuality:
        """
        验证数据质量
        
        Args:
            data: 待验证的DataFrame
            
        Returns:
            数据质量评级
        """
        if data.empty:
            return DataQuality.INVALID
        
        # 检查缺失值比例
        missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
        
        if missing_ratio > 0.3:
            return DataQuality.INVALID
        elif missing_ratio > 0.1:
            return DataQuality.LOW
        elif missing_ratio > 0.01:
            return DataQuality.MEDIUM
        else:
            # 检查数据连续性（对于时间序列数据）
            if 'date' in data.index.names or 'date' in data.columns:
                # 这里可以添加更多的连续性检查
                pass
            
            return DataQuality.HIGH


class DataSourceFactory:
    """数据源工厂类"""
    
    _instances = {}
    
    @classmethod
    def get_datasource(cls, provider: str = "akshare", **kwargs) -> DataSourceInterface:
        """
        获取数据源实例
        
        Args:
            provider: 数据源提供商
            **kwargs: 额外参数
            
        Returns:
            数据源实例
        """
        if provider not in cls._instances:
            if provider == "akshare":
                cls._instances[provider] = AKShareAdapter(**kwargs)
            else:
                raise ValueError(f"不支持的数据源: {provider}")
        
        return cls._instances[provider]


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def cross_validate(data1: pd.DataFrame, data2: pd.DataFrame, 
                       tolerance: float = 0.01) -> bool:
        """
        交叉验证两个数据源的数据
        
        Args:
            data1: 第一个数据源
            data2: 第二个数据源
            tolerance: 容差
            
        Returns:
            是否验证通过
        """
        try:
            # 对齐索引
            common_index = data1.index.intersection(data2.index)
            if len(common_index) == 0:
                return False
            
            # 比较数值列
            numeric_cols1 = data1.select_dtypes(include=[np.number]).columns
            numeric_cols2 = data2.select_dtypes(include=[np.number]).columns
            common_cols = numeric_cols1.intersection(numeric_cols2)
            
            for col in common_cols:
                diff = abs(data1.loc[common_index, col] - data2.loc[common_index, col])
                max_diff = diff.max()
                
                if max_diff > tolerance * data1.loc[common_index, col].abs().mean():
                    logger.warning(f"列 {col} 数据差异过大: {max_diff}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"数据交叉验证失败: {e}")
            return False