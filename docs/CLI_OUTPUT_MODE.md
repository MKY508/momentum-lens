# CLI 输出模式说明

## 概述

Momentum Lens CLI 支持两种输出模式：

1. **默认模式（交互式擦除）**：菜单会动态刷新，擦除之前的内容，保持界面简洁
2. **保留输出模式**：类似 Claude Code 的 CLI 界面，保留所有历史输出，不擦除之前的菜单

## 启用保留输出模式

### 方法 1：环境变量（推荐）

在运行脚本前设置环境变量：

```bash
# Linux/macOS
export MOMENTUM_CLI_PRESERVE_OUTPUT=1
./momentum_lens.sh

# 或者一行命令
MOMENTUM_CLI_PRESERVE_OUTPUT=1 ./momentum_lens.sh
```

```powershell
# Windows PowerShell
$env:MOMENTUM_CLI_PRESERVE_OUTPUT="1"
python -m momentum_cli

# 或者一行命令
$env:MOMENTUM_CLI_PRESERVE_OUTPUT="1"; python -m momentum_cli
```

```cmd
# Windows CMD
set MOMENTUM_CLI_PRESERVE_OUTPUT=1
python -m momentum_cli
```

### 方法 2：修改启动脚本

编辑 `momentum_lens.sh`，在脚本开头添加：

```bash
#!/usr/bin/env bash
export MOMENTUM_CLI_PRESERVE_OUTPUT=1

cd "$(dirname "$0")"
python3 -m momentum_cli "$@"
```

### 方法 3：在 shell 配置文件中永久设置

将以下内容添加到 `~/.bashrc` 或 `~/.zshrc`：

```bash
export MOMENTUM_CLI_PRESERVE_OUTPUT=1
```

然后重新加载配置：

```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 环境变量值

以下值会启用保留输出模式：
- `1`
- `true`
- `yes`

其他值或未设置该变量时，使用默认的交互式擦除模式。

## 两种模式的区别

### 默认模式（交互式擦除）

**优点：**
- 界面简洁，只显示当前菜单
- 适合终端窗口较小的环境
- 减少滚动，快速定位当前选项

**缺点：**
- 无法查看之前的菜单历史
- 在某些终端模拟器中可能出现闪烁
- 不适合需要回顾操作历史的场景

### 保留输出模式

**优点：**
- 保留完整的操作历史
- 类似 Claude Code 的 CLI 体验
- 便于调试和回顾操作流程
- 可以复制粘贴之前的输出

**缺点：**
- 输出较长，需要滚动查看
- 占用更多终端空间
- 在快速操作时可能显得冗余

## 推荐使用场景

### 使用默认模式（交互式擦除）

- 日常快速分析
- 终端窗口较小
- 熟悉菜单结构，不需要回顾历史

### 使用保留输出模式

- 调试和开发
- 需要记录完整操作流程
- 学习和熟悉工具
- 需要复制粘贴输出内容
- 在 tmux/screen 等终端复用器中使用

## 示例

### 默认模式输出

```
┌─ 功能清单 ─────────────────────────
  1 › 快速分析
  2 › 自定义分析
  3 › 回测工具
↑/↓ 选择 · 回车确认 · 数字快捷 · ESC 退出
请输入编号: _
```

（选择后，菜单会被擦除，显示新的内容）

### 保留输出模式输出

```
┌─ 功能清单 ─────────────────────────
  1 › 快速分析
  2 › 自定义分析
  3 › 回测工具
↑/↓ 选择 · 回车确认 · 数字快捷 · ESC 退出
请输入编号: 
选择: 1

┌─ 快速分析 ─────────────────────────
  1 › 核心资产
  2 › 卫星资产
  3 › 全市场
↑/↓ 选择 · 回车确认 · 数字快捷 · ESC 退出
请输入编号: 
选择: 1

正在运行分析...
```

（所有历史菜单和选择都保留在终端中）

## 技术实现

保留输出模式通过以下方式实现：

1. 检测环境变量 `MOMENTUM_CLI_PRESERVE_OUTPUT`
2. 在 `ui/menu.py` 和 `ui/interactive.py` 中跳过 ANSI 擦除序列
3. 在选择后打印选择结果，而不是擦除菜单

相关代码位置：
- `momentum_cli/ui/menu.py` - `erase_menu_block()` 函数
- `momentum_cli/ui/interactive.py` - `_handle_interactive_menu()` 函数

## 故障排除

### 问题：设置环境变量后仍然擦除输出

**解决方案：**
1. 确认环境变量值为 `1`、`true` 或 `yes`（不区分大小写）
2. 检查是否在正确的 shell 会话中设置
3. 尝试在命令行直接设置：`MOMENTUM_CLI_PRESERVE_OUTPUT=1 ./momentum_lens.sh`

### 问题：保留输出模式下输出过多

**解决方案：**
1. 使用 `clear` 命令清空终端
2. 切换回默认模式（取消设置环境变量）
3. 增大终端窗口大小或使用滚动缓冲区

### 问题：在某些终端中显示异常

**解决方案：**
1. 确保终端支持 ANSI 转义序列
2. 尝试更新终端模拟器
3. 使用保留输出模式避免 ANSI 擦除序列

## 反馈

如果您在使用过程中遇到问题或有改进建议，请提交 Issue 或 Pull Request。

