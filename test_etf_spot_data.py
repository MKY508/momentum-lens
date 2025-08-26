#!/usr/bin/env python3
"""
使用akshare获取ETF实时数据和计算动量
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def test_etf_spot():
    """测试获取ETF实时数据"""
    
    print("=" * 80)
    print("获取ETF实时行情数据")
    print("=" * 80)
    
    try:
        # 获取所有ETF的实时行情
        df = ak.fund_etf_spot_em()
        
        # 我们关注的ETF列表
        target_etfs = {
            '588000': '科创50ETF',
            '512760': '半导体ETF', 
            '512720': '计算机ETF',
            '516160': '新能源ETF',
            '515790': '光伏ETF',
            '512800': '银行ETF',
            '512400': '有色金属ETF',
            '512000': '券商ETF',
            '515030': '新能源车ETF',
            '516010': '游戏动漫ETF',
            '159869': '游戏ETF',
            '512170': '医疗ETF',
        }
        
        results = []
        
        for code, name in target_etfs.items():
            etf_data = df[df['代码'] == code]
            
            if not etf_data.empty:
                row = etf_data.iloc[0]
                
                # 获取涨跌幅
                change_pct = float(row.get('涨跌幅', 0))
                
                # 获取成交额（转换为亿元）
                volume = float(row.get('成交额', 0)) / 100000000
                
                print(f"{code} {name}: 今日涨幅={change_pct:.2f}%, 成交额={volume:.2f}亿")
                
                results.append({
                    'code': code,
                    'name': name,
                    'change_pct': change_pct,
                    'volume': volume,
                    'current_price': float(row.get('最新价', 0))
                })
        
        return results
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        return []

def test_etf_history():
    """测试获取ETF历史数据"""
    
    print("\n" + "=" * 80)
    print("获取ETF历史数据并计算动量")
    print("=" * 80)
    
    # 测试几个主要ETF
    test_codes = [
        ('sh588000', '科创50ETF'),
        ('sh512760', '半导体ETF'),
        ('sh512800', '银行ETF'),
        ('sh516160', '新能源ETF'),
    ]
    
    results = []
    
    for symbol, name in test_codes:
        try:
            # 获取历史数据（不带日期参数）
            df = ak.fund_etf_hist_sina(symbol=symbol)
            
            if df is not None and len(df) > 0:
                # 处理数据
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # 获取最近150个交易日的数据
                df = df.tail(150)
                
                if len(df) >= 60:
                    current_price = df['close'].iloc[-1]
                    price_60d_ago = df['close'].iloc[-60]
                    r60 = ((current_price / price_60d_ago) - 1) * 100
                    
                    if len(df) >= 120:
                        price_120d_ago = df['close'].iloc[-120]
                        r120 = ((current_price / price_120d_ago) - 1) * 100
                    else:
                        r120 = r60 * 0.8
                    
                    score = 0.6 * r60 + 0.4 * r120
                    
                    results.append({
                        'code': symbol[2:],
                        'name': name,
                        'r60': round(r60, 2),
                        'r120': round(r120, 2),
                        'score': round(score, 2)
                    })
                    
                    print(f"✅ {name}: r60={r60:.2f}%, r120={r120:.2f}%, score={score:.2f}")
                else:
                    print(f"⚠️ {name}: 数据不足（只有{len(df)}天）")
            else:
                print(f"❌ {name}: 无法获取历史数据")
                
        except Exception as e:
            print(f"❌ {name}: 错误 - {e}")
    
    # 排序
    if results:
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print("\n" + "=" * 80)
        print("动量排名")
        print("=" * 80)
        for i, etf in enumerate(results, 1):
            print(f"#{i} {etf['name']}: Score={etf['score']}, r60={etf['r60']}%, r120={etf['r120']}%")
    
    return results

def get_etf_fund_info():
    """获取ETF基金信息"""
    print("\n" + "=" * 80)
    print("获取ETF基金列表")
    print("=" * 80)
    
    try:
        # 获取ETF列表
        df = ak.fund_etf_category_sina(symbol="ETF基金")
        
        # 筛选我们关注的ETF
        target_codes = ['588000', '512760', '512800', '516160', '515790', '512720']
        
        for code in target_codes:
            etf_info = df[df['基金代码'].str.contains(code, na=False)]
            if not etf_info.empty:
                print(f"找到: {etf_info.iloc[0]['基金简称']} ({code})")
        
    except Exception as e:
        print(f"获取ETF列表失败: {e}")

if __name__ == "__main__":
    # 测试实时数据
    spot_data = test_etf_spot()
    
    # 测试历史数据
    history_data = test_etf_history()
    
    # 获取ETF信息
    get_etf_fund_info()
    
    print("\n测试完成！")