"""
Adapter manager with fallback strategy
适配器管理器，实现降级策略
"""
from typing import Optional, Dict, List, Any
from datetime import date
import pandas as pd
from loguru import logger

from .base import DataAdapter, DataQuality
from .akshare_adapter import AkShareAdapter
from .sina_adapter import SinaAdapter
from .eastmoney_adapter import EastmoneyAdapter


class AdapterManager:
    """
    适配器管理器
    实现数据源降级策略和自动切换
    """
    
    def __init__(self):
        """初始化适配器管理器"""
        self.adapters: List[DataAdapter] = []
        self.current_adapter: Optional[DataAdapter] = None
        self._init_adapters()
        
    def _init_adapters(self):
        """初始化所有数据适配器"""
        try:
            # 按优先级顺序初始化适配器
            # 1. AkShare (主数据源)
            try:
                akshare = AkShareAdapter()
                self.adapters.append(akshare)
                self.current_adapter = akshare
                logger.info("AkShare adapter initialized as primary source")
            except Exception as e:
                logger.error(f"Failed to initialize AkShare adapter: {str(e)}")
                
            # 2. Sina (备用源1)
            try:
                sina = SinaAdapter()
                self.adapters.append(sina)
                logger.info("Sina adapter initialized as fallback source")
            except Exception as e:
                logger.error(f"Failed to initialize Sina adapter: {str(e)}")
                
            # 3. Eastmoney (备用源2)
            try:
                eastmoney = EastmoneyAdapter()
                self.adapters.append(eastmoney)
                logger.info("Eastmoney adapter initialized as secondary fallback")
            except Exception as e:
                logger.error(f"Failed to initialize Eastmoney adapter: {str(e)}")
                
            if not self.adapters:
                raise RuntimeError("No data adapters available")
                
            if not self.current_adapter and self.adapters:
                self.current_adapter = self.adapters[0]
                
        except Exception as e:
            logger.error(f"Critical error initializing adapters: {str(e)}")
            raise
            
    def get_etf_price(self, code: str, start_date: Optional[date] = None,
                      end_date: Optional[date] = None, allow_fallback: bool = True) -> pd.DataFrame:
        """
        获取ETF价格数据，支持自动降级
        
        Args:
            code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            allow_fallback: 是否允许降级到备用源
            
        Returns:
            DataFrame with price data
        """
        if not self.adapters:
            logger.error("No adapters available")
            return pd.DataFrame()
            
        # 尝试从各个数据源获取数据
        for adapter in self.adapters:
            try:
                logger.debug(f"Trying to fetch ETF price from {adapter.name}")
                df = adapter.get_etf_price(code, start_date, end_date)
                
                if df is not None and not df.empty:
                    # 数据获取成功
                    logger.info(f"Successfully fetched ETF price from {adapter.name} "
                              f"(quality: {adapter.quality.value})")
                    
                    # 如果使用了降级源，添加质量标记
                    if adapter.quality != DataQuality.HIGH:
                        df['data_quality'] = adapter.quality.value
                        
                    return df
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {adapter.name}: {str(e)}")
                
            if not allow_fallback:
                break
                
        logger.error(f"Failed to fetch ETF price for {code} from all sources")
        return pd.DataFrame()
        
    def get_etf_realtime(self, code: str, allow_fallback: bool = True) -> Dict[str, Any]:
        """
        获取ETF实时行情，支持自动降级
        
        Args:
            code: ETF代码
            allow_fallback: 是否允许降级
            
        Returns:
            Dict with realtime data
        """
        if not self.adapters:
            logger.error("No adapters available")
            return {}
            
        # 尝试从各个数据源获取数据
        for adapter in self.adapters:
            try:
                logger.debug(f"Trying to fetch realtime data from {adapter.name}")
                data = adapter.get_etf_realtime(code)
                
                if data:
                    # 数据获取成功
                    logger.info(f"Successfully fetched realtime data from {adapter.name} "
                              f"(quality: {adapter.quality.value})")
                    
                    # 添加数据质量标记
                    data['data_quality'] = adapter.quality.value
                    return data
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {adapter.name}: {str(e)}")
                
            if not allow_fallback:
                break
                
        logger.error(f"Failed to fetch realtime data for {code} from all sources")
        return {}
        
    def get_convertible_bond_info(self, code: str, allow_fallback: bool = True) -> Dict[str, Any]:
        """
        获取可转债信息，支持自动降级
        
        Args:
            code: 可转债代码
            allow_fallback: 是否允许降级
            
        Returns:
            Dict with bond info
        """
        if not self.adapters:
            logger.error("No adapters available")
            return {}
            
        for adapter in self.adapters:
            try:
                logger.debug(f"Trying to fetch convertible bond info from {adapter.name}")
                data = adapter.get_convertible_bond_info(code)
                
                if data:
                    logger.info(f"Successfully fetched bond info from {adapter.name}")
                    data['data_quality'] = adapter.quality.value
                    return data
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {adapter.name}: {str(e)}")
                
            if not allow_fallback:
                break
                
        logger.error(f"Failed to fetch convertible bond info for {code} from all sources")
        return {}
        
    def get_convertible_bond_price(self, code: str, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None, 
                                  allow_fallback: bool = True) -> pd.DataFrame:
        """
        获取可转债价格数据，支持自动降级
        
        Args:
            code: 可转债代码
            start_date: 开始日期
            end_date: 结束日期
            allow_fallback: 是否允许降级
            
        Returns:
            DataFrame with price data
        """
        if not self.adapters:
            logger.error("No adapters available")
            return pd.DataFrame()
            
        for adapter in self.adapters:
            try:
                logger.debug(f"Trying to fetch convertible bond price from {adapter.name}")
                df = adapter.get_convertible_bond_price(code, start_date, end_date)
                
                if df is not None and not df.empty:
                    logger.info(f"Successfully fetched bond price from {adapter.name}")
                    
                    if adapter.quality != DataQuality.HIGH:
                        df['data_quality'] = adapter.quality.value
                        
                    return df
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {adapter.name}: {str(e)}")
                
            if not allow_fallback:
                break
                
        logger.error(f"Failed to fetch convertible bond price for {code} from all sources")
        return pd.DataFrame()
        
    def get_index_price(self, code: str, start_date: Optional[date] = None,
                       end_date: Optional[date] = None, 
                       allow_fallback: bool = True) -> pd.DataFrame:
        """
        获取指数价格数据，支持自动降级
        
        Args:
            code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            allow_fallback: 是否允许降级
            
        Returns:
            DataFrame with index price data
        """
        if not self.adapters:
            logger.error("No adapters available")
            return pd.DataFrame()
            
        for adapter in self.adapters:
            try:
                logger.debug(f"Trying to fetch index price from {adapter.name}")
                df = adapter.get_index_price(code, start_date, end_date)
                
                if df is not None and not df.empty:
                    logger.info(f"Successfully fetched index price from {adapter.name} "
                              f"(quality: {adapter.quality.value})")
                    
                    if adapter.quality != DataQuality.HIGH:
                        df['data_quality'] = adapter.quality.value
                        
                    return df
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {adapter.name}: {str(e)}")
                
            if not allow_fallback:
                break
                
        logger.error(f"Failed to fetch index price for {code} from all sources")
        return pd.DataFrame()
        
    def get_current_adapter(self) -> Optional[DataAdapter]:
        """获取当前使用的适配器"""
        return self.current_adapter
        
    def set_adapter(self, adapter_name: str) -> bool:
        """
        手动设置使用的适配器
        
        Args:
            adapter_name: 适配器名称
            
        Returns:
            bool: 设置是否成功
        """
        for adapter in self.adapters:
            if adapter.name.lower() == adapter_name.lower():
                self.current_adapter = adapter
                logger.info(f"Switched to {adapter_name} adapter")
                return True
                
        logger.error(f"Adapter {adapter_name} not found")
        return False
        
    def get_available_adapters(self) -> List[str]:
        """获取可用的适配器列表"""
        return [adapter.name for adapter in self.adapters]
        
    def clear_all_cache(self):
        """清空所有适配器的缓存"""
        for adapter in self.adapters:
            adapter.clear_cache()
        logger.info("All adapter caches cleared")