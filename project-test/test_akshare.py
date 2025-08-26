#!/usr/bin/env python3
"""测试AKShare数据获取功能"""

import asyncio
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

async def test_etf_list():
    """测试获取ETF列表"""
    print("测试获取ETF列表...")
    try:
        df = await asyncio.to_thread(ak.fund_etf_spot_em)
        print(f"成功获取 {len(df)} 只ETF")
        print(f"列名: {df.columns.tolist()[:5]}...")
        print(f"前3条数据:\n{df.head(3)}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

async def test_etf_history():
    """测试获取ETF历史数据"""
    print("\n测试获取ETF历史数据...")
    try:
        # 获取510300（沪深300ETF）的历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        df = await asyncio.to_thread(
            ak.fund_etf_hist_em,
            symbol="510300",
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq"
        )
        print(f"成功获取 {len(df)} 条历史数据")
        print(f"列名: {df.columns.tolist()}")
        print(f"最新3条数据:\n{df.tail(3)}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

async def test_convertible_bonds():
    """测试获取可转债数据"""
    print("\n测试获取可转债数据...")
    try:
        df = await asyncio.to_thread(ak.bond_zh_hs_cov_spot)
        print(f"成功获取 {len(df)} 只可转债")
        print(f"列名: {df.columns.tolist()[:5]}...")
        print(f"前3条数据:\n{df.head(3)}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

async def test_index_data():
    """测试获取指数数据"""
    print("\n测试获取指数数据...")
    try:
        # 获取沪深300指数
        df = await asyncio.to_thread(
            ak.stock_zh_index_daily,
            symbol="sh000300"
        )
        print(f"成功获取 {len(df)} 条指数数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 过滤最近30天的数据
        df['date'] = pd.to_datetime(df['date'])
        recent_date = datetime.now() - timedelta(days=30)
        df_recent = df[df['date'] >= recent_date]
        print(f"最近30天数据: {len(df_recent)} 条")
        print(f"最新3条数据:\n{df_recent.tail(3)}")
        return True
    except Exception as e:
        print(f"错误: {e}")
        return False

async def main():
    """运行所有测试"""
    print("=" * 50)
    print("AKShare 数据获取测试")
    print("=" * 50)
    
    results = {
        "ETF列表": await test_etf_list(),
        "ETF历史": await test_etf_history(),
        "可转债": await test_convertible_bonds(),
        "指数数据": await test_index_data()
    }
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过！AKShare数据源正常工作。")
    else:
        print("\n⚠️ 部分测试失败，请检查网络连接或API限制。")

if __name__ == "__main__":
    asyncio.run(main())