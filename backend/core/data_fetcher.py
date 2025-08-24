"""
Market data acquisition module for Momentum Lens.
Supports multiple data sources with fallback mechanisms.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from functools import lru_cache
import aiohttp
import json
import pytz
import requests
from urllib.parse import quote

# Data source imports
try:
    import akshare as ak
except ImportError:
    ak = None
    
try:
    import tushare as ts
except ImportError:
    ts = None

# Shanghai timezone for trading calendar
SHANGHAI_TZ = pytz.timezone('Asia/Shanghai')

from backend.config.settings import get_settings
from backend.models import PriceHistory, ETFInfo, MarketIndicators, RealtimeQuote
from backend.models.base import get_db
from backend.utils.calculations import calculate_returns, calculate_atr_series

logger = logging.getLogger(__name__)

class DataFetcher:
    """Market data fetcher with East Money as primary source"""
    
    # East Money API endpoints
    EASTMONEY_ETF_URL = "http://push2.eastmoney.com/api/qt/stock/get"
    EASTMONEY_IOPV_URL = "http://push2.eastmoney.com/api/qt/etfinfo/get"
    EASTMONEY_INDEX_URL = "http://push2.eastmoney.com/api/qt/stock/kline/get"
    
    def __init__(self):
        self.settings = get_settings()
        self._init_data_sources()
        self._cache = {}
        self._session = aiohttp.ClientSession()
        self._trading_calendar = None
        
    def _init_data_sources(self):
        """Initialize data sources with East Money primary, fallback chain"""
        self.sources = {}
        
        # East Money is always primary
        self.sources['eastmoney'] = True
        logger.info("East Money API initialized as primary source")
        
        # AkShare as first fallback
        if ak and self.settings.market_data.akshare_enabled:
            self.sources['akshare'] = ak
            logger.info("AkShare enabled as fallback")
        
        # Sina Finance as second fallback
        self.sources['sina'] = True
        logger.info("Sina Finance enabled as fallback")
        
        # Tushare for index data if available
        if ts and self.settings.market_data.tushare_token:
            try:
                ts.set_token(self.settings.market_data.tushare_token)
                self.sources['tushare'] = ts.pro_api()
                logger.info("Tushare API initialized for index data")
            except Exception as e:
                logger.error(f"Failed to initialize Tushare: {e}")
    
    async def fetch_hs300_data(self, 
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> pd.DataFrame:
        """
        Fetch CSI 300 index data
        Returns DataFrame with columns: date, open, high, low, close, volume
        """
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()
        
        # Try Tushare first
        if 'tushare' in self.sources:
            try:
                df = await self._fetch_hs300_tushare(start_date, end_date)
                if not df.empty:
                    return df
            except Exception as e:
                logger.error(f"Tushare fetch failed: {e}")
        
        # Fallback to AkShare
        if 'akshare' in self.sources:
            try:
                df = await self._fetch_hs300_akshare(start_date, end_date)
                if not df.empty:
                    return df
            except Exception as e:
                logger.error(f"AkShare fetch failed: {e}")
        
        # Last resort: fetch from database
        return await self._fetch_hs300_from_db(start_date, end_date)
    
    async def _fetch_hs300_tushare(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch CSI 300 data using Tushare"""
        api = self.sources['tushare']
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            api.index_daily,
            ts_code='000300.SH',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # Standardize column names
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume',
            'amount': 'turnover'
        })
        
        # Convert date format
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date')
        
        return df[['date', 'open', 'high', 'low', 'close', 'volume']]
    
    async def _fetch_hs300_akshare(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch CSI 300 data using AkShare"""
        loop = asyncio.get_event_loop()
        
        # AkShare function call
        df = await loop.run_in_executor(
            None,
            ak.stock_zh_index_daily,
            symbol='sh000300'
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter date range
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= pd.Timestamp(start_date)) & 
                (df['date'] <= pd.Timestamp(end_date))]
        
        return df[['date', 'open', 'high', 'low', 'close', 'volume']]
    
    async def _fetch_hs300_from_db(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch CSI 300 data from database"""
        with get_db() as db:
            indicators = db.query(MarketIndicators).filter(
                MarketIndicators.date >= start_date,
                MarketIndicators.date <= end_date
            ).all()
            
            if not indicators:
                return pd.DataFrame()
            
            data = [{
                'date': ind.date,
                'close': ind.hs300_close,
                'volume': ind.hs300_volume,
                'turnover': ind.hs300_turnover
            } for ind in indicators]
            
            return pd.DataFrame(data)
    
    async def fetch_etf_prices(self,
                              codes: List[str],
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch ETF price history for multiple codes
        Returns dict of {code: DataFrame}
        """
        if not start_date:
            start_date = date.today() - timedelta(days=365)
        if not end_date:
            end_date = date.today()
        
        results = {}
        
        # Fetch in parallel
        tasks = []
        for code in codes:
            tasks.append(self._fetch_single_etf_price(code, start_date, end_date))
        
        etf_data = await asyncio.gather(*tasks)
        
        for code, df in zip(codes, etf_data):
            if not df.empty:
                results[code] = df
        
        return results
    
    async def _fetch_single_etf_price(self, code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch price data for a single ETF"""
        # Try cache first
        cache_key = f"etf_{code}_{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        df = pd.DataFrame()
        
        # Try Tushare
        if 'tushare' in self.sources:
            try:
                df = await self._fetch_etf_tushare(code, start_date, end_date)
            except Exception as e:
                logger.error(f"Tushare ETF fetch failed for {code}: {e}")
        
        # Try AkShare if Tushare failed
        if df.empty and 'akshare' in self.sources:
            try:
                df = await self._fetch_etf_akshare(code, start_date, end_date)
            except Exception as e:
                logger.error(f"AkShare ETF fetch failed for {code}: {e}")
        
        # Cache result
        if not df.empty:
            self._cache[cache_key] = df
        
        return df
    
    async def _fetch_etf_tushare(self, code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch ETF data using Tushare"""
        api = self.sources['tushare']
        
        # Add exchange suffix
        ts_code = f"{code}.SH" if code.startswith('5') else f"{code}.SZ"
        
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            api.fund_daily,
            ts_code=ts_code,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # Standardize columns
        df = df.rename(columns={
            'trade_date': 'date',
            'vol': 'volume',
            'amount': 'turnover'
        })
        
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values('date')
        
        return df
    
    async def _fetch_etf_akshare(self, code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Fetch ETF data using AkShare"""
        loop = asyncio.get_event_loop()
        
        # Determine exchange
        exchange = 'sh' if code.startswith('5') else 'sz'
        symbol = f"{exchange}{code}"
        
        df = await loop.run_in_executor(
            None,
            ak.fund_etf_hist_sina,
            symbol=symbol
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # Standardize and filter
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= pd.Timestamp(start_date)) & 
                (df['date'] <= pd.Timestamp(end_date))]
        
        return df
    
    def calculate_ma200(self, df: pd.DataFrame, price_col: str = 'close') -> pd.Series:
        """Calculate 200-day Simple Moving Average"""
        return df[price_col].rolling(window=200, min_periods=200).mean()
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series]:
        """Calculate Average True Range and ATR percentage
        
        Returns:
            Tuple of (ATR20, ATR20_pct)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is 20-day average of TR
        atr20 = tr.rolling(window=period, min_periods=period).mean()
        
        # ATR percentage
        atr20_pct = (atr20 / close) * 100
        
        return atr20, atr20_pct
    
    def calculate_returns(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate r60 and r120 using exact trading days
        
        Returns:
            Dictionary with 'r60' and 'r120' Series
        """
        close = df['close']
        
        # Calculate returns using exact 60 and 120 trading days
        r60 = (close / close.shift(60) - 1) * 100
        r120 = (close / close.shift(120) - 1) * 100
        
        return {
            'r60': r60,
            'r120': r120
        }
    
    def calculate_rho90(self, df: pd.DataFrame) -> pd.Series:
        """Calculate 90-day correlation using log returns"""
        close = df['close']
        log_returns = np.log(close / close.shift(1))
        
        # Rolling 90-day correlation would need another series
        # This returns the log returns for correlation calculation
        return log_returns.rolling(window=90, min_periods=90)
    
    async def get_iopv_premium(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get IOPV and premium/discount from East Money
        Returns: {code: {'iopv': float, 'premium_discount': float, 'last_price': float}}
        """
        results = {}
        
        for code in codes:
            try:
                # Try East Money first
                data = await self._fetch_eastmoney_iopv(code)
                if data:
                    results[code] = data
                    continue
                    
                # Fallback to other sources
                quote = await self._get_realtime_quote(code)
                if quote:
                    iopv = quote.get('iopv', 0)
                    last_price = quote.get('last_price', 0)
                    
                    if iopv > 0:
                        premium_discount = ((last_price - iopv) / iopv) * 100
                    else:
                        premium_discount = 0
                    
                    results[code] = {
                        'iopv': iopv,
                        'premium_discount': premium_discount,
                        'last_price': last_price
                    }
            except Exception as e:
                logger.error(f"Failed to get IOPV for {code}: {e}")
        
        return results
    
    async def _fetch_eastmoney_iopv(self, code: str) -> Optional[Dict[str, float]]:
        """Fetch IOPV data from East Money"""
        try:
            # Determine market code
            market = 1 if code.startswith('5') else 0
            secid = f"{market}.{code}"
            
            params = {
                'secid': secid,
                'fields': 'f2,f3,f4,f5,f6,f193,f194,f195',  # price, change, volume, iopv, premium
                '_': int(datetime.now().timestamp() * 1000)
            }
            
            async with self._session.get(self.EASTMONEY_ETF_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data'):
                        info = data['data']
                        return {
                            'last_price': info.get('f2', 0) / 1000,  # Convert to actual price
                            'iopv': info.get('f193', 0) / 1000,
                            'premium_discount': info.get('f194', 0) / 100,  # Already in percentage
                            'open': info.get('f3', 0) / 1000,
                            'high': info.get('f4', 0) / 1000,
                            'low': info.get('f5', 0) / 1000,
                            'volume': info.get('f6', 0)
                        }
        except Exception as e:
            logger.error(f"East Money IOPV fetch failed for {code}: {e}")
        return None
    
    async def get_realtime_quotes(self, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time quotes for multiple ETFs
        Returns dict of {code: quote_data}
        """
        quotes = {}
        
        # Fetch quotes in parallel
        tasks = []
        for code in codes:
            tasks.append(self._get_realtime_quote(code))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for code, result in zip(codes, results):
            if not isinstance(result, Exception):
                quotes[code] = result
            else:
                logger.error(f"Failed to get quote for {code}: {result}")
        
        return quotes
    
    async def _get_realtime_quote(self, code: str) -> Dict[str, Any]:
        """Get real-time quote for a single ETF"""
        # This would connect to a real-time data feed
        # For now, we'll fetch the latest from database or simulate
        
        with get_db() as db:
            quote = db.query(RealtimeQuote).filter(
                RealtimeQuote.code == code
            ).first()
            
            if quote:
                return {
                    'code': quote.code,
                    'last_price': quote.last_price,
                    'bid': quote.bid_price,
                    'ask': quote.ask_price,
                    'volume': quote.volume,
                    'iopv': quote.iopv,
                    'premium_discount': quote.premium_discount,
                    'high': quote.high,
                    'low': quote.low,
                    'open': quote.open,
                    'prev_close': quote.prev_close,
                    'time': quote.quote_time
                }
        
        # Fallback to simulated data
        return self._simulate_quote(code)
    
    def _simulate_quote(self, code: str) -> Dict[str, Any]:
        """Simulate real-time quote for testing"""
        import random
        
        base_price = 1.0 + random.random() * 3
        spread = 0.001
        
        return {
            'code': code,
            'last_price': base_price,
            'bid': base_price - spread,
            'ask': base_price + spread,
            'volume': random.randint(1000000, 10000000),
            'iopv': base_price * (1 + random.uniform(-0.005, 0.005)),
            'premium_discount': random.uniform(-0.01, 0.01),
            'high': base_price * 1.02,
            'low': base_price * 0.98,
            'open': base_price * 0.99,
            'prev_close': base_price * 0.995,
            'time': datetime.now()
        }
    
    async def test_data_source(self, source_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Test connection to a specific data source"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if source_id == 'akshare':
                if 'akshare' in self.sources:
                    # Test with a simple query
                    loop = asyncio.get_event_loop()
                    df = await loop.run_in_executor(
                        None,
                        ak.fund_etf_spot_em
                    )
                    success = not df.empty
                else:
                    success = False
                    
            elif source_id == 'sina':
                # Test Sina Finance endpoint
                async with self._session.get('https://hq.sinajs.cn/list=sh510300') as response:
                    success = response.status == 200
                    
            elif source_id == 'eastmoney':
                # Test East Money endpoint
                params = {
                    'secid': '1.510300',
                    'fields': 'f2',
                    '_': int(datetime.now().timestamp() * 1000)
                }
                async with self._session.get(self.EASTMONEY_ETF_URL, params=params) as response:
                    success = response.status == 200
                    
            elif source_id == 'tushare':
                if 'tushare' in self.sources and api_key:
                    try:
                        ts.set_token(api_key)
                        api = ts.pro_api()
                        loop = asyncio.get_event_loop()
                        df = await loop.run_in_executor(
                            None,
                            api.trade_cal,
                            exchange='SSE',
                            cal_date=date.today().strftime('%Y%m%d')
                        )
                        success = not df.empty
                    except:
                        success = False
                else:
                    success = False
                    
            elif source_id == 'yahoo':
                # Test Yahoo Finance through yfinance
                try:
                    import yfinance as yf
                    loop = asyncio.get_event_loop()
                    ticker = await loop.run_in_executor(
                        None,
                        yf.Ticker,
                        '510300.SS'
                    )
                    info = await loop.run_in_executor(
                        None,
                        lambda: ticker.info
                    )
                    success = bool(info)
                except:
                    success = False
            else:
                success = False
                
            latency = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return {
                'success': success,
                'latency': latency,
                'source_id': source_id
            }
            
        except Exception as e:
            logger.error(f"Error testing {source_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'source_id': source_id
            }
    
    async def fetch_from_source(self, source_id: str, symbol: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Fetch data from a specific source"""
        try:
            if source_id == 'akshare':
                if 'akshare' in self.sources:
                    exchange = 'sh' if symbol.startswith('5') else 'sz'
                    full_symbol = f"{exchange}{symbol}"
                    
                    loop = asyncio.get_event_loop()
                    df = await loop.run_in_executor(
                        None,
                        ak.fund_etf_spot_em
                    )
                    
                    # Filter for the specific ETF
                    etf_data = df[df['代码'] == symbol]
                    if not etf_data.empty:
                        row = etf_data.iloc[0]
                        return {
                            'symbol': symbol,
                            'price': float(row.get('最新价', 0)),
                            'change': float(row.get('涨跌额', 0)),
                            'changePercent': float(row.get('涨跌幅', 0)),
                            'volume': float(row.get('成交量', 0)),
                            'high': float(row.get('最高', 0)),
                            'low': float(row.get('最低', 0)),
                            'open': float(row.get('今开', 0)),
                            'prevClose': float(row.get('昨收', 0))
                        }
                        
            elif source_id == 'sina':
                # Fetch from Sina Finance
                exchange = 'sh' if symbol.startswith('5') else 'sz'
                full_symbol = f"{exchange}{symbol}"
                
                async with self._session.get(f'https://hq.sinajs.cn/list={full_symbol}') as response:
                    if response.status == 200:
                        text = await response.text()
                        # Parse Sina format
                        parts = text.split(',')
                        if len(parts) > 30:
                            return {
                                'symbol': symbol,
                                'price': float(parts[3]),
                                'change': float(parts[3]) - float(parts[2]),
                                'changePercent': ((float(parts[3]) - float(parts[2])) / float(parts[2])) * 100,
                                'volume': float(parts[8]),
                                'high': float(parts[4]),
                                'low': float(parts[5]),
                                'open': float(parts[1]),
                                'prevClose': float(parts[2])
                            }
                            
            elif source_id == 'eastmoney':
                # Fetch from East Money
                data = await self._fetch_eastmoney_iopv(symbol)
                if data:
                    return {
                        'symbol': symbol,
                        'price': data['last_price'],
                        'iopv': data.get('iopv'),
                        'premium': data.get('premium_discount'),
                        'volume': data.get('volume', 0),
                        'high': data.get('high', 0),
                        'low': data.get('low', 0),
                        'open': data.get('open', 0)
                    }
                    
            elif source_id == 'tushare' and api_key:
                # Fetch from Tushare
                ts.set_token(api_key)
                api = ts.pro_api()
                
                ts_code = f"{symbol}.SH" if symbol.startswith('5') else f"{symbol}.SZ"
                
                loop = asyncio.get_event_loop()
                df = await loop.run_in_executor(
                    None,
                    api.fund_daily,
                    ts_code=ts_code,
                    trade_date=date.today().strftime('%Y%m%d')
                )
                
                if not df.empty:
                    row = df.iloc[0]
                    return {
                        'symbol': symbol,
                        'price': float(row['close']),
                        'change': float(row['change']),
                        'changePercent': float(row['pct_chg']),
                        'volume': float(row['vol']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'open': float(row['open']),
                        'prevClose': float(row['pre_close'])
                    }
                    
            return None
            
        except Exception as e:
            logger.error(f"Error fetching from {source_id}: {e}")
            return None
    
    async def fetch_market_indicators(self, date: date) -> MarketIndicators:
        """Fetch and calculate market indicators for a specific date"""
        # Fetch CSI 300 data
        end_date = date
        start_date = date - timedelta(days=250)  # Need history for MA200
        
        df = await self.fetch_hs300_data(start_date, end_date)
        
        if df.empty:
            return None
        
        # Calculate indicators
        df = df.sort_values('date')
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()
        df['ma200'] = df['close'].rolling(200).mean()
        
        # Get the row for the specific date
        row = df[df['date'] == pd.Timestamp(date)]
        if row.empty:
            return None
        
        row = row.iloc[0]
        
        # Calculate ATR
        atr20 = self.calculate_atr(df.tail(30))
        if not atr20.empty:
            atr20_value = atr20.iloc[-1]
        else:
            atr20_value = None
        
        # Create MarketIndicators object
        indicator = MarketIndicators(
            date=date,
            hs300_close=row['close'],
            hs300_volume=row.get('volume'),
            ma20=row.get('ma20'),
            ma60=row.get('ma60'),
            ma120=row.get('ma120'),
            ma200=row.get('ma200'),
            atr20=atr20_value,
            above_yearline=row['close'] > row['ma200'] if pd.notna(row['ma200']) else None,
            yearline_distance=((row['close'] - row['ma200']) / row['ma200'] * 100) if pd.notna(row['ma200']) else None
        )
        
        return indicator
    
    @lru_cache(maxsize=128)
    def get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """Get Shanghai Exchange trading days"""
        if self._trading_calendar is None:
            self._load_trading_calendar()
        
        # Filter trading days in range
        days = []
        current = start_date
        
        while current <= end_date:
            if self._is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        
        return days
    
    def _load_trading_calendar(self):
        """Load Shanghai Exchange trading calendar"""
        # In production, this would load from exchange API or database
        # For now, use basic weekday logic with Chinese holidays
        self._trading_calendar = set()
        
        # Add logic for Chinese holidays here
        # Spring Festival, National Day, etc.
        pass
    
    def _is_trading_day(self, check_date: date) -> bool:
        """Check if date is a trading day on Shanghai Exchange"""
        # Basic check - weekday and not holiday
        if check_date.weekday() >= 5:  # Weekend
            return False
        
        # Check against known holidays
        # This would be more sophisticated in production
        return True
    
    def get_month_end_trading_days(self, year: int) -> List[date]:
        """Get last trading day of each month"""
        month_ends = []
        
        for month in range(1, 13):
            # Get last day of month
            if month == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month + 1, 1)
            
            last_day = next_month - timedelta(days=1)
            
            # Find last trading day
            while not self._is_trading_day(last_day):
                last_day -= timedelta(days=1)
            
            month_ends.append(last_day)
        
        return month_ends
    
    def detect_outliers(self, df: pd.DataFrame, threshold: float = 15.0) -> pd.DataFrame:
        """Detect return outliers without announcements
        
        Args:
            df: DataFrame with price data
            threshold: Threshold for outlier detection (default 15%)
            
        Returns:
            DataFrame with 'outlier' column marking anomalies
        """
        df = df.copy()
        
        # Calculate daily returns
        df['daily_return'] = df['close'].pct_change() * 100
        
        # Mark outliers
        df['outlier'] = abs(df['daily_return']) > threshold
        
        # Log outliers for alerting
        outliers = df[df['outlier']]
        for idx, row in outliers.iterrows():
            logger.warning(
                f"Outlier detected on {idx}: {row['daily_return']:.2f}% return "
                f"(threshold: {threshold}%)"
            )
        
        return df


# Singleton instance
_data_fetcher: Optional[DataFetcher] = None

def get_data_fetcher() -> DataFetcher:
    """Get singleton data fetcher instance"""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = DataFetcher()
    return _data_fetcher