# 微信群聊总结机器人

基于 WeChatHook 框架开发的智能微信群聊总结机器人，实现实时监听、智能去重、AI分析和定时总结功能。

## 🚀 主要功能

### 📱 实时消息监听
- 监听所有群聊消息（文本、图片、语音、视频、表情）
- 支持图片 OCR 文字提取
- 支持语音消息处理
- 自动识别发送者和群聊信息

### 🔄 智能去重处理
- 基于内容哈希的重复消息过滤
- 24小时内相同内容自动去重
- 支持多媒体内容去重
- 自动清理过期去重记录

### ⚡ 实时推送提醒
- 关键词触发机制
- AI 智能紧急度分析 (1-10级)
- 上下文相关性判断
- 即时推送到指定用户

### 📊 每日总结报告
- AI 驱动的高质量总结生成
- 自动提取关键话题和重要事件
- 识别待办事项和行动计划
- 定时生成和推送总结报告

### 🤖 AI 分析引擎
- 集成 OpenAI GPT-4
- 智能紧急度评估
- 内容价值判断
- 结构化数据提取

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   微信客户端     │    │   消息收集层     │    │   去重处理层     │
│  (WeChatHook)   │────│  Message        │────│   SQLite        │
│                 │    │  Collector      │    │   Dedup         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据存储层     │    │   AI分析层      │    │   实时推送层     │
│   SQLite        │────│   OpenAI        │────│   Real-time     │
│   Database      │    │   GPT-4         │    │   Push          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   定时总结层     │
                    │   Daily         │
                    │   Summary       │
                    └─────────────────┘
```

## 🛠️ 安装部署

### 环境要求
- Python 3.8+
- 微信 PC 版 (推荐 3.9.5.81)
- Windows 操作系统

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd WeChatHook/wechat_summary_bot
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置机器人**
```bash
# 生成配置模板
python main.py config

# 编辑配置文件
# 编辑 config/bot_config.json，填入必要信息：
# - OpenAI API Key
# - 推送目标用户微信ID
# - 其他个性化配置
```

4. **启动机器人**
```bash
python main.py
```

## ⚙️ 配置说明

### 基础配置
```json
{
  "database_path": "./data/wechat_bot.db",    // 数据库文件路径
  "data_retention_days": 180,                // 数据保留天数
  "daily_summary_time": "20:00",             // 每日总结生成时间
  "cleanup_interval_hours": 24,              // 清理任务间隔
  "log_level": "INFO"                        // 日志级别
}
```

### 推送配置
```json
{
  "alert_config": {
    "enable_realtime_alerts": true,          // 启用实时推送
    "urgency_threshold": 6,                  // 推送阈值 (1-10)
    "max_context_messages": 10,              // 上下文消息数量
    "target_user": "your_wechat_id"          // 接收推送的用户
  }
}
```

### AI 配置
```json
{
  "ai_config": {
    "openai_api_key": "sk-xxx",              // OpenAI API密钥
    "openai_base_url": "https://api.openai.com/v1",  // API地址
    "model": "gpt-4",                        // 使用的模型
    "max_tokens": 2000,                      // 最大token数
    "temperature": 0.3                       // 生成随机性
  }
}
```

## 📋 使用指南

### 命令行选项

```bash
# 正常启动
python main.py

# 功能测试
python main.py test

# 生成配置模板
python main.py config

# 手动生成昨日总结
python main.py summary
```

### 关键词配置

系统预设了常用关键词，包括：
- **紧急类**: 紧急、急、重要、deadline、截止、故障等
- **工作类**: @所有人、通知、会议、任务、项目等

可通过数据库直接修改 `alert_keywords` 表自定义关键词。

### 实时推送示例

当检测到包含关键词的消息时，系统会：
1. 关键词快速筛选
2. AI 智能分析紧急度
3. 超过阈值立即推送

推送消息格式：
```
🚨 【重要消息提醒】

📱 群聊：技术讨论群
👤 发送人：张三
⏰ 时间：14:30:25
🎯 紧急度：8/10

💡 AI分析：检测到系统故障报告，需要立即关注和处理

📝 触发消息：
服务器出现故障，请紧急处理！
```

### 每日总结示例

```
📊 【每日群聊总结报告】

📅 日期：2024-01-15
📈 统计概览：
• 活跃群聊：5个
• 总消息数：245条
• 重要消息：12条

🏷️ 1. 技术讨论群
💬 消息数：89条
⭐ 重要消息：5条

