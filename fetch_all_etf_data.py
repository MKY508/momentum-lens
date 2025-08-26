#!/usr/bin/env python3
"""
获取所有卫星ETF的真实动量数据
"""

import akshare as ak
import pandas as pd
from datetime import datetime
from tqdm import tqdm

def fetch_all_satellite_etf_data():
    """获取所有卫星ETF的真实数据"""
    
    # 所有卫星候选池ETF
    etf_list = [
        ('sh588000', '588000', '科创50ETF', 'Growth'),
        ('sh512760', '512760', '半导体ETF', 'Growth'),
        ('sh512720', '512720', '计算机ETF', 'Growth'),
        ('sh516010', '516010', '游戏动漫ETF', 'Growth'),
        ('sz159869', '159869', '游戏ETF', 'Growth'),
        ('sh516160', '516160', '新能源ETF', 'NewEnergy'),
        ('sh515790', '515790', '光伏ETF', 'NewEnergy'),
        ('sh515030', '515030', '新能源车ETF', 'NewEnergy'),
        ('sh512400', '512400', '有色金属ETF', 'Industry'),
        ('sh512800', '512800', '银行ETF', 'Industry'),
        ('sh512000', '512000', '券商ETF', 'Industry'),
        ('sh512170', '512170', '医疗ETF', 'Industry'),
    ]
    
    results = []
    
    print("=" * 80)
    print("获取所有卫星ETF的真实数据")
    print("=" * 80)
    
    # 先获取实时行情
    spot_df = ak.fund_etf_spot_em()
    
    for symbol, code, name, etf_type in tqdm(etf_list):
        try:
            # 获取历史数据
            df = ak.fund_etf_hist_sina(symbol=symbol)
            
            if df is not None and len(df) > 0:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                df = df.tail(150)  # 获取最近150个交易日
                
                r60 = 0
                r120 = 0
                
                if len(df) >= 60:
                    current_price = df['close'].iloc[-1]
                    price_60d_ago = df['close'].iloc[-60]
                    r60 = ((current_price / price_60d_ago) - 1) * 100
                    
                    if len(df) >= 120:
                        price_120d_ago = df['close'].iloc[-120]
                        r120 = ((current_price / price_120d_ago) - 1) * 100
                    else:
                        # 数据不足120天，使用60天数据估算
                        r120 = r60 * 0.8
                else:
                    print(f"⚠️ {name}: 历史数据不足")
                    continue
                
                # 计算动量评分
                score = 0.6 * r60 + 0.4 * r120
                
                # 获取实时成交额
                spot_data = spot_df[spot_df['代码'] == code]
                if not spot_data.empty:
                    volume = float(spot_data.iloc[0]['成交额']) / 100000000  # 转换为亿元
                else:
                    volume = 10.0  # 默认值
                
                results.append({
                    'code': code,
                    'name': name,
                    'type': etf_type,
                    'r60': round(r60, 2),
                    'r120': round(r120, 2),
                    'score': round(score, 2),
                    'volume': round(volume, 2)
                })
                
            else:
                print(f"❌ {name}: 无法获取历史数据")
                
        except Exception as e:
            print(f"❌ {name}: 错误 - {e}")
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "=" * 80)
    print("真实ETF动量排名（按评分排序）")
    print("=" * 80)
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'类型':<10} {'60日':<8} {'120日':<8} {'评分':<8} {'成交额':<8}")
    print("-" * 80)
    
    for i, etf in enumerate(results, 1):
        print(f"{i:<4} {etf['code']:<8} {etf['name']:<12} {etf['type']:<10} "
              f"{etf['r60']:>7.2f}% {etf['r120']:>7.2f}% {etf['score']:>7.2f} {etf['volume']:>7.2f}亿")
    
    # 生成Python代码
    print("\n" + "=" * 80)
    print("生成的Python代码（复制到main_lite.py）:")
    print("=" * 80)
    print("    satellite_etfs = [")
    
    for etf in results:
        print(f'        {{"code": "{etf["code"]}", "name": "{etf["name"]}", '
              f'"type": "{etf["type"]}", "score": {etf["score"]}, '
              f'"r60": {etf["r60"]}, "r120": {etf["r120"]}, "volume": {etf["volume"]}}},')
    
    print("    ]")
    
    return results

if __name__ == "__main__":
    results = fetch_all_satellite_etf_data()
    
    print("\n" + "=" * 80)
    print("数据获取完成！")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)