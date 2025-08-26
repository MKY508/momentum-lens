#!/usr/bin/env python3
"""
快速分析最新的可转债CSV文件
自动查找并分析最新的CSV数据
"""

import os
import glob
import subprocess
import sys

def find_latest_csv():
    """查找最新的CSV文件"""
    csv_files = glob.glob("*.csv")
    if not csv_files:
        print("❌ 没有找到CSV文件")
        return None
    
    # 按修改时间排序，获取最新的
    csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return csv_files[0]

def main():
    print("=" * 60)
    print("可转债快速分析工具")
    print("=" * 60)
    
    # 查找CSV文件
    csv_file = find_latest_csv()
    if not csv_file:
        print("\n请先准备CSV数据文件：")
        print("1. 从集思录下载可转债数据")
        print("2. 或使用 1_HTML转CSV工具.py 从网页提取")
        return
    
    print(f"\n✅ 找到CSV文件: {csv_file}")
    print("开始分析...\n")
    
    # 调用分析工具
    subprocess.run([sys.executable, "2_CSV筛选分析工具.py", csv_file])

if __name__ == "__main__":
    main()