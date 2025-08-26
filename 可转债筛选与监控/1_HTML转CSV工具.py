#!/usr/bin/env python3
"""
集思录可转债数据提取工具
Extract convertible bond data from JiSiLu HTML files
"""

import re
import csv
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def extract_bond_data_from_html(html_file_path):
    """
    从集思录HTML文件中提取可转债数据
    
    Args:
        html_file_path: HTML文件路径
    
    Returns:
        list: 包含所有可转债数据的字典列表
    """
    bonds = []
    
    try:
        # 读取HTML文件
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 查找表格
        table = soup.find('table', {'id': 'flex_cb'})
        
        if table:
            # 提取表头
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find_all('tr')[-1]  # 获取最后一行作为实际的列标题
                for th in header_row.find_all(['th', 'td']):
                    header_text = th.get_text(strip=True)
                    # 清理表头文本
                    header_text = re.sub(r'\s+', '', header_text)
                    headers.append(header_text)
            
            # 提取表体数据
            tbody = table.find('tbody')
            if tbody:
                for row in tbody.find_all('tr'):
                    cells = row.find_all(['td'])
                    if cells and len(cells) > 1:  # 跳过空行或汇总行
                        bond_data = {}
                        for i, cell in enumerate(cells):
                            if i < len(headers):
                                # 提取单元格文本，处理特殊格式
                                cell_text = cell.get_text(strip=True)
                                # 获取data-value属性（如果存在）
                                if cell.has_attr('data-value'):
                                    cell_text = cell['data-value']
                                bond_data[headers[i]] = cell_text
                        
                        # 只添加有效数据行
                        if bond_data and any(bond_data.values()):
                            bonds.append(bond_data)
        
        # 如果没有找到表格数据，尝试从JavaScript变量中提取
        if not bonds:
            # 查找包含数据的script标签
            scripts = soup.find_all('script')
            for script in scripts:
                script_text = script.string or ''
                
                # 查找数据模式 - 可能在变量赋值中
                # 例如: var data = [{...}, {...}]
                data_pattern = r'(?:var\s+\w+\s*=\s*|data:\s*)(\[[\s\S]*?\])\s*[;,}]'
                matches = re.findall(data_pattern, script_text)
                
                for match in matches:
                    try:
                        # 尝试解析为JSON
                        data = json.loads(match)
                        if isinstance(data, list) and len(data) > 0:
                            # 检查是否是可转债数据
                            if isinstance(data[0], dict) and any(key in data[0] for key in ['bond_id', 'bond_nm', 'price']):
                                bonds.extend(data)
                                break
                    except:
                        continue
        
        # 如果还是没有数据，尝试从tbody的内联数据中提取
        if not bonds:
            # 定义要提取的字段
            bond_fields = [
                '代码', '转债名称', '现价', '涨跌幅', '正股名称', 
                '正股价', '正股涨跌', '正股PB', '转股价', '转股价值',
                '转股溢价率', '纯债价值', '债底溢价率', '债券评级', '期权价值',
                '正股波动率', '回售触发价', '强赎触发价', '转债占比', '资产负债率',
                '基金持仓', '到期时间', '剩余年限', '剩余规模', '成交额',
                '换手率', '到期税前收益', '到期税后收益', '回售收益', '双低'
            ]
            
            # 尝试提取任何包含这些字段的表格
            all_tables = soup.find_all('table')
            for table in all_tables:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    if rows and len(rows) > 0:
                        # 检查是否包含可转债相关数据
                        first_row = rows[0]
                        cells = first_row.find_all(['td'])
                        if len(cells) > 10:  # 可转债表格通常有很多列
                            for row in rows:
                                cells = row.find_all(['td'])
                                if cells and len(cells) > 10:
                                    bond_data = {}
                                    for i, cell in enumerate(cells):
                                        cell_text = cell.get_text(strip=True)
                                        if i < len(bond_fields):
                                            bond_data[bond_fields[i]] = cell_text
                                    
                                    if bond_data and any(bond_data.values()):
                                        bonds.append(bond_data)
        
        return bonds
        
    except Exception as e:
        print(f"解析HTML文件时出错: {e}")
        return []

