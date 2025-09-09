"""
微信群聊总结机器人 - 主程序入口
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wxhook import Bot
from wechat_summary_bot.config.settings import ConfigManager, get_config
from wechat_summary_bot.core.database import DatabaseManager
from wechat_summary_bot.core.deduplication import DeduplicationEngine
from wechat_summary_bot.core.message_collector import MessageCollector
from wechat_summary_bot.core.realtime_alerts import RealtimeAlertEngine
from wechat_summary_bot.core.ai_service import AIAnalysisService
from wechat_summary_bot.core.daily_summary import DailySummaryGenerator
from wechat_summary_bot.utils.helpers import (
    setup_logging, TaskScheduler, cleanup_temp_files,
    get_system_info, ensure_directory
)

logger = logging.getLogger(__name__)


class WeChatSummaryBot:
    """微信群聊总结机器人主类"""
    
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # 初始化组件
        self.bot = None
        self.db = None
        self.dedup_engine = None
        self.ai_service = None
        self.alert_engine = None
        self.message_collector = None
        self.summary_generator = None
        self.task_scheduler = None
        
        # 运行状态
        self.running = False
        self.scheduler_thread = None
        
        logger.info("微信群聊总结机器人初始化开始")
    
    def initialize(self):
        """初始化所有组件"""
        try:
            # 设置日志
            log_file = "./logs/wechat_bot.log" if self.config.log_level != "DEBUG" else None
            setup_logging(self.config.log_level, log_file)
            
            # 验证配置
            config_issues = self.config_manager.validate_config()
            if config_issues:
                logger.warning(f"配置验证发现问题: {config_issues}")
                # 如果有严重问题，提前退出
                if 'ai_api_key' in config_issues:
                    logger.error("OpenAI API Key未配置，AI功能将不可用")
            
            # 确保必要目录存在
            ensure_directory("./data")
            ensure_directory("./logs") 
            ensure_directory("./temp")
            
            # 初始化数据库
            self.db = DatabaseManager(self.config.database_path)
            logger.info("数据库管理器初始化完成")
            
            # 初始化去重引擎
            self.dedup_engine = DeduplicationEngine(self.config.database_path)
            logger.info("去重引擎初始化完成")
            
            # 初始化AI服务
            try:
                self.ai_service = AIAnalysisService(self.config.ai_config)
                logger.info("AI分析服务初始化完成")
            except Exception as e:
                logger.error(f"AI服务初始化失败: {e}")
                self.ai_service = None
            
            # 初始化微信机器人
            if self.test_mode:
                logger.info("测试模式：跳过微信机器人初始化")
                self.bot = None
            else:
                try:
                    self.bot = Bot(
                        on_login=self.on_login,
                        on_start=self.on_start,
                        on_stop=self.on_stop
                    )
                    logger.info("微信机器人初始化完成")
                except Exception as e:
                    logger.error(f"微信机器人初始化失败: {e}")
                    logger.error("可能原因:")
                    logger.error("  1. 微信PC版未启动或无法找到")
                    logger.error("  2. start-wechat.exe 或 wxhook.dll 文件损坏")
                    logger.error("  3. 运行环境不支持（仅支持Windows）")
                    logger.error("  4. 端口被占用")
                    raise Exception(f"微信机器人初始化失败: {e}")
            
            # 初始化实时推送引擎
            if self.ai_service and self.bot:
                self.alert_engine = RealtimeAlertEngine(
                    self.bot, self.db, self.ai_service, self.config.alert_config
                )
                logger.info("实时推送引擎初始化完成")
            else:
                if not self.ai_service:
                    logger.warning("AI服务不可用，实时推送功能已禁用")
                if not self.bot:
                    logger.warning("微信机器人不可用，实时推送功能已禁用")
            
            # 初始化消息收集器
            if self.bot:
                self.message_collector = MessageCollector(
                    self.bot, self.db, self.dedup_engine, self.alert_engine
                )
                logger.info("消息收集器初始化完成")
            else:
                logger.warning("微信机器人不可用，消息收集器未初始化")
            
            # 初始化每日总结生成器
            if self.ai_service:
                self.summary_generator = DailySummaryGenerator(
                    self.bot, self.db, self.ai_service, self.config
                )
                logger.info("每日总结生成器初始化完成")
            else:
                logger.warning("AI服务不可用，每日总结功能已禁用")
            
            # 初始化任务调度器
            self.task_scheduler = TaskScheduler()
            self.setup_scheduled_tasks()
            logger.info("任务调度器初始化完成")
            
            logger.info("所有组件初始化完成")
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"初始化失败: {e}")
            logger.error(f"详细错误信息:\n{traceback.format_exc()}")
            return False
    
    def setup_scheduled_tasks(self):
        """设置定时任务"""
        if not self.task_scheduler:
            return
        
        # 每日总结任务
        if self.summary_generator:
            self.task_scheduler.add_daily_job(
                self.generate_daily_summaries,
                self.config.daily_summary_time
            )
            logger.info(f"每日总结任务已设置: {self.config.daily_summary_time}")
        
        # 数据清理任务（每天凌晨2点）
        self.task_scheduler.add_daily_job(
            self.cleanup_data,
            "02:00"
        )
        
        # 去重记录清理任务
        self.task_scheduler.add_interval_job(
            self.dedup_engine.cleanup_old_records,
            self.config.cleanup_interval_hours
        )
        
        # 临时文件清理任务（每4小时）
        self.task_scheduler.add_interval_job(
            lambda: cleanup_temp_files("./temp", 4),
            4
        )
    
    def on_login(self, bot: Bot, event):
        """登录成功回调"""
        user_info = bot.get_self_info()
        logger.info(f"微信登录成功: {getattr(user_info, 'name', 'Unknown')}")
        
        # 发送启动通知
        if self.config.alert_config.target_user:
            try:
                startup_msg = f"""🤖 【微信总结机器人启动】

