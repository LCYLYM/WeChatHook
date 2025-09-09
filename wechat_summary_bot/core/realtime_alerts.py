"""
实时推送引擎 - 基于关键词触发和AI分析的消息推送系统
"""
import logging
from datetime import datetime, timedelta
from typing import List

from wxhook import Bot
from ..models.data_models import (
    Message, KeywordConfig, RealtimeAlert, AlertConfig, 
    UrgencyAnalysisResult
)
from .database import DatabaseManager
from .ai_service import AIAnalysisService

logger = logging.getLogger(__name__)


class RealtimeAlertEngine:
    """实时推送引擎"""
    
    def __init__(self, bot: Bot, db: DatabaseManager, ai_service: AIAnalysisService, config: AlertConfig):
        self.bot = bot
        self.db = db
        self.ai_service = ai_service
        self.config = config
        self.target_user = config.target_user
        
        # 缓存关键词以提高性能
        self._keywords_cache = None
        self._last_keyword_update = None
        
        logger.info(f"实时推送引擎初始化完成, 目标用户: {self.target_user}")
    
    def check_and_process(self, message: Message):
        """检查消息是否需要实时推送"""
        if not self.config.enable_realtime_alerts or not self.target_user:
            return
        
        # 第一阶段：关键词快速筛选
        triggered_keywords = self.check_urgent_keywords(message)
        
        if triggered_keywords:
            logger.info(f"关键词触发: {[k.keyword for k in triggered_keywords]} - {message.chat_name}")
            # 第二阶段：AI分析
            self.process_potential_alert(message, triggered_keywords)
    
    def check_urgent_keywords(self, message: Message) -> List[KeywordConfig]:
        """检查是否包含紧急关键词"""
        keywords = self._get_keywords()
        content = message.content + (message.extracted_text or "")
        
        triggered_keywords = []
        for keyword in keywords:
            if keyword.keyword in content:
                triggered_keywords.append(keyword)
                logger.debug(f"关键词匹配: '{keyword.keyword}' in {message.chat_name}")
        
        return triggered_keywords
    
    def _get_keywords(self) -> List[KeywordConfig]:
        """获取关键词（带缓存）"""
        now = datetime.now()
        
        # 缓存5分钟
        if (self._keywords_cache is None or 
            self._last_keyword_update is None or 
            now - self._last_keyword_update > timedelta(minutes=5)):
            
            self._keywords_cache = self.db.get_active_keywords()
            self._last_keyword_update = now
            logger.debug(f"关键词缓存更新: {len(self._keywords_cache)}个关键词")
        
        return self._keywords_cache
    
    def process_potential_alert(self, trigger_message: Message, triggered_keywords: List[KeywordConfig]):
        """处理潜在的紧急消息"""
        try:
            # 获取当天该群的前N条消息作为上下文
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            context_messages = self.db.get_messages_by_date_range(
                chat_id=trigger_message.chat_id,
                start_date=today_start,
                end_date=trigger_message.timestamp,
                limit=self.config.max_context_messages
            )
            
            # AI分析
            analysis_result = self.ai_service.analyze_urgency(
                trigger_message, context_messages, triggered_keywords
            )
            
            logger.info(f"AI分析完成: 紧急度{analysis_result.urgency_score}/10, "
                       f"推送类型={analysis_result.push_type}")
            
            if analysis_result.is_urgent and analysis_result.urgency_score >= self.config.urgency_threshold:
                # 执行推送
                success = self.execute_push(trigger_message, context_messages, analysis_result)
                
                if success:
                    # 记录推送历史
                    alert = RealtimeAlert(
                        trigger_message_id=trigger_message.message_id,
                        chat_id=trigger_message.chat_id,
                        chat_name=trigger_message.chat_name,
                        alert_content=analysis_result.summary,
                        trigger_keywords=[k.keyword for k in triggered_keywords],
                        context_message_ids=analysis_result.push_message_ids,
                        urgency_score=analysis_result.urgency_score
                    )
                    self.db.save_realtime_alert(alert)
                    logger.info(f"实时推送完成并记录: {trigger_message.chat_name}")
            else:
                logger.debug(f"消息未达到推送阈值: 紧急度{analysis_result.urgency_score} < {self.config.urgency_threshold}")
                
        except Exception as e:
            logger.error(f"处理潜在推送消息失败: {e}")
    
    def execute_push(self, trigger_msg: Message, context_msgs: List[Message], 
                    ai_result: UrgencyAnalysisResult) -> bool:
        """执行推送（直接发送给目标用户）"""
        
        try:
            # 构建推送内容
            push_content = self.build_push_content(trigger_msg, context_msgs, ai_result)
            
            # 使用WeChatHook API发送消息
            result = self.bot.send_text(self.target_user, push_content)
            
            if hasattr(result, 'code') and result.code == 200:
                logger.info(f"实时推送成功: {trigger_msg.chat_name} - {trigger_msg.sender_name}")
                return True
            else:
                error_msg = getattr(result, 'msg', '未知错误')
                logger.error(f"实时推送失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"实时推送异常: {e}")
            return False
    
    def build_push_content(self, trigger_msg: Message, context_msgs: List[Message], 
                          ai_result: UrgencyAnalysisResult) -> str:
        """构建推送内容"""
        # 根据紧急度选择表情符号
        if ai_result.urgency_score >= 9:
            emoji = "🚨🔥"
        elif ai_result.urgency_score >= 7:
            emoji = "⚠️🔔"
        else:
            emoji = "💡📢"
        
        push_content = f"""{emoji} 【重要消息提醒】

📱 群聊：{trigger_msg.chat_name}
👤 发送人：{trigger_msg.sender_name}
⏰ 时间：{trigger_msg.timestamp.strftime('%H:%M:%S')}
🎯 紧急度：{ai_result.urgency_score}/10

💡 AI分析：{ai_result.summary}

📝 触发消息：
{trigger_msg.content}"""

        # 添加提取的内容
        if (trigger_msg.extracted_text and 
            trigger_msg.extracted_text not in ["[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"]):
            push_content += f"\n🔍 提取内容：{trigger_msg.extracted_text}"
        
        # 根据AI判断添加上下文
        if ai_result.push_type == "context" and len(ai_result.push_message_ids) > 1:
            push_content += "\n\n📋 相关上下文："
            
            context_count = 0
            for msg_id in ai_result.push_message_ids:
                if msg_id != trigger_msg.message_id and context_count < 3:  # 最多显示3条上下文
                    context_msg = next((m for m in context_msgs if m.message_id == msg_id), None)
                    if context_msg:
                        content_preview = (context_msg.content[:50] + "...") if len(context_msg.content) > 50 else context_msg.content
                        push_content += f"\n• {context_msg.sender_name}：{content_preview}"
                        context_count += 1
        
        # 添加关键因素
        if ai_result.key_factors:
            push_content += f"\n\n🔑 关键因素：{', '.join(ai_result.key_factors[:3])}"  # 最多显示3个因素
        
        return push_content
    
    def send_test_alert(self, test_message: str = "这是一条测试推送消息") -> bool:
        """发送测试推送"""
        try:
            test_content = f"""🧪 【测试推送】

⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📝 内容：{test_message}

✅ 如果您收到此消息，说明实时推送功能正常工作。"""

            result = self.bot.send_text(self.target_user, test_content)
            
            if hasattr(result, 'code') and result.code == 200:
                logger.info("测试推送发送成功")
                return True
            else:
                logger.error(f"测试推送发送失败: {getattr(result, 'msg', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"发送测试推送异常: {e}")
            return False
    
    def update_target_user(self, new_target: str) -> bool:
        """更新目标用户"""
        try:
            old_target = self.target_user
            self.target_user = new_target
            self.config.target_user = new_target
            
            # 更新数据库配置
            success = self.db.set_config('target_user', new_target, '接收推送的用户微信ID')
            
            if success:
                logger.info(f"推送目标用户已更新: {old_target} -> {new_target}")
                return True
            else:
                # 回滚
                self.target_user = old_target
                self.config.target_user = old_target
                return False
                
        except Exception as e:
            logger.error(f"更新推送目标用户失败: {e}")
            return False
    
    def get_alert_statistics(self) -> dict:
        """获取推送统计信息"""
        try:
            # 这里需要在数据库中添加统计查询方法
            # 暂时返回基本统计
            return {
                'target_user': self.target_user,
                'urgency_threshold': self.config.urgency_threshold,
                'max_context_messages': self.config.max_context_messages,
                'keywords_count': len(self._get_keywords()),
                'enabled': self.config.enable_realtime_alerts
            }
        except Exception as e:
            logger.error(f"获取推送统计失败: {e}")
            return {}
    
    def disable_alerts_temporarily(self, duration_minutes: int = 60):
        """临时禁用推送"""
        # 这里可以添加临时禁用的逻辑
        # 例如设置一个时间窗口，在这个窗口内不发送推送
        logger.info(f"推送已临时禁用 {duration_minutes} 分钟")
        # TODO: 实现临时禁用逻辑