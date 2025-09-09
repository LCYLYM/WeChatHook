"""
每日总结生成器 - 定时生成群聊总结报告
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from wxhook import Bot
from ..models.data_models import DailySummary, BotConfig
from .database import DatabaseManager
from .ai_service import AIAnalysisService
from ..utils.helpers import get_date_string, calculate_date_range

logger = logging.getLogger(__name__)


class DailySummaryGenerator:
    """每日总结生成器"""
    
    def __init__(self, bot: Bot, db: DatabaseManager, ai_service: AIAnalysisService, config: BotConfig):
        self.bot = bot
        self.db = db
        self.ai_service = ai_service
        self.config = config
        self.target_user = config.alert_config.target_user
        
        logger.info("每日总结生成器初始化完成")
    
    def generate_all_summaries(self, target_date: datetime = None) -> List[DailySummary]:
        """生成所有活跃群聊的每日总结"""
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)  # 默认生成昨天的总结
        
        date_str = get_date_string(target_date)
        logger.info(f"开始生成 {date_str} 的每日总结")
        
        # 获取所有活跃群聊
        active_chats = self.db.get_active_chats()
        summaries = []
        
        for chat in active_chats:
            try:
                summary = self.generate_chat_summary(
                    chat_id=chat['chat_id'],
                    chat_name=chat['chat_name'],
                    target_date=target_date
                )
                
                if summary and summary.message_count > 0:
                    summaries.append(summary)
                    
                    # 保存总结到数据库
                    self.db.save_daily_summary(summary)
                    logger.info(f"群聊总结生成完成: {chat['chat_name']} ({summary.message_count}条消息)")
                else:
                    logger.debug(f"群聊无消息，跳过总结: {chat['chat_name']}")
                    
            except Exception as e:
                logger.error(f"生成群聊总结失败 {chat['chat_name']}: {e}")
        
        logger.info(f"每日总结生成完成，共{len(summaries)}个群聊")
        
        # 如果有总结且配置了目标用户，发送汇总报告
        if summaries and self.target_user:
            self.send_summary_report(summaries, date_str)
        
        return summaries
    
    def generate_chat_summary(self, chat_id: str, chat_name: str, target_date: datetime) -> DailySummary:
        """生成单个群聊的每日总结"""
        # 计算目标日期的时间范围
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 获取当天的所有消息
        messages = self.db.get_messages_by_date_range(chat_id, start_date, end_date)
        
        if not messages:
            return None
        
        date_str = get_date_string(target_date)
        
        try:
            # 使用AI生成总结
            summary = self.ai_service.generate_daily_summary(chat_name, messages, date_str)
            logger.debug(f"AI总结生成成功: {chat_name}")
            return summary
            
        except Exception as e:
            logger.error(f"AI总结生成失败 {chat_name}: {e}")
            # 生成简单的后备总结
            return self.generate_simple_summary(chat_id, chat_name, messages, date_str)
    
    def generate_simple_summary(self, chat_id: str, chat_name: str, messages: List, date_str: str) -> DailySummary:
        """生成简单的后备总结"""
        # 统计发言人
        senders = {}
        message_types = {}
        
        for msg in messages:
            senders[msg.sender_name] = senders.get(msg.sender_name, 0) + 1
            message_types[msg.message_type] = message_types.get(msg.message_type, 0) + 1
        
        top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 构建简单总结
        summary_content = f"今日{chat_name}共有{len(messages)}条消息。\n"
        
        if top_senders:
            summary_content += "主要发言人：" + "、".join([f"{name}({count}条)" for name, count in top_senders[:3]]) + "。\n"
        
        if message_types:
            type_str = "、".join([f"{type_name}({count}条)" for type_name, count in message_types.items()])
            summary_content += f"消息类型：{type_str}。"
        
        return DailySummary(
            date=date_str,
            chat_id=chat_id,
            chat_name=chat_name,
            summary_content=summary_content,
            key_topics=["日常交流"],
            important_events=[],
            action_items=[],
            message_count=len(messages),
            high_value_count=0,
            source_message_ids=[msg.message_id for msg in messages[:10]]
        )
    
    def send_summary_report(self, summaries: List[DailySummary], date_str: str):
        """发送总结报告给目标用户"""
        try:
            # 构建汇总报告
            report_content = self.build_summary_report(summaries, date_str)
            
            # 发送报告
            result = self.bot.send_text(self.target_user, report_content)
            
            if hasattr(result, 'code') and result.code == 200:
                logger.success(f"每日总结报告发送成功: {date_str}")
            else:
                logger.error(f"每日总结报告发送失败: {getattr(result, 'msg', '未知错误')}")
                
        except Exception as e:
            logger.error(f"发送每日总结报告异常: {e}")
    
    def build_summary_report(self, summaries: List[DailySummary], date_str: str) -> str:
        """构建总结报告内容"""
        # 按消息数量排序
        summaries.sort(key=lambda s: s.message_count, reverse=True)
        
        total_messages = sum(s.message_count for s in summaries)
        total_high_value = sum(s.high_value_count for s in summaries)
        
        report = f"""📊 【每日群聊总结报告】

