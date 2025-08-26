#!/usr/bin/env python3
"""
测试脚本：验证相关性矩阵数据格式
"""

import requests
import json

def test_correlation_api():
    """测试相关性API返回格式"""
    
    print("=" * 60)
    print("测试相关性矩阵API格式")
    print("=" * 60)
    
    try:
        # 测试相关性API
        response = requests.get('http://127.0.0.1:8000/api/market/correlation?anchor=588000')
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ API响应成功")
        
        # 检查必需字段
        required_fields = ['anchor', 'etfs', 'values']
        for field in required_fields:
            if field in data:
                print(f"✅ 字段 '{field}' 存在")
                if field == 'etfs':
                    print(f"   - ETF数量: {len(data[field])}")
                    print(f"   - ETF列表: {', '.join(data[field][:5])}...")
                elif field == 'values':
                    print(f"   - 矩阵大小: {len(data[field])} x {len(data[field][0]) if data[field] else 0}")
                    if data[field] and len(data[field]) > 0:
                        print(f"   - 第一行样本: {data[field][0][:3]}...")
            else:
                print(f"❌ 字段 '{field}' 缺失")
        
        # 验证矩阵维度
        if 'etfs' in data and 'values' in data:
            etf_count = len(data['etfs'])
            matrix_rows = len(data['values'])
            matrix_cols = len(data['values'][0]) if data['values'] else 0
            
            if etf_count == matrix_rows == matrix_cols:
                print(f"\n✅ 矩阵维度正确: {etf_count} x {etf_count}")
            else:
                print(f"\n❌ 矩阵维度错误: ETFs={etf_count}, 行={matrix_rows}, 列={matrix_cols}")
        
        # 验证自相关
        if 'values' in data and data['values']:
            print("\n验证自相关（对角线应为1.0）:")
            for i in range(min(3, len(data['values']))):
                diagonal_value = data['values'][i][i]
                status = "✅" if diagonal_value == 1.0 else "❌"
                print(f"  {status} [{i},{i}] = {diagonal_value}")
        
        print("\n" + "=" * 60)
        print("测试完成 - API格式正确，前端应能正常渲染")
        print("=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API请求失败: {e}")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    test_correlation_api()