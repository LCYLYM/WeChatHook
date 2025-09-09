#!/usr/bin/env python3
"""
微信群聊总结机器人启动脚本
"""
import os
import sys
import json
from pathlib import Path

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本需要3.8或更高")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查必要模块
    required_modules = [
        'wxhook', 'openai', 'schedule', 'psutil', 
        'loguru', 'pyee', 'requests'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"❌ {module}")
    
    if missing_modules:
        print(f"\n缺少模块: {', '.join(missing_modules)}")
        print("请运行: pip install -r wechat_summary_bot/requirements.txt")
        return False
    
    return True


def check_configuration():
    """检查配置文件"""
    print("\n⚙️ 检查配置...")
    
    config_file = Path("./wechat_summary_bot/config/bot_config.json")
    
    if not config_file.exists():
        print("❌ 配置文件不存在")
        print("正在创建配置模板...")
        
        # 创建配置模板
        try:
            sys.path.insert(0, str(Path.cwd()))
            from wechat_summary_bot.config.settings import ConfigManager
            
            config_manager = ConfigManager(str(config_file))
            template_file = config_manager.create_config_template()
            
            print(f"✅ 配置模板已创建: {template_file}")
            print(f"✅ 默认配置已创建: {config_file}")
            print("\n📝 请编辑配置文件，填入以下必要信息:")
            print("   - OpenAI API Key (ai_config.openai_api_key)")
            print("   - 推送目标用户微信ID (alert_config.target_user)")
            print("   - 其他个性化设置")
            
            return False  # 需要用户配置
            
        except Exception as e:
            print(f"❌ 创建配置失败: {e}")
            return False
    
    # 检查配置内容
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查关键配置
        api_key = config.get('ai_config', {}).get('openai_api_key', '')
        target_user = config.get('alert_config', {}).get('target_user', '')
        
        issues = []
        if not api_key or api_key in ['your_openai_api_key_here', 'test_key']:
            issues.append("OpenAI API Key 未配置或为默认值")
        
        if not target_user or target_user in ['your_wechat_id_here', 'test_user']:
            issues.append("推送目标用户未配置或为默认值")
        
        if issues:
            print("⚠️ 配置检查发现问题:")
            for issue in issues:
                print(f"   - {issue}")
            print(f"\n请编辑配置文件: {config_file}")
            return False
        
        print("✅ 配置文件检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False


def start_bot():
    """启动机器人"""
    print("\n🚀 启动微信群聊总结机器人...")
    
    try:
        # 添加项目路径
        sys.path.insert(0, str(Path.cwd()))
        
        # 导入并启动机器人
        from wechat_summary_bot.main import WeChatSummaryBot
        
        bot = WeChatSummaryBot()
        return bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户取消，机器人已停止")
        return True
    except Exception as e:
        error_message = str(e)
        print(f"\n❌ 启动失败: {error_message}")
        
        # 根据错误类型提供具体的解决建议
        if "未发现微信进程" in error_message:
            print("\n🔧 解决方案:")
            print("1. 启动微信PC版并完成登录")
            print("2. 确保微信版本为3.9.5.81（推荐版本）")
            print("3. 检查微信是否正常运行（能收发消息）")
        elif "仅支持Windows系统" in error_message:
            print("\n🔧 解决方案:")
            print("1. WeChatHook仅支持Windows操作系统")
            print("2. 请在Windows环境中运行此程序")
        elif "start-wechat.exe" in error_message or "wxhook.dll" in error_message:
            print("\n🔧 解决方案:")
            print("1. 检查wxhook/tools/目录下的文件是否完整")
            print("2. 重新下载完整的程序包")
            print("3. 检查杀毒软件是否误删了文件")
            print("4. 尝试以管理员权限运行")
        elif "OpenAI API Key" in error_message:
            print("\n🔧 解决方案:")
            print("1. 编辑配置文件设置OpenAI API Key")
            print("2. 配置文件路径: ./wechat_summary_bot/config/bot_config.json")
        else:
            print("\n🔧 通用解决方案:")
            print("1. 检查微信PC版是否正常启动")
            print("2. 尝试以管理员权限运行程序")
            print("3. 检查防火墙和杀毒软件设置")
            print("4. 重新下载完整程序包")
        
        print(f"\n📋 详细错误信息:")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 微信群聊总结机器人启动程序")
    print("=" * 60)
    
    # 环境检查
    if not check_environment():
        print("\n❌ 环境检查未通过，请解决上述问题后重试")
        sys.exit(1)
    
    # 配置检查
    if not check_configuration():
        print("\n⚠️ 请完成配置后重新运行此脚本")
        sys.exit(1)
    
    print("\n✅ 所有检查通过，准备启动机器人...")
    print("\n📋 注意事项:")
    print("   1. 请确保微信PC版已启动")
    print("   2. 建议使用微信3.9.5.81版本")
    print("   3. 机器人启动后会自动注入微信")
    print("   4. 按 Ctrl+C 可安全停止机器人")
    
    input("\n按回车键继续启动...")
    
    # 启动机器人
    success = start_bot()
    
    if success:
        print("\n✅ 机器人已正常退出")
    else:
        print("\n❌ 机器人异常退出")
        sys.exit(1)


if __name__ == "__main__":
    main()