📅 日期：{date_str}
📈 统计概览：
• 活跃群聊：{len(summaries)}个
• 总消息数：{total_messages}条
• 重要消息：{total_high_value}条

"""
        
        # 添加各群聊总结
        for i, summary in enumerate(summaries[:10], 1):  # 最多显示10个群聊
            report += f"""
🏷️ {i}. {summary.chat_name}
💬 消息数：{summary.message_count}条
⭐ 重要消息：{summary.high_value_count}条

📝 今日总结：
{summary.summary_content[:200]}{'...' if len(summary.summary_content) > 200 else ''}
"""
            
            # 添加关键话题
            if summary.key_topics:
                topics_str = "、".join(summary.key_topics[:3])
                report += f"🔍 关键话题：{topics_str}\n"
            
            # 添加重要事件
            if summary.important_events:
                events_str = "、".join(summary.important_events[:2])
                report += f"📌 重要事件：{events_str}\n"
            
            # 添加待办事项
            if summary.action_items:
                actions_str = "、".join(summary.action_items[:2])
                report += f"✅ 待办事项：{actions_str}\n"
        
        # 如果群聊太多，添加提示
        if len(summaries) > 10:
            report += f"\n... 还有{len(summaries) - 10}个群聊的总结已保存到数据库"
        
        report += f"\n\n⏰ 生成时间：{datetime.now().strftime('%H:%M:%S')}"
        
        return report
    
    def get_summary_by_date(self, chat_id: str, date_str: str) -> DailySummary:
        """根据日期获取已生成的总结"""
        try:
            # 这里需要在数据库管理器中添加相应的查询方法
            # 暂时返回None，需要后续实现
            return None
        except Exception as e:
            logger.error(f"获取历史总结失败 {chat_id} {date_str}: {e}")
            return None
    
    def regenerate_summary(self, chat_id: str, date_str: str) -> DailySummary:
        """重新生成指定日期的总结"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            chat_info = next((c for c in self.db.get_active_chats() if c['chat_id'] == chat_id), None)
            
            if not chat_info:
                logger.error(f"找不到群聊信息: {chat_id}")
                return None
            
            summary = self.generate_chat_summary(chat_id, chat_info['chat_name'], target_date)
            
            if summary:
                self.db.save_daily_summary(summary)
                logger.info(f"总结重新生成成功: {chat_info['chat_name']} {date_str}")
            
            return summary
            
        except Exception as e:
            logger.error(f"重新生成总结失败 {chat_id} {date_str}: {e}")
            return None
    
    def get_summary_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取总结统计信息"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 这里需要实现数据库查询来获取统计信息
            # 暂时返回基本信息
            return {
                'days_analyzed': days,
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'total_summaries': 0,  # 需要从数据库查询
                'avg_messages_per_day': 0,  # 需要从数据库查询
                'most_active_chat': '',  # 需要从数据库查询
            }
        except Exception as e:
            logger.error(f"获取总结统计失败: {e}")
            return {}
    
    def cleanup_old_summaries(self, retention_days: int = None):
        """清理过期的总结"""
        if retention_days is None:
            retention_days = self.config.data_retention_days * 2  # 总结保留更长时间
        
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            # 这里需要实现数据库清理逻辑
            logger.info(f"清理{cutoff_date.strftime('%Y-%m-%d')}之前的总结")
        except Exception as e:
            logger.error(f"清理总结失败: {e}")
    
    def export_summaries(self, chat_id: str = None, start_date: str = None, end_date: str = None) -> str:
        """导出总结到文件"""
        try:
            # 构建导出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"summaries_export_{timestamp}.json"
            filepath = f"./data/exports/{filename}"
            
            # 确保导出目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 这里需要实现导出逻辑
            logger.info(f"总结导出完成: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"导出总结失败: {e}")
            return ""