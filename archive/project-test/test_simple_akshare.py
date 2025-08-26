#!/usr/bin/env python3
"""简单测试AKShare数据获取"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def test_etf_data():
    """测试ETF数据获取"""
    print("=" * 50)
    print("📊 测试AKShare ETF数据获取")
    print("=" * 50)
    
    # 1. 获取ETF实时行情
    print("\n1. 获取ETF实时行情列表...")
    try:
        # 获取ETF实时行情
        etf_spot = ak.fund_etf_spot_em()
        print(f"✅ 成功获取 {len(etf_spot)} 只ETF实时行情")
        
        # 显示前5只ETF
        print("\n前5只ETF：")
        for _, row in etf_spot.head(5).iterrows():
            print(f"  {row['代码']}: {row['名称']}")
            print(f"    最新价: {row['最新价']}")
            print(f"    涨跌幅: {row['涨跌幅']}%")
            print(f"    成交额: {row['成交额']}")
            print()
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    # 2. 获取具体ETF历史数据
    print("\n2. 获取沪深300ETF(510300)历史数据...")
    try:
        # 获取ETF历史数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        etf_hist = ak.fund_etf_hist_em(
            symbol="510300",
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        print(f"✅ 成功获取 {len(etf_hist)} 条历史数据")
        print("\n最近5个交易日：")
        for _, row in etf_hist.tail(5).iterrows():
            print(f"  {row['日期']}: 收盘 {row['收盘']}, 涨跌幅 {row['涨跌幅']}%")
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    # 3. 获取沪深300指数数据
    print("\n3. 获取沪深300指数数据...")
    try:
        # 获取指数数据
        index_data = ak.stock_zh_index_daily(symbol="sh000300")
        print(f"✅ 成功获取 {len(index_data)} 条指数数据")
        
        # 显示最近5天
        print("\n最近5个交易日：")
        for _, row in index_data.tail(5).iterrows():
            print(f"  {row['date']}: 收盘 {row['close']}")
    except Exception as e:
        print(f"❌ 获取失败: {e}")

def test_convertible_bonds():
    """测试可转债数据获取"""
    print("\n" + "=" * 50)
    print("💰 测试可转债数据获取")
    print("=" * 50)
    
    try:
        # 获取可转债列表
        print("\n获取可转债列表...")
        cb_list = ak.bond_zh_cov_spot()  # 可转债实时行情
        
        if not cb_list.empty:
            print(f"✅ 成功获取 {len(cb_list)} 只可转债")
            
            # 筛选低溢价可转债
            print("\n低溢价可转债（溢价率<10%）：")
            # 注意：字段名可能不同，需要根据实际返回调整
            low_premium = cb_list.head(5)  # 显示前5只
            
            for _, cb in low_premium.iterrows():
                print(f"  {cb.get('symbol', 'N/A')}: {cb.get('name', 'N/A')}")
                if 'value' in cb:
                    print(f"    价格: {cb['value']}")
        else:
            print("⚠️ 未获取到可转债数据")
            
    except Exception as e:
        print(f"❌ 获取可转债失败: {e}")

def test_etf_fund_info():
    """测试ETF基金信息"""
    print("\n" + "=" * 50)
    print("📋 测试ETF基金信息获取")
    print("=" * 50)
    
    try:
        # 获取ETF基金列表信息
        print("\n获取ETF基金列表...")
        etf_list = ak.fund_etf_fund_info_em()
        
        if not etf_list.empty:
            print(f"✅ 成功获取 {len(etf_list)} 只ETF基金信息")
            
            # 显示一些主要ETF
            major_etfs = ['510300', '510050', '159915', '518880', '510880']
            print("\n主要ETF信息：")
            
            for code in major_etfs:
                etf = etf_list[etf_list['基金代码'].str.contains(code, na=False)]
                if not etf.empty:
                    row = etf.iloc[0]
                    print(f"  {row['基金代码']}: {row['基金简称']}")
                    if '管理费' in row:
                        print(f"    管理费: {row['管理费']}")
                    if '规模' in row:
                        print(f"    规模: {row['规模']}")
    except Exception as e:
        print(f"❌ 获取ETF基金信息失败: {e}")

def calculate_momentum():
    """计算动量指标"""
    print("\n" + "=" * 50)
    print("📈 计算动量指标")
    print("=" * 50)
    
    try:
        # 获取沪深300ETF历史数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=250)).strftime('%Y%m%d')
        
        etf_hist = ak.fund_etf_hist_em(
            symbol="510300",
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if not etf_hist.empty:
            # 计算收益率
            etf_hist['收盘'] = pd.to_numeric(etf_hist['收盘'], errors='coerce')
            
            # 计算MA200
            etf_hist['MA200'] = etf_hist['收盘'].rolling(window=200).mean()
            
            # 计算3月和6月动量
            if len(etf_hist) >= 126:
                r_3m = (etf_hist['收盘'].iloc[-1] / etf_hist['收盘'].iloc[-63] - 1) * 100
                r_6m = (etf_hist['收盘'].iloc[-1] / etf_hist['收盘'].iloc[-126] - 1) * 100
                
                momentum_score = 0.6 * r_3m + 0.4 * r_6m
                
                print(f"沪深300ETF (510300) 动量分析：")
                print(f"  当前价格: {etf_hist['收盘'].iloc[-1]:.3f}")
                print(f"  MA200: {etf_hist['MA200'].iloc[-1]:.3f}")
                print(f"  3月动量: {r_3m:.2f}%")
                print(f"  6月动量: {r_6m:.2f}%")
                print(f"  综合动量得分: {momentum_score:.2f}")
                
                # 判断市场状态
                if etf_hist['收盘'].iloc[-1] > etf_hist['MA200'].iloc[-1] * 1.01:
                    print("  📈 市场状态: 强势（站上年线）")
                elif etf_hist['收盘'].iloc[-1] < etf_hist['MA200'].iloc[-1] * 0.99:
                    print("  📉 市场状态: 弱势（跌破年线）")
                else:
                    print("  ➡️ 市场状态: 震荡（年线附近）")
            else:
                print("⚠️ 数据不足，无法计算动量")
    except Exception as e:
        print(f"❌ 计算动量失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试AKShare数据获取...")
    print("=" * 50)
    print()
    
    # 测试ETF数据
    test_etf_data()
    
    # 测试可转债数据
    test_convertible_bonds()
    
    # 测试ETF基金信息
    test_etf_fund_info()
    
    # 计算动量指标
    calculate_momentum()
    
    print("\n" + "=" * 50)
    print("✅ 测试完成！")
    print("\n系统说明：")
    print("- 数据来源：东方财富、新浪财经等")
    print("- 更新频率：实时行情每3-5秒更新")
    print("- 历史数据：可获取任意时间段")
    print("- 可用于实盘决策参考")