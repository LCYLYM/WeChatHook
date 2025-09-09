# 微信群聊总结机器人设置指南

## 🚀 快速开始

### 1. 环境准备

**系统要求:**
- Windows 10/11 (微信Hook功能仅支持Windows)
- Python 3.8 或更高版本
- 微信PC版 3.9.5.81 (推荐版本)

**安装依赖:**
```bash
cd WeChatHook
pip install -r wechat_summary_bot/requirements.txt
```

### 2. 配置机器人

**生成配置文件:**
```bash
python wechat_summary_bot/main.py config
```

**编辑配置文件 `wechat_summary_bot/config/bot_config.json`:**

```json
{
  "ai_config": {
    "openai_api_key": "你的OpenAI API Key",
    "openai_base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
  },
  "alert_config": {
    "enable_realtime_alerts": true,
    "target_user": "你的微信ID"
  }
}
```

### 3. 启动机器人

**使用启动脚本(推荐):**
```bash
python start_bot.py
```

**直接启动:**
```bash
python wechat_summary_bot/main.py
```

**测试模式(无需微信):**
```bash
python wechat_summary_bot/main.py test
```

## 📋 配置说明

### OpenAI API Key 获取
1. 访问 [OpenAI官网](https://platform.openai.com)
2. 注册账号并登录
3. 进入 API Keys 页面
4. 创建新的 API Key
5. 将 Key 填入配置文件

### 微信ID 获取
1. 启动微信PC版
2. 发送任意消息给自己(文件传输助手)
3. 查看机器人日志中显示的用户ID
4. 将用户ID填入配置文件

## 🛠️ 功能测试

### 测试AI服务
```bash
python wechat_summary_bot/main.py test
```

### 手动生成总结
```bash
python wechat_summary_bot/main.py summary
```

## ❌ 故障排除

### 问题：start-wechat.exe 执行失败
**可能原因：**
1. 微信PC版未启动
2. 微信版本不兼容
3. 权限不足
4. 文件被杀毒软件拦截

**解决方案：**
1. 启动微信PC版并完成登录
2. 下载微信3.9.5.81版本
3. 以管理员权限运行程序
4. 将程序目录添加到杀毒软件白名单

### 问题：OpenAI API Key 未配置
**解决方案：**
1. 编辑 `wechat_summary_bot/config/bot_config.json`
2. 将 `openai_api_key` 设置为有效的API Key
3. 重新启动机器人

### 问题：推送目标用户未设置
**解决方案：**
1. 编辑配置文件中的 `target_user`
2. 设置为你的微信ID (如: wxid_1234567890)
3. 或者设置 `enable_realtime_alerts` 为 `false` 禁用推送

## 📖 详细配置

参考 [完整配置文档](wechat_summary_bot/README.md) 了解所有配置选项。