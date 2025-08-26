#!/usr/bin/env python3
"""
启动脚本 - 正确设置Python路径并启动Streamlit应用
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
backend_path = project_root / "backend"

# 确保路径在sys.path的最前面
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 设置环境变量
os.environ['PYTHONPATH'] = f"{project_root}:{backend_path}:" + os.environ.get('PYTHONPATH', '')

# 启动Streamlit应用
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    
    # 设置Streamlit参数
    sys.argv = [
        "streamlit",
        "run",
        str(backend_path / "app.py"),
        "--server.port=8501",
        "--server.address=localhost",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    
    # 运行Streamlit
    sys.exit(stcli.main())