⏰ 启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 登录用户：{getattr(user_info, 'name', 'Unknown')}
💾 数据库：{self.config.database_path}
🔔 实时推送：{'启用' if self.config.alert_config.enable_realtime_alerts else '禁用'}
🤖 AI分析：{'启用' if self.ai_service else '禁用'}

✅ 机器人已就绪，开始监听群聊消息..."""

                bot.send_text(self.config.alert_config.target_user, startup_msg)
                logger.info("启动通知发送成功")
            except Exception as e:
                logger.warning(f"发送启动通知失败: {e}")
    
    def on_start(self, bot: Bot):
        """微信客户端启动回调"""
        logger.info("微信客户端启动完成")
        
        # 显示系统信息
        sys_info = get_system_info()
        logger.info(f"系统信息: {sys_info}")
    
    def on_stop(self, bot: Bot):
        """微信客户端停止回调"""
        logger.info("微信客户端正在关闭")
        self.shutdown()
    
    def generate_daily_summaries(self):
        """生成每日总结的定时任务"""
        try:
            if not self.summary_generator:
                logger.warning("每日总结生成器未初始化")
                return
            
            logger.info("开始执行每日总结任务")
            summaries = self.summary_generator.generate_all_summaries()
            logger.info(f"每日总结任务完成，生成了{len(summaries)}个总结")
            
        except Exception as e:
            logger.error(f"每日总结任务执行失败: {e}")
    
    def cleanup_data(self):
        """数据清理任务"""
        try:
            logger.info("开始执行数据清理任务")
            
            # 清理过期消息数据
            self.db.cleanup_old_data(self.config.data_retention_days)
            
            # 清理去重记录
            self.dedup_engine.cleanup_old_records()
            
            # 清理临时文件
            cleanup_temp_files("./temp", 24)
            
            logger.info("数据清理任务完成")
            
        except Exception as e:
            logger.error(f"数据清理任务失败: {e}")
    
    def start_scheduler(self):
        """启动任务调度器"""
        if self.task_scheduler and not self.scheduler_thread:
            self.scheduler_thread = threading.Thread(
                target=self.task_scheduler.start,
                daemon=True,
                name="TaskScheduler"
            )
            self.scheduler_thread.start()
            logger.info("任务调度器线程启动")
    
    def run(self):
        """运行机器人"""
        try:
            if not self.initialize():
                logger.error("初始化失败，程序退出")
                return False
            
            self.running = True
            
            # 启动任务调度器
            self.start_scheduler()
            
            # 启动微信机器人（阻塞运行）
            logger.info("启动微信机器人...")
            self.bot.run()
            
        except KeyboardInterrupt:
            logger.info("收到中断信号，准备关闭...")
            self.shutdown()
        except Exception as e:
            logger.error(f"运行异常: {e}")
            self.shutdown()
            return False
        
        return True
    
    def shutdown(self):
        """关闭机器人"""
        if not self.running:
            return
        
        logger.info("开始关闭微信总结机器人...")
        self.running = False
        
        try:
            # 停止任务调度器
            if self.task_scheduler:
                self.task_scheduler.stop()
                logger.info("任务调度器已停止")
            
            # 发送关闭通知
            if (self.bot and 
                self.config.alert_config.target_user and 
                self.config.alert_config.enable_realtime_alerts):
                
                shutdown_msg = f"""🤖 【微信总结机器人关闭】

