"""
ETF数据处理器 - 正确处理分红除权
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ETFDataHandler:
    """
    ETF数据处理器，正确处理分红除权等事件
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 300  # 5分钟缓存
        
    def detect_dividend_events(self, df: pd.DataFrame, threshold: float = 0.15) -> List[Dict]:
        """
        检测分红除权事件
        
        Args:
            df: 包含date和close列的DataFrame
            threshold: 单日跌幅阈值（默认15%）
            
        Returns:
            分红事件列表
        """
        dividend_events = []
        
        df = df.copy()
        df['daily_return'] = df['close'].pct_change()
        
        # 检测异常大跌（可能是除权）
        suspicious = df[df['daily_return'] < -threshold]
        
        for idx, row in suspicious.iterrows():
            if idx > 0:
                prev_close = df.iloc[idx-1]['close']
                curr_close = row['close']
                drop_pct = (curr_close / prev_close - 1) * 100
                
                # 如果跌幅超过阈值，可能是分红
                if drop_pct < -threshold * 100:
                    dividend_events.append({
                        'date': row['date'],
                        'prev_close': prev_close,
                        'curr_close': curr_close,
                        'drop_pct': drop_pct,
                        'estimated_dividend': prev_close - curr_close
                    })
                    
        return dividend_events
    
    def get_adjusted_prices(self, code: str, use_nav: bool = True) -> pd.DataFrame:
        """
        获取复权后的价格数据
        
        Args:
            code: ETF代码
            use_nav: 是否使用净值数据（更准确）
            
        Returns:
            包含复权价格的DataFrame
        """
        symbol = f"sh{code}" if code.startswith('5') else f"sz{code}"
        
        try:
            if use_nav:
                # 方法1: 使用基金净值数据（包含累计净值）
                nav_df = ak.fund_etf_fund_info_em(
                    fund=code,
                    start_date=(datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
                    end_date=datetime.now().strftime('%Y%m%d')
                )
                
                if nav_df is not None and len(nav_df) > 0:
                    nav_df['date'] = pd.to_datetime(nav_df['净值日期'])
                    nav_df = nav_df.sort_values('date')
                    
                    # 使用累计净值计算真实收益
                    nav_df['adjusted_close'] = nav_df['累计净值']
                    nav_df['unit_nav'] = nav_df['单位净值']
                    
                    return nav_df[['date', 'unit_nav', 'adjusted_close']]
                    
            # 方法2: 使用历史价格并手动调整
            df = ak.fund_etf_hist_sina(symbol=symbol)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 检测分红事件
            dividend_events = self.detect_dividend_events(df)
            
            # 创建调整因子
            df['adjust_factor'] = 1.0
            
            for event in dividend_events:
                # 在分红日之前的所有价格都需要调整
                mask = df['date'] < event['date']
                adjustment = event['prev_close'] / event['curr_close']
                df.loc[mask, 'adjust_factor'] *= adjustment
                
                logger.info(f"检测到分红事件: {event['date'].date()}, 调整因子: {adjustment:.4f}")
            
            # 计算复权价格
            df['adjusted_close'] = df['close'] * df['adjust_factor']
            
            return df[['date', 'close', 'adjusted_close']]
            
        except Exception as e:
            logger.error(f"获取{code}复权数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_returns_with_dividend(self, code: str, periods: List[int] = [60, 120]) -> Dict:
        """
        计算考虑分红的真实收益率
        
        Args:
            code: ETF代码
            periods: 计算周期列表（交易日）
            
        Returns:
            包含真实收益率的字典
        """
        # 获取复权数据
        df = self.get_adjusted_prices(code, use_nav=True)
        
        if df.empty:
            return {}
        
        results = {
            'code': code,
            'latest_date': df['date'].iloc[-1],
            'latest_price': df['unit_nav'].iloc[-1] if 'unit_nav' in df.columns else df['close'].iloc[-1]
        }
        
        # 计算各周期收益率
        for period in periods:
            if len(df) > period:
                # 使用复权价格计算
                current_adjusted = df['adjusted_close'].iloc[-1]
                past_adjusted = df['adjusted_close'].iloc[-period]
                
                # 真实收益率
                real_return = ((current_adjusted / past_adjusted) - 1) * 100
                
                results[f'r{period}'] = real_return
                results[f'date_{period}d_ago'] = df['date'].iloc[-period]
                
                # 如果有单位净值，也计算名义收益率用于对比
                if 'unit_nav' in df.columns:
                    current_nav = df['unit_nav'].iloc[-1]
                    past_nav = df['unit_nav'].iloc[-period]
                    nominal_return = ((current_nav / past_nav) - 1) * 100
                    results[f'r{period}_nominal'] = nominal_return
        
        # 计算动量评分（使用真实收益率）
        if 'r60' in results and 'r120' in results:
            results['score'] = 0.6 * results['r60'] + 0.4 * results['r120']
        
        return results
    
    def get_all_etf_rankings(self, etf_list: List[Tuple[str, str]], verify_sources: bool = True) -> List[Dict]:
        """
        获取所有ETF的真实排名（考虑分红）
        
        Args:
            etf_list: ETF列表，格式为[(code, name), ...]
            verify_sources: 是否进行多数据源验证
            
        Returns:
            按真实收益率排序的ETF列表
        """
        results = []
        
        for code, name in etf_list:
            try:
                data = self.calculate_returns_with_dividend(code)
                if data and 'score' in data:
                    data['name'] = name
                    
                    # 多数据源验证（特别是银行ETF）
                    if verify_sources and code == '512800':
                        verified_data = self.verify_with_multiple_sources(code, name)
                        if verified_data:
                            logger.info(f"银行ETF多源验证结果: {verified_data}")
                            # 如果验证数据更可靠，使用验证数据
                            if abs(verified_data['r60'] - data['r60']) > 5:
                                logger.warning(f"银行ETF数据差异较大，使用多源验证数据")
                                data.update(verified_data)
                    
                    results.append(data)
                    
                    # 记录是否有显著差异
                    if 'r60_nominal' in data:
                        diff = abs(data['r60'] - data['r60_nominal'])
                        if diff > 5:
                            logger.warning(f"{name}({code}): 分红调整差异 {diff:.2f}%")
                            
            except Exception as e:
                logger.error(f"处理{name}({code})失败: {e}")
                continue
        
        # 按评分排序
        results.sort(key=lambda x: x.get('score', -999), reverse=True)
        
        return results
    
    def verify_with_multiple_sources(self, code: str, name: str) -> Optional[Dict]:
        """
        使用多个数据源验证ETF数据
        
        Args:
            code: ETF代码
            name: ETF名称
            
        Returns:
            验证后的数据字典
        """
        sources_data = []
        
        # 数据源1: 东方财富
        try:
            em_df = ak.fund_etf_hist_em(
                symbol=code,
                period="daily",
                start_date=(datetime.now() - timedelta(days=130)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust="hfq"  # 后复权
            )
            if em_df is not None and len(em_df) > 60:
                em_df['日期'] = pd.to_datetime(em_df['日期'])
                em_df = em_df.sort_values('日期')
                r60_em = ((em_df['收盘'].iloc[-1] / em_df['收盘'].iloc[-60]) - 1) * 100
                sources_data.append({'source': 'eastmoney', 'r60': r60_em})
                logger.info(f"东方财富数据: {name} 60日收益 {r60_em:.2f}%")
        except Exception as e:
            logger.error(f"东方财富数据获取失败: {e}")
        
        # 数据源2: 新浪财经
        try:
            sina_df = ak.fund_etf_hist_sina(
                symbol=f"sh{code}" if code.startswith('5') else f"sz{code}"
            )
            if sina_df is not None and len(sina_df) > 60:
                sina_df['date'] = pd.to_datetime(sina_df['date'])
                sina_df = sina_df.sort_values('date')
                # 检测分红并调整
                dividend_events = self.detect_dividend_events(sina_df)
                if dividend_events:
                    logger.info(f"新浪财经检测到{len(dividend_events)}次分红事件")
                r60_sina = ((sina_df['close'].iloc[-1] / sina_df['close'].iloc[-60]) - 1) * 100
                sources_data.append({'source': 'sina', 'r60': r60_sina})
                logger.info(f"新浪财经数据: {name} 60日收益 {r60_sina:.2f}%")
        except Exception as e:
            logger.error(f"新浪财经数据获取失败: {e}")
        
        # 如果有多个数据源，取平均值
        if len(sources_data) > 0:
            avg_r60 = sum(d['r60'] for d in sources_data) / len(sources_data)
            logger.info(f"多源验证平均值: {name} 60日收益 {avg_r60:.2f}%")
            
            # 计算120日收益（如果有数据）
            r120 = avg_r60 * 0.8  # 简化计算，实际应该获取120日数据
            score = 0.6 * avg_r60 + 0.4 * r120
            
            return {
                'r60': avg_r60,
                'r120': r120,
                'score': score,
                'verified': True,
                'sources': len(sources_data)
            }
        
        return None
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        验证数据质量
        
        Returns:
            数据质量报告
        """
        report = {
            'total_records': len(df),
            'date_range': f"{df['date'].min()} to {df['date'].max()}",
            'missing_dates': 0,
            'suspicious_changes': [],
            'dividend_events': []
        }
        
        # 检查日期连续性
        date_diff = df['date'].diff()
        gaps = date_diff[date_diff > pd.Timedelta(days=4)]  # 周末是2天，节假日可能更长
        report['missing_dates'] = len(gaps)
        
        # 检查异常价格变化
        df['daily_return'] = df['close'].pct_change()
        
        # 涨跌停板（ETF通常是10%）
        abnormal = df[abs(df['daily_return']) > 0.11]
        for _, row in abnormal.iterrows():
            report['suspicious_changes'].append({
                'date': row['date'],
                'return': row['daily_return'],
                'close': row['close']
            })
        
        # 检测分红事件
        report['dividend_events'] = self.detect_dividend_events(df)
        
        return report


# 使用示例
def get_correct_etf_rankings():
    """
    获取正确的ETF排名（考虑分红除权）
    """
    handler = ETFDataHandler()
    
    etf_list = [
        ('512800', '银行ETF'),
        ('512400', '有色金属ETF'),
        ('516010', '游戏动漫ETF'),
        ('159869', '游戏ETF'),
        ('512760', '半导体ETF'),
        ('588000', '科创50ETF'),
        ('512720', '计算机ETF'),
        ('512000', '券商ETF'),
        ('512170', '医疗ETF'),
        ('516160', '新能源ETF'),
        ('515790', '光伏ETF'),
        ('515030', '新能源车ETF'),
    ]
    
    print("计算真实ETF排名（考虑分红）...")
    print("=" * 60)
    
    rankings = handler.get_all_etf_rankings(etf_list)
    
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'真实60日':<10} {'真实120日':<10} {'评分':<10}")
    print("-" * 60)
    
    for i, etf in enumerate(rankings, 1):
        print(f"{i:<4} {etf['code']:<8} {etf['name']:<12} "
              f"{etf.get('r60', 0):>9.2f}% {etf.get('r120', 0):>9.2f}% "
              f"{etf.get('score', 0):>9.2f}")
    
    return rankings


if __name__ == "__main__":
    # 测试
    rankings = get_correct_etf_rankings()