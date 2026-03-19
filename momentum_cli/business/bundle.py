"""数据包管理模块"""
from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional


def update_data_bundle_interactive(
    bundle_status_func: Callable[[bool, Optional[Dict]], Dict[str, Any]],
    find_rqalpha_func: Callable[[], Optional[list]],
    on_refresh_callback: Callable[[], None],
    wait_for_ack_func: Callable[[], None],
    colorize_func: Callable,
) -> None:
    """交互式更新数据包
    
    Args:
        bundle_status_func: 获取bundle状态的函数
        find_rqalpha_func: 查找rqalpha命令的函数
        on_refresh_callback: 刷新完成后的回调
        wait_for_ack_func: 等待确认的函数
        colorize_func: 着色函数
    """
    # 移除本地版本检查，直接调用 RQAlpha 命令
    # RQAlpha 的 download-bundle/update-bundle 会自行判断是否需要更新
    # status = bundle_status_func(True, {})
    # if status.get("state") == "fresh":
    #     version_display = status.get("version") or status.get("version_raw") or "最新版本"
    #     print(colorize_func(f"当前数据包 {version_display} 已是最新，无需重新下载。", "info"))
    #     wait_for_ack_func()
    #     return
    
    command = find_rqalpha_func()
    if not command:
        print(colorize_func("未找到 rqalpha 可执行文件，请先安装或激活环境后再试。", "danger"))
        wait_for_ack_func()
        return
    
    print(colorize_func("开始下载最新的 RQAlpha 数据包，这可能需要几分钟……", "info"))
    download_command = command + ["download-bundle"]
    try:
        download_result = subprocess.run(
            download_command, cwd=str(Path.home()), check=False
        )
    except Exception as exc:
        print(colorize_func(f"download-bundle 调用失败: {exc}", "danger"))
        wait_for_ack_func()
        return
    
    if download_result.returncode == 0:
        bundle_path = Path.home() / ".rqalpha" / "bundle"
        print(colorize_func("数据下载完成，分析将基于最新 bundle。", "value_positive"))
        print(colorize_func(
            f"数据路径: {bundle_path}，包含 ETF/股票/指数的日线行情，可回溯到历史最早可用日期。",
            "menu_hint"
        ))
        on_refresh_callback()
        wait_for_ack_func()
        return
    
    printable_dl = " ".join(download_command)
    print(
        colorize_func(
            f"download-bundle 失败（退出码 {download_result.returncode}）。正在尝试 rqalpha update-bundle……",
            "warning",
        )
    )
    
    update_command = command + ["update-bundle"]
    try:
        update_result = subprocess.run(update_command, cwd=str(Path.home()), check=False)
    except Exception as exc:
        print(colorize_func(f"update-bundle 调用失败: {exc}", "danger"))
        wait_for_ack_func()
        return
    
    if update_result.returncode == 0:
        bundle_path = Path.home() / ".rqalpha" / "bundle"
        print(colorize_func("数据更新完成，分析将基于最新 bundle。", "value_positive"))
        print(colorize_func(
            f"数据路径: {bundle_path}，包含 ETF/股票/指数的日线行情，可回溯到历史最早可用日期。",
            "menu_hint"
        ))
        on_refresh_callback()
        wait_for_ack_func()
        return
    
    printable_up = " ".join(update_command)
    print(
        colorize_func(
            "数据更新失败。您可以手动执行以下命令后重试: "
            f"{printable_dl} 或 {printable_up}",
            "danger",
        )
    )
    wait_for_ack_func()

