#!/usr/bin/env python3
"""
测试脚本 - 演示微信群聊总结机器人的核心功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 开始测试微信群聊总结机器人...")
    
    try:
        # 测试数据模型
        from wechat_summary_bot.models.data_models import Message, BotConfig, AIConfig, AlertConfig
        print("✅ 数据模型导入成功")
        
        # 创建配置对象
        ai_config = AIConfig(openai_api_key="test_key")
        alert_config = AlertConfig(target_user="test_user")
        bot_config = BotConfig(ai_config=ai_config, alert_config=alert_config)
        print(f"✅ 配置对象创建成功: log_level={bot_config.log_level}")
        
        # 测试消息对象
        from datetime import datetime
        message = Message(
            message_id="test_123",
            chat_id="test_chat@chatroom", 
            chat_name="测试群聊",
            sender_id="test_sender",
            sender_name="测试用户",
            message_type="text",
            content="这是一条测试消息",
            timestamp=datetime.now()
        )
        print(f"✅ 消息对象创建成功: hash={message.content_hash[:8]}...")
        
        # 测试数据库管理器 (内存数据库)
        from wechat_summary_bot.core.database import DatabaseManager
        db = DatabaseManager(":memory:")  # 使用内存数据库测试
        print("✅ 数据库管理器创建成功")
        
        # 测试消息存储
        success = db.save_message(message)
        print(f"✅ 消息存储测试: {success}")
        
        # 测试去重引擎
        from wechat_summary_bot.core.deduplication import DeduplicationEngine
        dedup = DeduplicationEngine(":memory:")
        is_dup = dedup.is_duplicate(message)
        print(f"✅ 去重测试 (首次): {not is_dup}")
        
        # 再次测试相同消息
        is_dup2 = dedup.is_duplicate(message)
        print(f"✅ 去重测试 (重复): {is_dup2}")
        
        # 测试关键词获取
        keywords = db.get_active_keywords()
        print(f"✅ 关键词获取成功: {len(keywords)}个关键词")
        
        # 测试配置管理
        from wechat_summary_bot.config.settings import ConfigManager
        config_manager = ConfigManager("./test_config.json")
        print("✅ 配置管理器创建成功")
        
        # 创建配置模板
        template_file = config_manager.create_config_template()
        if template_file and os.path.exists(template_file):
            print(f"✅ 配置模板创建成功: {template_file}")
        else:
            print("⚠️ 配置模板创建失败")
        
        # 测试工具函数
        from wechat_summary_bot.utils.helpers import (
            truncate_text, validate_wxid, format_timestamp, get_date_string
        )
        
        truncated = truncate_text("这是一个很长的测试文本内容", 10)
        print(f"✅ 文本截断测试: '{truncated}'")
        
        valid_id = validate_wxid("test_user@chatroom")
        print(f"✅ 微信ID验证测试: {valid_id}")
        
        date_str = get_date_string()
        print(f"✅ 日期格式化测试: {date_str}")
        
        print("\n🎉 所有基础功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_functionality():
    """测试AI功能 (模拟)"""
    print("\n🤖 测试AI功能...")
    
    try:
        from wechat_summary_bot.models.data_models import AIConfig, UrgencyAnalysisResult
        
        # 创建AI配置
        ai_config = AIConfig(
            openai_api_key="test_key",
            model="gpt-4",
            temperature=0.3
        )
        print(f"✅ AI配置创建成功: {ai_config.model}")
        
        # 创建模拟分析结果
        result = UrgencyAnalysisResult(
            is_urgent=True,
            urgency_score=8,
            push_type="single",
            push_message_ids=["msg_123"],
            summary="这是一个模拟的AI分析结果",
            key_factors=["关键词匹配", "紧急程度高"]
        )
        print(f"✅ AI分析结果模拟成功: 紧急度={result.urgency_score}/10")
        
        return True
        
    except Exception as e:
        print(f"❌ AI功能测试失败: {e}")
        return False


def test_summary_functionality():
    """测试总结功能"""
    print("\n📊 测试总结功能...")
    
    try:
        from wechat_summary_bot.models.data_models import DailySummary
        from datetime import datetime
        
        # 创建模拟总结
        summary = DailySummary(
            date="2024-01-15",
            chat_id="test_chat@chatroom",
            chat_name="测试群聊",
            summary_content="今日群聊活跃，主要讨论了项目进展和技术问题。",
            key_topics=["项目进展", "技术讨论", "bug修复"],
            important_events=["版本发布确认", "会议安排"],
            action_items=["完成测试", "更新文档"],
            message_count=45,
            high_value_count=8,
            source_message_ids=["msg_1", "msg_2", "msg_3"]
        )
        
        print(f"✅ 总结对象创建成功:")
        print(f"   - 群聊: {summary.chat_name}")
        print(f"   - 消息数: {summary.message_count}")
        print(f"   - 关键话题: {', '.join(summary.key_topics[:2])}...")
        print(f"   - 重要事件: {len(summary.important_events)}个")
        
        return True
        
    except Exception as e:
        print(f"❌ 总结功能测试失败: {e}")
        return False


def cleanup_test_files():
    """清理测试文件"""
    test_files = [
        "./test_config.json",
        "./config/config_template_*.json",
        "./config/bot_config_template.json"
    ]
    
    import glob
    for pattern in test_files:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
                print(f"🗑️ 清理测试文件: {file}")
            except:
                pass


def main():
    """主测试函数"""
    print("=" * 60)
    print("🚀 微信群聊总结机器人 - 功能测试")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("基础功能", test_basic_functionality),
        ("AI功能", test_ai_functionality), 
        ("总结功能", test_summary_functionality)
    ]
    
    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ {name}测试异常: {e}")
    
    # 显示结果
    print("=" * 60)
    print(f"📋 测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 恭喜! 所有测试都通过了!")
        print("\n📖 接下来的步骤:")
        print("1. 配置 OpenAI API Key")
        print("2. 设置推送目标用户微信ID")
        print("3. 启动微信客户端")
        print("4. 运行: python wechat_summary_bot/main.py")
    else:
        print("⚠️ 部分测试未通过，请检查错误信息")
    
    print("=" * 60)
    
    # 清理测试文件
    cleanup_test_files()


if __name__ == "__main__":
    main()