⏰ 关闭时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 运行统计：{self.get_runtime_stats()}

👋 机器人已停止运行"""

                try:
                    self.bot.send_text(self.config.alert_config.target_user, shutdown_msg)
                except:
                    pass  # 关闭时忽略发送失败
            
            logger.info("微信总结机器人关闭完成")
            
        except Exception as e:
            logger.error(f"关闭过程中出现异常: {e}")
    
    def get_runtime_stats(self) -> str:
        """获取运行时统计信息"""
        try:
            stats = []
            
            if self.message_collector:
                collector_stats = self.message_collector.get_statistics()
                stats.append(f"处理消息{collector_stats.get('processed_messages', 0)}条")
                stats.append(f"过滤重复{collector_stats.get('filtered_messages', 0)}条")
            
            if self.dedup_engine:
                dedup_stats = self.dedup_engine.get_duplicate_stats()
                if dedup_stats:
                    stats.append(f"去重率{dedup_stats.get('duplicate_rate', 0)*100:.1f}%")
            
            return "、".join(stats) if stats else "暂无统计数据"
            
        except Exception as e:
            logger.error(f"获取运行统计失败: {e}")
            return "统计获取失败"
    
    def test_functionality(self):
        """测试机器人功能"""
        logger.info("开始功能测试...")
        
        # 测试AI服务
        if self.ai_service:
            logger.info("✅ AI服务可用")
        else:
            logger.warning("❌ AI服务不可用")
        
        # 测试数据库
        try:
            active_chats = self.db.get_active_chats()
            logger.info(f"✅ 数据库连接正常，发现{len(active_chats)}个活跃群聊")
        except Exception as e:
            logger.error(f"❌ 数据库测试失败: {e}")
        
        # 测试实时推送
        if self.alert_engine and self.config.alert_config.target_user:
            try:
                success = self.alert_engine.send_test_alert("功能测试消息")
                if success:
                    logger.info("✅ 实时推送测试成功")
                else:
                    logger.warning("❌ 实时推送测试失败")
            except Exception as e:
                logger.error(f"❌ 实时推送测试异常: {e}")
        else:
            logger.warning("❌ 实时推送未配置或不可用")
        
        logger.info("功能测试完成")


def main():
    """主函数"""
    print("微信群聊总结机器人启动中...")
    
    try:
        # 创建并运行机器人
        bot = WeChatSummaryBot()
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "test":
                # 测试模式
                if bot.initialize():
                    bot.test_functionality()
                return
            
            elif command == "config":
                # 配置管理
                print("创建配置模板...")
                template_file = bot.config_manager.create_config_template()
                if template_file:
                    print(f"配置模板创建成功: {template_file}")
                    print("请编辑配置文件后重新启动机器人")
                return
            
            elif command == "summary":
                # 手动生成总结
                if bot.initialize() and bot.summary_generator:
                    print("开始生成昨日总结...")
                    summaries = bot.summary_generator.generate_all_summaries()
                    print(f"总结生成完成，共{len(summaries)}个群聊")
                return
        
        # 正常运行模式
        success = bot.run()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()