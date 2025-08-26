#!/usr/bin/env python3
"""
最终验证：银行ETF分红调整后的真实收益
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from etf_data_handler import ETFDataHandler
import pandas as pd
from datetime import datetime

def test_bank_etf_final():
    """最终测试银行ETF的真实收益"""
    
    print("=" * 70)
    print("银行ETF (512800) 最终验证报告")
    print("=" * 70)
    
    handler = ETFDataHandler()
    
    # 1. 获取分红调整后的数据
    print("\n1. 分红调整后的真实收益:")
    print("-" * 40)
    
    result = handler.calculate_returns_with_dividend('512800', periods=[60, 120])
    
    if result:
        print(f"  60天真实收益率: {result.get('r60', 0):.2f}%")
        print(f"  120天真实收益率: {result.get('r120', 0):.2f}%") 
        print(f"  动量评分: {result.get('score', 0):.2f}")
        
        if 'r60_nominal' in result:
            print(f"\n  60天名义收益率（不含分红）: {result.get('r60_nominal', 0):.2f}%")
            print(f"  分红影响: {abs(result.get('r60', 0) - result.get('r60_nominal', 0)):.2f}%")
    
    # 2. 多数据源验证
    print("\n2. 多数据源验证:")
    print("-" * 40)
    
    verified = handler.verify_with_multiple_sources('512800', '银行ETF')
    if verified:
        print(f"  验证后60天收益: {verified.get('r60', 0):.2f}%")
        print(f"  数据源数量: {verified.get('sources', 0)}")
    
    # 3. 获取完整排名
    print("\n3. 所有ETF排名（考虑分红）:")
    print("-" * 40)
    
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
    
    rankings = handler.get_all_etf_rankings(etf_list)
    
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'60日真实':<10} {'评分':<10} {'分红？':<6}")
    print("-" * 60)
    
    for i, etf in enumerate(rankings[:12], 1):
        has_dividend = abs(etf.get('r60', 0) - etf.get('r60_nominal', etf.get('r60', 0))) > 1
        dividend_mark = "✓" if has_dividend else ""
        
        # 标记银行ETF
        mark = " ← 银行" if etf['code'] == '512800' else ""
        
        print(f"{i:<4} {etf['code']:<8} {etf['name']:<12} "
              f"{etf.get('r60', 0):>9.2f}% {etf.get('score', 0):>9.2f} "
              f"{dividend_mark:^6}{mark}")
    
    # 4. 验证结论
    print("\n" + "=" * 70)
    print("验证结论:")
    print("-" * 40)
    
    bank_etf = next((etf for etf in rankings if etf['code'] == '512800'), None)
    if bank_etf:
        rank = rankings.index(bank_etf) + 1
        r60 = bank_etf.get('r60', 0)
        
        if r60 > 0:
            print(f"✅ 银行ETF真实收益为正: {r60:.2f}%")
            print(f"✅ 排名第{rank}位（共{len(rankings)}只ETF）")
            print(f"✅ 分红调整正确应用")
        else:
            print(f"❌ 银行ETF收益仍为负: {r60:.2f}%")
            print(f"⚠️ 可能需要检查数据源或分红调整逻辑")
    else:
        print("❌ 未找到银行ETF数据")
    
    print("=" * 70)

if __name__ == "__main__":
    test_bank_etf_final()