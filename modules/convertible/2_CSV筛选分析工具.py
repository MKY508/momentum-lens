#!/usr/bin/env python3
"""
简单的可转债CSV分析器（无需外部依赖）
"""

import csv
import os
from datetime import datetime
from pathlib import Path

# 创建必要目录
os.makedirs('reports', exist_ok=True)


def clean_numeric(value):
    """清理数值字段"""
    if not value or value == '-' or '会员' in value:
        return None
    # 移除百分号、逗号、星号等
    value = str(value).replace('%', '').replace(',', '').replace('*', '').replace('！', '')
    try:
        return float(value)
    except:
        return None


def analyze_csv(csv_file):
    """分析CSV文件"""
    print(f"\n{'='*60}")
    print("可转债CSV数据分析")
    print(f"{'='*60}")
    print(f"数据文件: {csv_file}\n")
    
    # 读取CSV
    bonds = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bonds.append(row)
    
    print(f"✅ 读取到 {len(bonds)} 条可转债数据")
    
    # 数据预处理和筛选
    qualified_bonds = []
    
    for bond in bonds:
        # 提取关键字段
        code = bond.get('代码', '')
        name = bond.get('转债名称', '').replace('!', '')
        price = clean_numeric(bond.get('现价'))
        premium = clean_numeric(bond.get('转股溢价率'))
        scale = clean_numeric(bond.get('剩余规模(亿元)'))
        rating = bond.get('债券评级', '')
        years_left = clean_numeric(bond.get('剩余年限'))
        double_low = clean_numeric(bond.get('双低'))
        turnover = clean_numeric(bond.get('成交额(万元)'))
        
        # 跳过数据不完整的
        if not price or not name:
            continue
        
        # 应用筛选条件
        passed = True
        reasons = []
        
        # 1. 价格条件 (90-130)
        if price and (price < 90 or price > 130):
            passed = False
            reasons.append(f"价格超限({price:.2f})")
        
        # 2. 溢价条件 (0-40%)
        if premium is not None and (premium < 0 or premium > 40):
            passed = False
            reasons.append(f"溢价超限({premium:.2f}%)")
        
        # 3. 规模条件 (>=5亿)
        if scale and scale < 5:
            passed = False
            reasons.append(f"规模不足({scale:.2f}亿)")
        
        # 4. 评级条件 (AA-及以上)
        good_ratings = ['AAA', 'AA+', 'AA', 'AA-']
        if rating and rating not in good_ratings:
            passed = False
            reasons.append(f"评级不足({rating})")
        
        # 5. 期限条件 (0.5-3.5年)
        if years_left is not None and (years_left < 0.5 or years_left > 3.5):
            passed = False
            reasons.append(f"期限不符({years_left:.2f}年)")
        
        # 记录通过筛选的债券
        if passed:
            # 计算简单得分
            score = 0
            
            # 价格得分（越低越好）
            if price:
                score += (130 - price) / 40 * 0.2
            
            # 溢价得分（越低越好）
            if premium is not None:
                score += (40 - premium) / 40 * 0.3
            
            # 双低得分（越低越好）
            if double_low:
                score += (200 - double_low) / 100 * 0.3 if double_low < 200 else 0
            
            # 评级得分
            rating_scores = {'AAA': 1.0, 'AA+': 0.9, 'AA': 0.8, 'AA-': 0.7}
            score += rating_scores.get(rating, 0.5) * 0.2
            
            qualified_bonds.append({
                'code': code,
                'name': name,
                'price': price,
                'premium': premium,
                'scale': scale,
                'rating': rating,
                'years_left': years_left,
                'double_low': double_low,
                'turnover': turnover,
                'score': score
            })
    
    print(f"✅ 通过筛选: {len(qualified_bonds)} 只")
    
    # 按得分排序
    qualified_bonds.sort(key=lambda x: x['score'], reverse=True)
    
    # 生成报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"reports/简单分析报告_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("可转债筛选分析报告\n")
        f.write("="*60 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据文件: {csv_file}\n\n")
        
        f.write(f"筛选结果:\n")
        f.write(f"  原始数据: {len(bonds)} 只\n")
        f.write(f"  通过筛选: {len(qualified_bonds)} 只\n\n")
        
        f.write("-"*60 + "\n")
        f.write("TOP 10 推荐买入:\n")
        f.write("-"*60 + "\n\n")
        
        for i, bond in enumerate(qualified_bonds[:10], 1):
            f.write(f"{i}. {bond['name']} ({bond['code']})\n")
            f.write(f"   现价: {bond['price']:.2f}  ")
            if bond['premium'] is not None:
                f.write(f"溢价: {bond['premium']:.2f}%  ")
            if bond['double_low']:
                f.write(f"双低: {bond['double_low']:.2f}  ")
            f.write(f"评级: {bond['rating']}  ")
            f.write(f"得分: {bond['score']:.3f}")
            f.write("\n\n")
        
        f.write("-"*60 + "\n")
        f.write("投资建议:\n")
        f.write("-"*60 + "\n")
        f.write("1. 建议分散投资8-10只可转债\n")
        f.write("2. 单券仓位不超过总资金的10%\n")
        f.write("3. 重点关注双低值低于150的品种\n")
        f.write("4. 注意强赎风险，及时关注正股走势\n")
        f.write("5. 建议采用网格交易策略，网格宽度3-5%\n\n")
        
        f.write("风险提示:\n")
        f.write("- 本报告仅供参考，不构成投资建议\n")
        f.write("- 请在实际投资前进行充分的尽职调查\n")
    
    print(f"✅ 报告已生成: {report_file}\n")
    
    # 显示TOP 5
    print("🎯 TOP 5 推荐买入:")
    print("-"*60)
    for i, bond in enumerate(qualified_bonds[:5], 1):
        print(f"{i}. {bond['name']} ({bond['code']})")
        print(f"   现价: {bond['price']:.2f}", end='')
        if bond['premium'] is not None:
            print(f"  溢价: {bond['premium']:.2f}%", end='')
        if bond['double_low']:
            print(f"  双低: {bond['double_low']:.2f}", end='')
        print(f"  得分: {bond['score']:.3f}")
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)
    
    return qualified_bonds


def main():
    """主函数"""
    import sys
    
    # 获取CSV文件
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # 默认文件
        csv_file = '可转债数据_20250825_151056.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ 文件不存在: {csv_file}")
        print("\n使用方法:")
        print("python3 simple_analyzer.py [CSV文件路径]")
        return
    
    # 运行分析
    analyze_csv(csv_file)


if __name__ == "__main__":
    main()