"""
Backend module entry point
"""
import sys
import os
from pathlib import Path

# 设置Python路径
backend_path = Path(__file__).parent
project_path = backend_path.parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(project_path))

# 设置环境变量
os.environ['PYTHONPATH'] = f"{backend_path}:{project_path}:" + os.environ.get('PYTHONPATH', '')

if __name__ == "__main__":
    # 启动Streamlit应用
    import streamlit.web.cli as stcli
    
    sys.argv = [
        "streamlit",
        "run",
        str(backend_path / "app.py"),
        "--server.port=8501",
        "--server.address=localhost",
    ]
    
    sys.exit(stcli.main())