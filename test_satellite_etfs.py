#!/usr/bin/env python3
"""
测试脚本：验证Satellite ETF池是否完整
"""

import requests
import json

def test_satellite_etfs():
    """测试Satellite模块的ETF列表"""
    
    # 期望的完整ETF列表
    expected_etfs = {
        # 成长线
        '588000': '科创50',
        '512760': '半导体',
        '512720': '计算机',
        '516010': '游戏动漫',
        '159869': '游戏',
        # 电新链
        '516160': '新能源',
        '515790': '光伏',
        '515030': '新能源车',
        # 其他行业
        '512400': '有色金属',
        '512800': '银行',
        '512000': '券商',
        '512170': '医疗'
    }
    
    print("=" * 60)
    print("测试 Satellite ETF 池完整性")
    print("=" * 60)
    
    try:
        # 1. 测试动量排名API
        response = requests.get('http://127.0.0.1:8000/api/market/momentum-rankings')
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ API响应成功")
        print(f"返回ETF数量: {len(data)}")
        
        # 检查返回的ETF
        returned_codes = {etf['code'] for etf in data}
        expected_codes = set(expected_etfs.keys())
        
        print(f"\n期望ETF数量: {len(expected_codes)}")
        print(f"实际ETF数量: {len(returned_codes)}")
        
        # 找出缺失的ETF
        missing = expected_codes - returned_codes
        if missing:
            print(f"\n❌ 缺失的ETF:")
            for code in missing:
                print(f"  - {code}: {expected_etfs[code]}")
        else:
            print("\n✅ 所有期望的ETF都已返回")
        
        # 找出额外的ETF
        extra = returned_codes - expected_codes
        if extra:
            print(f"\n⚠️ 额外的ETF: {extra}")
        
        # 显示返回的ETF详情
        print("\n返回的ETF列表（按动量评分排序）:")
        print("-" * 60)
        print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'类型':<10} {'评分':<8} {'60日涨幅':<10} {'120日涨幅':<10}")
        print("-" * 60)
        
        for i, etf in enumerate(data, 1):
            print(f"{i:<4} {etf['code']:<8} {etf['name']:<12} {etf.get('type', 'N/A'):<10} "
                  f"{etf['score']:<8.2f} {etf['r60']:<10.1f}% {etf['r120']:<10.1f}%")
        
        # 2. 测试相关性API
        print("\n" + "=" * 60)
        print("测试相关性数据")
        print("=" * 60)
        
        response = requests.get('http://127.0.0.1:8000/api/market/correlation?anchor=588000')
        response.raise_for_status()
        corr_data = response.json()
        
        if 'correlations' in corr_data:
            print(f"✅ 相关性数据返回成功")
            print(f"相关性对数量: {len(corr_data['correlations'])}")
            
            # 显示一些样本相关性
            print("\n样本相关性数据:")
            for item in corr_data['correlations'][:5]:
                print(f"  {item['etf1']} <-> {item['etf2']}: {item['correlation']:.3f}")
        else:
            print("❌ 相关性数据格式错误")
        
        # 3. 分组统计
        print("\n" + "=" * 60)
        print("ETF分组统计")
        print("=" * 60)
        
        groups = {}
        for etf in data:
            etf_type = etf.get('type', 'unknown')
            if etf_type not in groups:
                groups[etf_type] = []
            groups[etf_type].append(etf['code'] + ' ' + etf['name'])
        
        for group_name, etfs in groups.items():
            print(f"\n{group_name} ({len(etfs)}个):")
            for etf in etfs:
                print(f"  - {etf}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API请求失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    test_satellite_etfs()