def save_to_csv(bonds, output_file):
    """
    将可转债数据保存为CSV文件
    
    Args:
        bonds: 可转债数据列表
        output_file: 输出CSV文件路径
    """
    if not bonds:
        print("没有找到可转债数据")
        return False
    
    try:
        # 获取所有字段名
        all_fields = set()
        for bond in bonds:
            all_fields.update(bond.keys())
        
        # 排序字段名，确保重要字段在前
        priority_fields = ['代码', '转债名称', '现价', '涨跌幅', '正股名称', '正股价', '转股溢价率']
        fieldnames = []
        for field in priority_fields:
            if field in all_fields:
                fieldnames.append(field)
                all_fields.remove(field)
        fieldnames.extend(sorted(all_fields))
        
        # 写入CSV文件
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bonds)
        
        print(f"成功保存 {len(bonds)} 条可转债数据到 {output_file}")
        return True
        
    except Exception as e:
        print(f"保存CSV文件时出错: {e}")
        return False

def save_to_excel(bonds, output_file):
    """
    将可转债数据保存为Excel文件
    
    Args:
        bonds: 可转债数据列表
        output_file: 输出Excel文件路径
    """
    if not bonds:
        print("没有找到可转债数据")
        return False
    
    try:
        # 转换为DataFrame
        df = pd.DataFrame(bonds)
        
        # 尝试转换数值列
        numeric_columns = ['现价', '涨跌幅', '正股价', '正股涨跌', '转股价', 
                          '转股价值', '转股溢价率', '纯债价值', '债底溢价率',
                          '剩余年限', '剩余规模', '成交额', '换手率']
        
        for col in numeric_columns:
            if col in df.columns:
                # 清理数据：移除百分号、逗号等
                df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '')
                # 尝试转换为数值
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 保存到Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='可转债数据', index=False)
            
            # 调整列宽
            worksheet = writer.sheets['可转债数据']
            for column in df.columns:
                column_width = max(df[column].astype(str).str.len().max(), len(column)) + 2
                column_width = min(column_width, 50)  # 限制最大宽度
                col_idx = df.columns.get_loc(column)
                worksheet.column_dimensions[chr(65 + col_idx)].width = column_width
        
        print(f"成功保存 {len(bonds)} 条可转债数据到 {output_file}")
        return True
        
    except Exception as e:
        print(f"保存Excel文件时出错: {e}")
        return False

def main():
    """主函数"""
    # 默认输入文件
    default_input = "/Users/maokaiyue/Downloads/(1) 可转债 - 可转债 - 集思录.html"
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = default_input
    
    # 检查文件是否存在
    if not Path(input_file).exists():
        print(f"文件不存在: {input_file}")
        return
    
    print(f"正在处理文件: {input_file}")
    
    # 提取数据
    bonds = extract_bond_data_from_html(input_file)
    
    if bonds:
        print(f"成功提取 {len(bonds)} 条可转债数据")
        
        # 生成输出文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_output = f"/Users/maokaiyue/Downloads/可转债数据_{timestamp}.csv"
        excel_output = f"/Users/maokaiyue/Downloads/可转债数据_{timestamp}.xlsx"
        
        # 保存为CSV
        save_to_csv(bonds, csv_output)
        
        # 如果安装了pandas，也保存为Excel
        try:
            import pandas
            save_to_excel(bonds, excel_output)
        except ImportError:
            print("未安装pandas，跳过Excel输出")
        
        # 显示前几条数据作为预览
        print("\n数据预览（前5条）:")
        for i, bond in enumerate(bonds[:5], 1):
            print(f"\n第{i}条:")
            for key, value in list(bond.items())[:5]:  # 只显示前5个字段
                print(f"  {key}: {value}")
    else:
        print("未能提取到可转债数据")
        print("可能原因:")
        print("1. HTML文件中的数据是动态加载的")
        print("2. 数据格式已变化")
        print("3. 文件不完整或损坏")

if __name__ == "__main__":
    main()