📝 今日总结：
今日主要讨论了新版本发布计划和API优化方案...

🔍 关键话题：版本发布、API优化、bug修复
📌 重要事件：确定发布时间为本周五
✅ 待办事项：完成测试用例编写、更新文档
```

## 📁 项目结构

```
wechat_summary_bot/
├── core/                    # 核心功能模块
│   ├── message_collector.py    # 消息收集器
│   ├── deduplication.py        # 去重引擎
│   ├── database.py             # 数据库管理
│   ├── realtime_alerts.py      # 实时推送
│   ├── ai_service.py           # AI分析服务
│   └── daily_summary.py        # 每日总结
├── models/                  # 数据模型
│   └── data_models.py          # 核心数据结构
├── config/                  # 配置管理
│   ├── settings.py             # 配置管理器
│   └── bot_config_example.json # 配置示例
├── utils/                   # 工具函数
│   └── helpers.py              # 通用辅助函数
├── data/                    # 数据目录
│   └── wechat_bot.db           # SQLite数据库
├── logs/                    # 日志目录
├── temp/                    # 临时文件
├── main.py                  # 主程序入口
├── requirements.txt         # 依赖列表
└── README.md               # 说明文档
```

## 🎯 核心特性

### 智能去重
- 使用 MD5 哈希算法对消息内容去重
- 支持文本和提取内容的组合去重
- 24小时滑动窗口，避免误杀
- 自动清理过期去重记录

### AI 分析
- GPT-4 驱动的内容理解
- 多维度紧急度评估（时效性、重要性、行动性）
- 上下文相关性分析
- 结构化 JSON 输出

### 数据存储
- SQLite 轻量级数据库
- 完整的消息历史记录
- 高效的索引设计
- 自动数据清理机制

### 任务调度
- 基于 schedule 库的定时任务
- 支持每日和间隔任务
- 多线程异步执行
- 异常恢复机制

## 🔧 高级配置

### 自定义关键词
```sql
-- 添加新关键词
INSERT INTO alert_keywords (keyword, category, weight) 
VALUES ('客户投诉', 'urgent', 2.5);

-- 修改关键词权重
UPDATE alert_keywords SET weight = 3.0 WHERE keyword = '系统异常';

-- 禁用关键词
UPDATE alert_keywords SET is_active = FALSE WHERE keyword = '日常';
```

### 数据库维护
```python
# 手动清理数据
python -c "
from wechat_summary_bot.core.database import DatabaseManager
db = DatabaseManager()
db.cleanup_old_data(30)  # 清理30天前的数据
"

# 获取统计信息
python -c "
from wechat_summary_bot.core.deduplication import DeduplicationEngine
dedup = DeduplicationEngine('./data/wechat_bot.db')
print(dedup.get_duplicate_stats())
"
```

## 🚨 注意事项

1. **微信版本兼容性**
   - 推荐使用微信 3.9.5.81 版本
   - 确保 WeChatHook 注入成功

2. **API 配额管理**
   - OpenAI API 有调用限制
   - 建议设置合理的紧急度阈值
   - 监控 API 使用情况

3. **数据隐私**
   - 敏感群聊可手动排除
   - 定期清理历史数据
   - 妥善保管配置文件

4. **系统资源**
   - 数据库大小随消息量增长
   - 建议定期备份重要数据
   - 监控磁盘空间使用

## 🐛 故障排除

### 常见问题

**Q: 机器人无法启动**
- 检查微信客户端是否运行
- 确认 WeChatHook 注入成功
- 查看日志文件定位问题

**Q: AI 分析失败**
- 检查 OpenAI API Key 有效性
- 确认网络连接正常
- 查看 API 配额使用情况

**Q: 消息去重过于严格**
- 调整去重时间窗口
- 检查内容哈希算法
- 查看去重统计信息

**Q: 推送消息不及时**
- 检查关键词配置
- 调整紧急度阈值
- 确认目标用户 ID 正确

## 📈 性能优化

### 数据库优化
- 定期执行 `VACUUM` 清理
- 适当调整索引策略
- 监控查询性能

### 内存优化
- 控制消息缓存大小
- 及时清理临时文件
- 监控内存使用情况

### 网络优化
- 配置 API 请求超时
- 实施重试机制
- 使用连接池

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙋‍♂️ 支持

如有问题或建议，请：
1. 查看本文档
2. 搜索已有 Issue
3. 创建新 Issue
4. 联系项目维护者

---

**⚡ 让AI为您的群聊总结赋能！**