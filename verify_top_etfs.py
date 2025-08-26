#!/usr/bin/env python3
"""
验证排名靠前的ETF数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime

def verify_etf(code, name):
    """验证单个ETF的数据"""
    symbol = f"sh{code}" if code.startswith('5') else f"sz{code}"
    
    try:
        # 获取历史数据
        hist_df = ak.fund_etf_hist_sina(symbol=symbol)
        
        if hist_df is not None and len(hist_df) > 0:
            hist_df['date'] = pd.to_datetime(hist_df['date'])
            hist_df = hist_df.sort_values('date')
            hist_df = hist_df.tail(150)  # 最近150个交易日
            
            if len(hist_df) >= 120:
                current_price = hist_df['close'].iloc[-1]
                price_60d = hist_df['close'].iloc[-60]
                price_120d = hist_df['close'].iloc[-120]
                
                r60 = ((current_price / price_60d) - 1) * 100
                r120 = ((current_price / price_120d) - 1) * 100
                score = 0.6 * r60 + 0.4 * r120
                
                return {
                    'code': code,
                    'name': name,
                    'r60': round(r60, 2),
                    'r120': round(r120, 2),
                    'score': round(score, 2),
                    'current': round(current_price, 4)
                }
    except Exception as e:
        print(f"获取{name}失败: {e}")
    
    return None

def main():
    # 验证几个关键ETF
    test_etfs = [
        ('512400', '有色金属ETF'),
        ('516010', '游戏动漫ETF'),
        ('512760', '半导体ETF'),
        ('588000', '科创50ETF'),
        ('512800', '银行ETF'),
        ('512000', '券商ETF'),
    ]
    
    print("=" * 80)
    print("验证关键ETF的真实数据")
    print("=" * 80)
    print(f"{'代码':<8} {'名称':<12} {'60日涨幅':>10} {'120日涨幅':>10} {'评分':>8} {'当前价':>8}")
    print("-" * 80)
    
    results = []
    for code, name in test_etfs:
        data = verify_etf(code, name)
        if data:
            results.append(data)
            print(f"{data['code']:<8} {data['name']:<12} {data['r60']:>9.2f}% {data['r120']:>9.2f}% "
                  f"{data['score']:>7.2f} {data['current']:>8.4f}")
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 80)
    print("按动量评分排序：")
    print("=" * 80)
    for i, data in enumerate(results, 1):
        status = "✅" if data['score'] > 0 else "❌"
        print(f"{status} #{i} {data['name']}: Score={data['score']}")

if __name__ == "__main__":
    main()