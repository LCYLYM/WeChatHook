# 微信群聊总结机器人使用指南

## 快速开始

### 1. 环境准备

确保你的系统满足以下要求：
- Windows 操作系统
- Python 3.8 或更高版本
- 微信PC版 (推荐 3.9.5.81)

### 2. 安装依赖

```bash
# 安装项目依赖
pip install -r wechat_summary_bot/requirements.txt

# 或者手动安装核心依赖
pip install wxhook openai schedule psutil loguru pyee requests xmltodict
```

### 3. 配置机器人

#### 方法一：使用启动脚本 (推荐)
```bash
python start_bot.py
```
启动脚本会自动检查环境、创建配置文件并引导你完成设置。

#### 方法二：手动配置
```bash
# 生成配置模板
python wechat_summary_bot/main.py config

# 编辑配置文件
# 编辑 wechat_summary_bot/config/bot_config.json
```

### 4. 关键配置说明

编辑 `wechat_summary_bot/config/bot_config.json` 文件：

```json
{
  "ai_config": {
    "openai_api_key": "sk-your-actual-api-key-here",  // ⭐ 必填
    "openai_base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  },
  "alert_config": {
    "enable_realtime_alerts": true,
    "target_user": "your_wechat_id_here",  // ⭐ 必填
    "urgency_threshold": 6
  }
}
```

**必须配置的项目：**
- `openai_api_key`: 你的 OpenAI API 密钥
- `target_user`: 接收推送消息的微信ID

### 5. 启动机器人

```bash
# 使用启动脚本（推荐）
python start_bot.py

# 或直接启动
python wechat_summary_bot/main.py
```

## 功能详解

### 📱 实时消息监听

机器人会自动监听所有群聊消息，支持：
- **文本消息**：直接分析内容
- **图片消息**：自动OCR提取文字
- **语音消息**：获取语音文件
- **其他类型**：表情、视频、卡片等

### 🚨 实时推送功能

当检测到包含关键词的重要消息时：

1. **关键词匹配**：系统预设了紧急、重要、deadline等关键词
2. **AI智能分析**：GPT-4评估消息紧急度（1-10级）
3. **即时推送**：超过阈值立即发送到你的微信

**推送示例：**
```
🚨 【重要消息提醒】

📱 群聊：项目开发群
👤 发送人：张经理
⏰ 时间：14:30:25
🎯 紧急度：8/10

💡 AI分析：检测到项目deadline相关的紧急通知，需要立即关注

📝 触发消息：
大家注意，项目deadline提前到本周五，请抓紧完成！

🔑 关键因素：deadline、紧急通知、时间敏感
```

### 📊 每日总结报告

每天20:00（可配置）自动生成总结：

1. **AI分析内容**：提取关键话题、重要事件
2. **生成总结**：智能摘要当天讨论内容
3. **推送报告**：发送到你的微信

**总结示例：**
```
📊 【每日群聊总结报告】

📅 日期：2024-01-15
📈 统计概览：
• 活跃群聊：5个
• 总消息数：245条
• 重要消息：12条

🏷️ 1. 项目开发群
💬 消息数：89条
⭐ 重要消息：5条

📝 今日总结：
今日主要讨论了新版本发布计划，确定了技术方案和时间安排。团队针对API优化和性能改进进行了深入讨论...

🔍 关键话题：版本发布、API优化、性能测试
📌 重要事件：确定发布时间、技术方案评审
✅ 待办事项：完成单元测试、更新API文档
```

### 🔄 智能去重

- 自动过滤重复消息（24小时内相同内容）
- 支持文本和多媒体内容去重
- 避免重复推送相同信息

## 高级功能

### 自定义关键词

你可以通过数据库添加自己的关键词：

```sql
-- 添加新的紧急关键词
INSERT INTO alert_keywords (keyword, category, weight) 
VALUES ('客户投诉', 'urgent', 2.5);

-- 修改关键词权重
UPDATE alert_keywords SET weight = 3.0 WHERE keyword = '系统故障';
```

### 手动操作

```bash
# 运行测试
python wechat_summary_bot/main.py test

# 手动生成昨日总结
python wechat_summary_bot/main.py summary

# 生成新的配置模板
python wechat_summary_bot/main.py config
```

### 查看统计信息

```bash
# 测试脚本会显示各种统计信息
python test_summary_bot.py
```

## 故障排除

### 常见问题

**Q: 机器人启动失败**
```
解决方案：
1. 确保微信客户端已启动
2. 检查是否有其他微信hook程序在运行
3. 查看日志文件 logs/wechat_bot.log
```

**Q: 没有收到推送消息**
```
检查项：
1. target_user 微信ID是否正确
2. 关键词配置是否合理
3. urgency_threshold 阈值是否太高
4. AI服务是否正常工作
```

**Q: AI分析失败**
```
解决方案：
1. 检查OpenAI API密钥是否有效
2. 确认网络连接正常
3. 查看API配额使用情况
4. 检查base_url配置
```

**Q: 数据库相关错误**
```
解决方案：
1. 检查data目录权限
2. 删除损坏的数据库文件重新初始化
3. 确保磁盘空间充足
```

### 日志分析

日志文件位置：`logs/wechat_bot.log`

重要日志关键词：
- `✅` 或 `success`：成功操作
- `❌` 或 `error`：错误信息
- `⚠️` 或 `warning`：警告信息
- `AI分析`：AI相关操作
- `推送`：消息推送相关

### 性能优化

1. **定期清理数据**：
   - 机器人会自动清理过期数据
   - 可手动调整 `data_retention_days` 配置

2. **调整AI调用频率**：
   - 提高 `urgency_threshold` 减少AI调用
   - 优化关键词配置避免误触发

3. **监控资源使用**：
   - 定期检查数据库大小
   - 监控内存和磁盘使用情况

## 安全建议

1. **保护API密钥**：
   - 不要将包含真实API密钥的配置文件提交到版本控制
   - 定期轮换API密钥

2. **数据隐私**：
   - 敏感群聊可以手动排除
   - 定期清理历史数据
   - 考虑加密存储重要信息

3. **网络安全**：
   - 使用HTTPS API端点
   - 考虑使用代理或VPN
   - 监控API调用日志

## 支持与反馈

如果遇到问题：
1. 查看本使用指南
2. 运行 `python test_summary_bot.py` 进行诊断
3. 检查日志文件
4. 提交Issue到项目仓库

---

**🎯 开始享受智能群聊总结服务吧！**