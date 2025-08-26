#!/usr/bin/env python3
"""
测试获取真实ETF数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_etf_performance():
    """获取ETF的真实涨幅数据"""
    
    etf_list = [
        {'code': '588000', 'name': '科创50ETF'},
        {'code': '512760', 'name': '半导体ETF'},
        {'code': '512720', 'name': '计算机ETF'},
        {'code': '516160', 'name': '新能源ETF'},
        {'code': '515790', 'name': '光伏ETF'},
        {'code': '512800', 'name': '银行ETF'},
        {'code': '512400', 'name': '有色金属ETF'},
        {'code': '512000', 'name': '券商ETF'},
        {'code': '515030', 'name': '新能源车ETF'},
        {'code': '516010', 'name': '游戏动漫ETF'},
        {'code': '159869', 'name': '游戏ETF'},
        {'code': '512170', 'name': '医疗ETF'},
    ]
    
    results = []
    
    print("=" * 80)
    print("获取真实ETF数据（使用akshare）")
    print("=" * 80)
    
    for etf in etf_list:
        try:
            # 确定交易所前缀
            if etf['code'].startswith('5'):
                symbol = f"sh{etf['code']}"
            elif etf['code'].startswith('1'):
                symbol = f"sz{etf['code']}"
            else:
                symbol = f"sh{etf['code']}"
            
            # 获取历史数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=150)  # 获取150天数据
            
            df = ak.fund_etf_hist_sina(
                symbol=symbol,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust='hfq'  # 后复权
            )
            
            if df is not None and len(df) > 0:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.sort_values('日期')
                
                # 当前价格
                current_price = df['收盘'].iloc[-1]
                
                # 计算60日涨幅（约3个月）
                if len(df) >= 60:
                    price_60d_ago = df['收盘'].iloc[-60]
                    r60 = ((current_price / price_60d_ago) - 1) * 100
                else:
                    r60 = 0
                
                # 计算120日涨幅（约6个月）
                if len(df) >= 120:
                    price_120d_ago = df['收盘'].iloc[-120]
                    r120 = ((current_price / price_120d_ago) - 1) * 100
                else:
                    r120 = 0
                
                # 计算动量评分
                score = 0.6 * r60 + 0.4 * r120
                
                results.append({
                    'code': etf['code'],
                    'name': etf['name'],
                    'r60': round(r60, 2),
                    'r120': round(r120, 2),
                    'score': round(score, 2),
                    'current_price': round(current_price, 3)
                })
                
                print(f"✅ {etf['code']} {etf['name']}: r60={r60:.2f}%, r120={r120:.2f}%, score={score:.2f}")
            else:
                print(f"❌ {etf['code']} {etf['name']}: 无法获取数据")
                
        except Exception as e:
            print(f"❌ {etf['code']} {etf['name']}: 错误 - {e}")
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 80)
    print("ETF动量排名（按评分排序）")
    print("=" * 80)
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'60日涨幅':<10} {'120日涨幅':<10} {'评分':<8}")
    print("-" * 80)
    
    for i, etf in enumerate(results, 1):
        print(f"{i:<4} {etf['code']:<8} {etf['name']:<12} {etf['r60']:<10.2f}% {etf['r120']:<10.2f}% {etf['score']:<8.2f}")
    
    print("\n" + "=" * 80)
    print("数据获取时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    try:
        results = get_etf_performance()
    except Exception as e:
        print(f"程序执行失败: {e}")