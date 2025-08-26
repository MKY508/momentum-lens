#!/usr/bin/env python3
"""测试真实数据获取"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from data.datasource import AKShareAdapter
from indicators.momentum import MomentumCalculator
from datetime import datetime, timedelta
import pandas as pd

def test_real_etf_data():
    """测试真实ETF数据获取"""
    print("=" * 50)
    print("📊 测试真实ETF数据获取")
    print("=" * 50)
    
    adapter = AKShareAdapter()
    
    # 1. 获取ETF列表
    print("\n1. 获取ETF实时列表...")
    try:
        etf_list = adapter.get_etf_list()
        if etf_list is not None and not etf_list.empty:
            print(f"✅ 成功获取 {len(etf_list)} 只ETF")
            print("\n热门ETF示例：")
            
            # 显示一些主要ETF
            major_etfs = {
                '510300': '沪深300ETF',
                '510050': '上证50ETF', 
                '159915': '创业板ETF',
                '512660': '军工ETF',
                '518880': '黄金ETF',
                '510880': '红利ETF',
                '513500': '标普500',
                '159992': '创新药ETF',
                '512690': '酒ETF',
                '512010': '医药ETF'
            }
            
            for code, name in list(major_etfs.items())[:5]:
                etf_info = etf_list[etf_list['代码'].str.contains(code[-6:], na=False)]
                if not etf_info.empty:
                    row = etf_info.iloc[0]
                    print(f"  {code}: {name}")
                    print(f"    最新价: {row.get('最新价', 'N/A')}")
                    print(f"    涨跌幅: {row.get('涨跌幅', 'N/A')}%")
                    print(f"    成交额: {row.get('成交额', 'N/A')}")
        else:
            print("⚠️  ETF列表为空")
    except Exception as e:
        print(f"❌ 获取ETF列表失败: {e}")
    
    # 2. 获取具体ETF历史数据
    print("\n2. 获取沪深300ETF(510300)历史数据...")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        etf_hist = adapter.get_etf_price('510300', start_date, end_date)
        if etf_hist is not None and not etf_hist.empty:
            print(f"✅ 成功获取 {len(etf_hist)} 条历史数据")
            print("\n最近5个交易日：")
            recent = etf_hist.tail(5)
            for _, row in recent.iterrows():
                print(f"  {row['日期']}: 收盘 {row['收盘']:.3f}, 涨跌幅 {row['涨跌幅']:.2f}%")
            
            # 计算动量指标
            print("\n3. 计算动量指标...")
            calc = MomentumCalculator()
            
            # 计算MA200
            ma200 = calc.calculate_ma(etf_hist['收盘'], 200)
            current_price = etf_hist['收盘'].iloc[-1]
            ma200_value = ma200.iloc[-1] if not pd.isna(ma200.iloc[-1]) else 0
            
            if ma200_value > 0:
                ratio = current_price / ma200_value
                print(f"  当前价格: {current_price:.3f}")
                print(f"  MA200: {ma200_value:.3f}")
                print(f"  价格/MA200: {ratio:.3f}")
                
                if ratio > 1.01:
                    print("  📈 市场状态: 强势（站上年线）")
                elif ratio < 0.99:
                    print("  📉 市场状态: 弱势（跌破年线）")
                else:
                    print("  ➡️ 市场状态: 震荡（年线附近）")
            
            # 计算动量
            r63 = calc.calculate_momentum(etf_hist, 63)
            r126 = calc.calculate_momentum(etf_hist, 126)
            if r63 is not None and r126 is not None:
                momentum_score = 0.6 * r63 + 0.4 * r126
                print(f"\n  3月动量: {r63:.2%}")
                print(f"  6月动量: {r126:.2%}")
                print(f"  综合动量得分: {momentum_score:.2f}")
                
        else:
            print("⚠️  历史数据为空")
    except Exception as e:
        print(f"❌ 获取历史数据失败: {e}")
    
    # 3. 获取沪深300指数数据
    print("\n4. 获取沪深300指数数据...")
    try:
        index_data = adapter.get_index_data('000300')
        if index_data is not None and not index_data.empty:
            print(f"✅ 成功获取指数数据")
            recent = index_data.tail(1).iloc[0]
            print(f"  最新收盘: {recent.get('close', 'N/A')}")
            print(f"  日涨跌幅: {((recent.get('close', 0) / recent.get('open', 1) - 1) * 100):.2f}%")
        else:
            print("⚠️  指数数据为空")
    except Exception as e:
        print(f"❌ 获取指数数据失败: {e}")
    
    # 4. 获取可转债数据
    print("\n5. 获取可转债数据...")
    try:
        cb_data = adapter.get_convertible_bonds()
        if cb_data is not None and not cb_data.empty:
            print(f"✅ 成功获取 {len(cb_data)} 只可转债")
            
            # 筛选优质可转债
            quality_cb = cb_data[
                (cb_data['转股溢价率'] < 20) & 
                (cb_data['债券价格'] < 130) &
                (cb_data['债券价格'] > 90)
            ].head(5)
            
            if not quality_cb.empty:
                print("\n优质可转债（低溢价、合理价格）：")
                for _, cb in quality_cb.iterrows():
                    print(f"  {cb['债券代码']}: {cb['债券简称']}")
                    print(f"    价格: {cb['债券价格']:.2f}")
                    print(f"    溢价率: {cb['转股溢价率']:.2f}%")
                    print(f"    到期收益率: {cb.get('到期收益率', 'N/A')}")
        else:
            print("⚠️  可转债数据为空")
    except Exception as e:
        print(f"❌ 获取可转债数据失败: {e}")

def test_momentum_ranking():
    """测试动量排名"""
    print("\n" + "=" * 50)
    print("🏆 ETF动量排名")
    print("=" * 50)
    
    adapter = AKShareAdapter()
    calc = MomentumCalculator()
    
    # 热门ETF代码列表
    etf_codes = [
        ('510300', '沪深300ETF'),
        ('510050', '上证50ETF'),
        ('159915', '创业板ETF'),
        ('512660', '军工ETF'),
        ('512690', '酒ETF'),
        ('512010', '医药ETF'),
        ('159992', '创新药ETF'),
        ('512880', '证券ETF'),
        ('515030', '新能源车ETF'),
        ('516160', '新能源ETF')
    ]
    
    momentum_scores = []
    
    for code, name in etf_codes:
        try:
            # 获取历史数据
            hist = adapter.get_etf_price(code)
            if hist is not None and len(hist) > 126:
                # 计算动量
                r63 = calc.calculate_momentum(hist, 63)
                r126 = calc.calculate_momentum(hist, 126)
                
                if r63 is not None and r126 is not None:
                    score = 0.6 * r63 + 0.4 * r126
                    momentum_scores.append({
                        'code': code,
                        'name': name,
                        'r3m': r63,
                        'r6m': r126,
                        'score': score
                    })
                    print(f"  {code} {name}: 动量得分 {score:.2f}")
        except Exception as e:
            print(f"  {code} {name}: 获取失败 - {e}")
    
    # 排序并显示Top5
    if momentum_scores:
        momentum_df = pd.DataFrame(momentum_scores)
        momentum_df = momentum_df.sort_values('score', ascending=False)
        
        print("\n🏆 动量Top5 ETF：")
        for i, row in momentum_df.head(5).iterrows():
            print(f"  {row['code']} {row['name']}")
            print(f"    3月动量: {row['r3m']:.2%}")
            print(f"    6月动量: {row['r6m']:.2%}")
            print(f"    综合得分: {row['score']:.2f}")

if __name__ == "__main__":
    print("🚀 开始测试真实数据获取...")
    print("注意：数据来源于AKShare，可能需要一些时间加载\n")
    
    # 测试真实数据
    test_real_etf_data()
    
    # 测试动量排名
    test_momentum_ranking()
    
    print("\n✅ 测试完成！")
    print("\n提示：")
    print("- 如果某些数据获取失败，可能是网络问题或API限制")
    print("- 可以在config/config.yaml中配置数据源参数")
    print("- 系统会自动缓存数据，减少重复请求")