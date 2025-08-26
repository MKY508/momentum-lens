"""
Data adapters for Momentum Lens
数据适配器模块
"""
from .base import DataAdapter, DataQuality
from .akshare_adapter import AkShareAdapter
from .sina_adapter import SinaAdapter
from .eastmoney_adapter import EastmoneyAdapter
from .adapter_manager import AdapterManager

__all__ = [
    'DataAdapter',
    'DataQuality',
    'AkShareAdapter', 
    'SinaAdapter',
    'EastmoneyAdapter',
    'AdapterManager'
]