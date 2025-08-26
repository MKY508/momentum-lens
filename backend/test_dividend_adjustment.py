#!/usr/bin/env python3
"""
测试分红调整计算
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def test_bank_etf_with_dividend():
    """测试银行ETF分红调整后的真实收益"""
    
    print("银行ETF (512800) 分红调整测试")
    print("=" * 60)
    
    try:
        # 获取基金净值数据（包含累计净值）
        nav_df = ak.fund_etf_fund_info_em(
            fund='512800',
            start_date='20250301',
            end_date='20250825'
        )
        
        nav_df['净值日期'] = pd.to_datetime(nav_df['净值日期'])
        nav_df = nav_df.sort_values('净值日期')
        
        # 找到60个交易日前的数据
        if len(nav_df) >= 60:
            current_nav = nav_df.iloc[-1]
            nav_60_ago = nav_df.iloc[-60]
            
            # 使用单位净值计算（不考虑分红）
            nominal_return = ((current_nav['单位净值'] / nav_60_ago['单位净值']) - 1) * 100
            
            # 使用累计净值计算（考虑分红）
            adjusted_return = ((current_nav['累计净值'] / nav_60_ago['累计净值']) - 1) * 100
            
            print(f"当前日期: {current_nav['净值日期'].date()}")
            print(f"60天前日期: {nav_60_ago['净值日期'].date()}")
            print()
            print(f"60天前单位净值: {nav_60_ago['单位净值']:.4f}")
            print(f"当前单位净值: {current_nav['单位净值']:.4f}")
            print(f"名义收益率（不考虑分红）: {nominal_return:.2f}%")
            print()
            print(f"60天前累计净值: {nav_60_ago['累计净值']:.4f}")
            print(f"当前累计净值: {current_nav['累计净值']:.4f}")
            print(f"真实收益率（考虑分红）: {adjusted_return:.2f}%")
            print()
            print(f"分红影响: {adjusted_return - nominal_return:.2f}%")
            
            # 检测7月4日的分红
            july_data = nav_df[(nav_df['净值日期'] >= '2025-07-03') & 
                               (nav_df['净值日期'] <= '2025-07-05')]
            
            if len(july_data) >= 2:
                print("\n7月4日分红事件分析:")
                for _, row in july_data.iterrows():
                    print(f"{row['净值日期'].date()}: "
                          f"单位净值={row['单位净值']:.4f}, "
                          f"累计净值={row['累计净值']:.4f}")
                
                # 计算分红金额
                div_amount = july_data.iloc[0]['单位净值'] - july_data.iloc[-1]['单位净值']
                if div_amount > 0.5:
                    print(f"\n推测分红金额: {div_amount:.4f}元/份")
            
            return adjusted_return
            
    except Exception as e:
        print(f"错误: {e}")
        return None

def compare_all_etfs():
    """比较所有ETF的真实与名义收益"""
    
    etf_list = [
        ('512800', '银行ETF'),
        ('512400', '有色金属ETF'),
        ('516010', '游戏动漫ETF'),
        ('512760', '半导体ETF'),
        ('588000', '科创50ETF'),
    ]
    
    print("\n\nETF收益率对比（60天）")
    print("=" * 80)
    print(f"{'ETF名称':<12} {'名义收益率':<12} {'真实收益率':<12} {'差异':<10} {'备注':<20}")
    print("-" * 80)
    
    for code, name in etf_list:
        try:
            # 获取净值数据
            nav_df = ak.fund_etf_fund_info_em(
                fund=code,
                start_date='20250501',
                end_date='20250825'
            )
            
            if nav_df is not None and len(nav_df) >= 60:
                nav_df['净值日期'] = pd.to_datetime(nav_df['净值日期'])
                nav_df = nav_df.sort_values('净值日期')
                
                current = nav_df.iloc[-1]
                past_60 = nav_df.iloc[-60]
                
                # 计算收益率
                nominal = ((current['单位净值'] / past_60['单位净值']) - 1) * 100
                adjusted = ((current['累计净值'] / past_60['累计净值']) - 1) * 100
                diff = adjusted - nominal
                
                # 判断是否有分红
                note = "有分红" if abs(diff) > 1 else ""
                
                print(f"{name:<12} {nominal:>11.2f}% {adjusted:>11.2f}% {diff:>9.2f}% {note:<20}")
                
        except Exception as e:
            print(f"{name:<12} {'错误':<12} {'错误':<12} {'--':<10} {str(e)[:20]}")
    
    print("=" * 80)
    print("\n结论: 使用累计净值计算才能得到真实收益率！")

if __name__ == "__main__":
    # 测试银行ETF
    bank_return = test_bank_etf_with_dividend()
    
    # 比较所有ETF
    compare_all_etfs()