# Momentum Lens 故障排除手册

## 🔥 常见问题和解决方案

### 1. "Cannot read properties of undefined (reading 'toFixed')"

**症状**：Satellite模块或其他地方出现undefined错误

**原因**：API返回的数据缺少必需字段

**解决方案**：
```python
# 确保所有数字字段都有值
"r60": 15.0,  # 不能是undefined
"r120": 14.0,
"volume": 12500000,
"spread": 0.05
```

### 2. "Invalid time value"

**症状**：Core模块日期格式化错误

**原因**：前端期望`nextDate`，后端返回`nextExecution`

**解决方案**：
```python
# 后端返回两个字段保证兼容性
"nextDate": "2024-08-27",
"nextExecution": "2024-08-27"
```

### 3. API 404错误

**症状**：所有API请求返回404

**原因**：路径不匹配（/api/v1 vs /api）

**解决方案**：
```python
# 使用 /api 而不是 /api/v1
@app.get("/api/health")  # ✅
@app.get("/api/v1/health")  # ❌
```

### 4. CORS错误（403/400）

**症状**：OPTIONS请求失败，WebSocket连接被拒

**原因**：CORS配置不正确

**解决方案**：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)
```

### 5. WebSocket连接错误

**症状**：持续的WebSocket 403错误

**原因**：Socket.IO尝试连接但后端不支持

**解决方案**：
```python
# 添加占位端点避免错误
@app.get("/socket.io/")
async def socketio_fallback():
    return {"message": "Socket.IO not supported in lite version"}
```

## 🛠️ 快速修复命令

### 一键修复
```bash
./fix_all.sh
```

### 手动修复步骤
```bash
# 1. 停止后端
ps aux | grep -E 'python.*main_lite' | grep -v grep | awk '{print $2}' | xargs kill

# 2. 重启后端
cd backend
./venv/bin/python main_lite.py > ../backend.log 2>&1 &

# 3. 测试API
curl http://localhost:8000/api/health

# 4. 检查日志
tail -f backend.log
```

## 📊 API端点清单

### 必需的端点和字段

| 端点 | 必需字段 | 说明 |
|------|---------|------|
| `/api/portfolio/holdings` | targetWeight, currentWeight, deviation | Core模块需要 |
| `/api/portfolio/dca-schedule` | nextDate (不是nextExecution!) | 日期格式化需要 |
| `/api/market/momentum-rankings` | r60, r120, volume, spread | Satellite模块需要 |
| `/api/market/correlation` | etfs[], values[][] | 相关性矩阵需要 |
| `/api/market/hs300-chart` | prices[], ma200[] | 图表需要Unix时间戳 |

## 🎯 调试技巧

### 1. 查看具体错误
```javascript
// 打开浏览器控制台
// 查看具体的错误堆栈
// 找到是哪个字段undefined
```

### 2. 测试单个API
```bash
# 测试特定端点
curl -s http://localhost:8000/api/portfolio/holdings | python3 -m json.tool

# 检查字段是否完整
```

### 3. 对比前后端数据格式
```typescript
// 前端期望的类型（在types/index.ts中）
interface Holding {
  targetWeight: number;  // 必需
  currentWeight: number; // 必需
  deviation: number;     // 必需
}

// 后端必须返回完全匹配的字段
```

## ⚠️ 不要做的事情

1. **不要**随意改变API路径（保持/api前缀）
2. **不要**删除字段（即使看起来没用）
3. **不要**改变日期格式（保持YYYY-MM-DD）
4. **不要**忽略undefined错误（会级联失败）

## 💡 最佳实践

1. **每次修改后端后重启**
```bash
# 修改 main_lite.py 后必须重启
./fix_all.sh
```

2. **使用测试脚本验证**
```bash
./test_api_status.sh
```

3. **保持数据完整性**
- 宁可返回模拟数据，也不要返回undefined
- 所有数字字段都要有默认值
- 日期字段要有合理的值

## 🆘 紧急恢复

如果一切都乱了：

```bash
# 1. 完全停止所有服务
pkill -f python
pkill -f node

# 2. 清理日志
> backend.log
> frontend.log

# 3. 重新启动
cd backend && ./venv/bin/python main_lite.py &
cd frontend && npm start &

# 4. 等待服务启动
sleep 5

# 5. 验证
curl http://localhost:8000/api/health
```

## 📝 记住的教训

1. **前后端字段名必须完全匹配**（大小写敏感）
2. **日期格式很重要**（nextDate vs nextExecution）
3. **所有数字字段都要初始化**（避免undefined）
4. **CORS配置要完整**（包括OPTIONS方法）
5. **API路径要一致**（/api不是/api/v1）

---

*"按下葫芦浮起瓢"是软件开发的常态，关键是要有系统的解决方案。*

最后更新：2025-08-25