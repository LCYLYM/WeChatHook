#!/usr/bin/env python3
"""
微信群聊总结机器人配置设置工具
"""
import os
import sys
import json
from pathlib import Path


def main():
    """配置设置主函数"""
    print("🔧 微信群聊总结机器人配置设置")
    print("=" * 50)
    
    config_file = Path("wechat_summary_bot/config/bot_config.json")
    config_dir = config_file.parent
    
    # 确保配置目录存在
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取当前配置或创建默认配置
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ 找到现有配置文件")
    else:
        print("📄 创建新的配置文件")
        config = {
            "database_path": "./data/wechat_bot.db",
            "data_retention_days": 180,
            "daily_summary_time": "20:00",
            "cleanup_interval_hours": 24,
            "log_level": "INFO",
            "alert_config": {
                "enable_realtime_alerts": False,
                "urgency_threshold": 6,
                "max_context_messages": 10,
                "target_user": "your_wechat_id_here"
            },
            "ai_config": {
                "openai_api_key": "your_openai_api_key_here",
                "openai_base_url": "https://api.openai.com/v1",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.3
            }
        }
    
    print("\n🔑 配置OpenAI API Key")
    current_api_key = config["ai_config"]["openai_api_key"]
    if current_api_key in ["your_openai_api_key_here", ""]:
        print("当前未设置API Key")
    else:
        print(f"当前API Key: {current_api_key[:10]}...")
    
    new_api_key = input("请输入新的OpenAI API Key (直接回车跳过): ").strip()
    if new_api_key:
        config["ai_config"]["openai_api_key"] = new_api_key
        print("✅ API Key已更新")
    
    print("\n👤 配置目标用户")
    current_user = config["alert_config"]["target_user"]
    if current_user in ["your_wechat_id_here", "demo_user", ""]:
        print("当前未设置目标用户")
    else:
        print(f"当前目标用户: {current_user}")
    
    new_user = input("请输入微信用户ID (直接回车跳过): ").strip()
    if new_user:
        config["alert_config"]["target_user"] = new_user
        config["alert_config"]["enable_realtime_alerts"] = True
        print("✅ 目标用户已更新，实时推送已启用")
    
    print("\n📊 其他配置")
    print(f"数据库路径: {config['database_path']}")
    print(f"日志级别: {config['log_level']}")
    print(f"每日总结时间: {config['daily_summary_time']}")
    
    # 保存配置
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 配置已保存到: {config_file}")
        
        # 验证配置
        api_key_ok = config["ai_config"]["openai_api_key"] not in ["your_openai_api_key_here", "", "sk-demo"]
        user_ok = (not config["alert_config"]["enable_realtime_alerts"] or 
                  config["alert_config"]["target_user"] not in ["your_wechat_id_here", "demo_user", ""])
        
        if api_key_ok and user_ok:
            print("🎉 配置完成！可以启动机器人了")
            print("\n启动命令:")
            print("  python start_bot.py")
            print("  或")
            print("  python wechat_summary_bot/main.py")
        else:
            print("\n⚠️ 配置不完整:")
            if not api_key_ok:
                print("  - 请设置有效的OpenAI API Key")
            if not user_ok:
                print("  - 请设置目标用户或禁用实时推送")
            print("\n可以重新运行此脚本完成配置")
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 配置已取消")
    except Exception as e:
        print(f"\n❌ 配置失败: {e}")
        sys.exit(1)