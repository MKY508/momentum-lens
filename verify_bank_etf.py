#!/usr/bin/env python3
"""
验证银行ETF的真实数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def verify_bank_etf():
    """验证银行ETF (512800) 的真实表现"""
    
    code = '512800'
    symbol = 'sh512800'
    
    print("=" * 80)
    print("验证银行ETF (512800) 真实数据")
    print("=" * 80)
    
    try:
        # 1. 获取实时行情
        print("\n1. 实时行情数据:")
        print("-" * 40)
        spot_df = ak.fund_etf_spot_em()
        bank_etf = spot_df[spot_df['代码'] == code]
        
        if not bank_etf.empty:
            row = bank_etf.iloc[0]
            print(f"ETF名称: {row['名称']}")
            print(f"最新价: {row['最新价']}")
            print(f"今日涨跌幅: {row['涨跌幅']}%")
            print(f"成交额: {float(row['成交额'])/100000000:.2f}亿元")
        
        # 2. 获取历史数据
        print("\n2. 历史数据分析:")
        print("-" * 40)
        
        # 获取全部历史数据
        hist_df = ak.fund_etf_hist_sina(symbol=symbol)
        
        if hist_df is not None and len(hist_df) > 0:
            hist_df['date'] = pd.to_datetime(hist_df['date'])
            hist_df = hist_df.sort_values('date')
            
            print(f"数据总条数: {len(hist_df)}")
            print(f"数据范围: {hist_df['date'].min().strftime('%Y-%m-%d')} 至 {hist_df['date'].max().strftime('%Y-%m-%d')}")
            
            # 当前价格
            current_price = hist_df['close'].iloc[-1]
            latest_date = hist_df['date'].iloc[-1]
            print(f"\n最新收盘价: {current_price:.4f} ({latest_date.strftime('%Y-%m-%d')})")
            
            # 计算不同时间段的涨跌幅
            periods = [
                (20, "1个月"),
                (60, "3个月"),
                (120, "6个月"),
                (250, "1年")
            ]
            
            print("\n各时间段涨跌幅:")
            for days, label in periods:
                if len(hist_df) >= days:
                    price_ago = hist_df['close'].iloc[-days]
                    date_ago = hist_df['date'].iloc[-days]
                    change = ((current_price / price_ago) - 1) * 100
                    print(f"  {label} ({date_ago.strftime('%Y-%m-%d')}): {change:>7.2f}%")
            
            # 计算动量评分
            if len(hist_df) >= 60:
                price_60d = hist_df['close'].iloc[-60]
                r60 = ((current_price / price_60d) - 1) * 100
            else:
                r60 = 0
            
            if len(hist_df) >= 120:
                price_120d = hist_df['close'].iloc[-120]
                r120 = ((current_price / price_120d) - 1) * 100
            else:
                r120 = 0
            
            score = 0.6 * r60 + 0.4 * r120
            
            print(f"\n动量指标:")
            print(f"  60日涨幅 (r60): {r60:.2f}%")
            print(f"  120日涨幅 (r120): {r120:.2f}%")
            print(f"  动量评分: {score:.2f}")
            
            # 显示最近10天的价格走势
            print("\n最近10个交易日走势:")
            print("-" * 40)
            recent_10 = hist_df.tail(10)
            for _, row in recent_10.iterrows():
                change_pct = ((row['close'] / row['open']) - 1) * 100 if row['open'] > 0 else 0
                print(f"  {row['date'].strftime('%Y-%m-%d')}: {row['close']:.4f} ({change_pct:+.2f}%)")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    verify_bank_etf()