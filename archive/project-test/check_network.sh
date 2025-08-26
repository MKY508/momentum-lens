#!/bin/bash

echo "🔍 检查网络配置..."
echo ""

# 检查 hosts 文件
echo "1. 检查 /etc/hosts 文件中的 localhost 配置:"
grep -E "127\.0\.0\.1.*localhost|localhost.*127\.0\.0\.1" /etc/hosts
if [ $? -eq 0 ]; then
    echo "  ✅ localhost 配置正常"
else
    echo "  ⚠️  localhost 未正确配置"
    echo "  建议添加: 127.0.0.1 localhost"
fi

echo ""
echo "2. 测试 localhost 解析:"
ping -c 1 localhost > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ localhost 可以正常解析"
else
    echo "  ❌ localhost 无法解析"
fi

echo ""
echo "3. 测试 127.0.0.1 连接:"
ping -c 1 127.0.0.1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ 127.0.0.1 可以正常连接"
else
    echo "  ❌ 127.0.0.1 无法连接"
fi

echo ""
echo "4. 检查端口占用:"
echo "  端口 3000 (前端):"
lsof -i :3000 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "    ⚠️  端口 3000 已被占用"
    lsof -i :3000 | head -2
else
    echo "    ✅ 端口 3000 可用"
fi

echo "  端口 8000 (后端):"
lsof -i :8000 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "    ⚠️  端口 8000 已被占用"
    lsof -i :8000 | head -2
else
    echo "    ✅ 端口 8000 可用"
fi

echo ""
echo "📝 建议解决方案:"
echo "  1. 如果 localhost 无法解析，请编辑 /etc/hosts 文件添加:"
echo "     127.0.0.1 localhost"
echo "  2. 如果端口被占用，可以:"
echo "     - 关闭占用端口的程序"
echo "     - 或修改配置文件使用其他端口"
echo "  3. 项目已配置为使用 127.0.0.1 而不是 localhost"