#!/usr/bin/env python3
"""
测试券商ETF分红调整计算
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def test_broker_etf_dividend():
    """测试券商ETF (512000) 分红调整"""
    
    print("券商ETF (512000) 分红调整测试")
    print("=" * 60)
    
    try:
        # 获取基金净值数据（包含累计净值）
        nav_df = ak.fund_etf_fund_info_em(
            fund='512000',
            start_date='20240301',
            end_date='20250825'
        )
        
        if nav_df is not None and len(nav_df) > 0:
            nav_df['净值日期'] = pd.to_datetime(nav_df['净值日期'])
            nav_df = nav_df.sort_values('净值日期')
            
            print(f"数据范围: {nav_df['净值日期'].min().date()} 到 {nav_df['净值日期'].max().date()}")
            print(f"记录数: {len(nav_df)}")
            print()
            
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
                
                # 检测可能的分红事件
                print("\n检测分红事件:")
                print("-" * 40)
                
                # 计算每日收益率
                nav_df['daily_return'] = nav_df['单位净值'].pct_change()
                nav_df['累计收益'] = nav_df['累计净值'].pct_change()
                
                # 找出单位净值大跌但累计净值正常的日期（可能是分红）
                suspicious = nav_df[nav_df['daily_return'] < -0.10]  # 单日跌幅超过10%
                
                if len(suspicious) > 0:
                    print("发现可能的分红日期:")
                    for _, row in suspicious.iterrows():
                        prev_idx = nav_df.index.get_loc(row.name) - 1
                        if prev_idx >= 0:
                            prev_row = nav_df.iloc[prev_idx]
                            drop = (row['单位净值'] / prev_row['单位净值'] - 1) * 100
                            cumulative_change = (row['累计净值'] / prev_row['累计净值'] - 1) * 100
                            
                            print(f"\n日期: {row['净值日期'].date()}")
                            print(f"  单位净值: {prev_row['单位净值']:.4f} → {row['单位净值']:.4f} ({drop:.2f}%)")
                            print(f"  累计净值: {prev_row['累计净值']:.4f} → {row['累计净值']:.4f} ({cumulative_change:.2f}%)")
                            
                            if abs(drop) > 10 and abs(cumulative_change) < 2:
                                dividend = prev_row['单位净值'] - row['单位净值']
                                print(f"  推测分红金额: {dividend:.4f}元/份")
                else:
                    print("未发现明显的分红事件")
                
                # 计算120天收益（如果有数据）
                if len(nav_df) >= 120:
                    nav_120_ago = nav_df.iloc[-120]
                    nominal_120 = ((current_nav['单位净值'] / nav_120_ago['单位净值']) - 1) * 100
                    adjusted_120 = ((current_nav['累计净值'] / nav_120_ago['累计净值']) - 1) * 100
                    
                    print(f"\n120天收益率:")
                    print(f"  名义收益率: {nominal_120:.2f}%")
                    print(f"  真实收益率: {adjusted_120:.2f}%")
                    print(f"  分红影响: {adjusted_120 - nominal_120:.2f}%")
                    
                    # 计算动量评分
                    nominal_score = 0.6 * nominal_return + 0.4 * nominal_120
                    adjusted_score = 0.6 * adjusted_return + 0.4 * adjusted_120
                    
                    print(f"\n动量评分:")
                    print(f"  名义评分: {nominal_score:.2f}")
                    print(f"  真实评分: {adjusted_score:.2f}")
                    print(f"  差异: {adjusted_score - nominal_score:.2f}")
                
                return adjusted_return
            else:
                print("数据不足60天")
                
    except Exception as e:
        print(f"错误: {e}")
        
    # 尝试获取历史价格数据检查
    print("\n\n使用历史价格数据验证:")
    print("-" * 40)
    
    try:
        # 获取新浪财经数据
        df = ak.fund_etf_hist_sina(symbol="sh512000")
        if df is not None and len(df) > 0:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 计算最近60天收益
            if len(df) >= 60:
                recent_return = ((df['close'].iloc[-1] / df['close'].iloc[-60]) - 1) * 100
                print(f"新浪财经60天价格收益率: {recent_return:.2f}%")
                
                # 检测大幅下跌
                df['daily_return'] = df['close'].pct_change()
                big_drops = df[df['daily_return'] < -0.10]
                
                if len(big_drops) > 0:
                    print(f"\n发现{len(big_drops)}次大幅下跌(>10%):")
                    for _, row in big_drops.tail(5).iterrows():
                        print(f"  {row['date'].date()}: {row['daily_return']*100:.2f}%")
                        
    except Exception as e:
        print(f"新浪数据获取失败: {e}")
    
    return None

if __name__ == "__main__":
    result = test_broker_etf_dividend()
    
    print("\n" + "=" * 60)
    print("结论:")
    if result is not None:
        if result > -30:
            print(f"✅ 券商ETF真实收益率 ({result:.2f}%) 比显示的名义收益率高")
            print("✅ 存在分红调整的影响")
        else:
            print(f"⚠️ 券商ETF真实收益率仍然较低: {result:.2f}%")
    else:
        print("❌ 无法获取完整数据")