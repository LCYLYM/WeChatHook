"""
AI分析服务 - 集成OpenAI GPT-4进行消息分析和总结
"""
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from ..models.data_models import (
    Message, KeywordConfig, UrgencyAnalysisResult, 
    DailySummary, AIConfig
)

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """AI分析服务"""
    
    def __init__(self, config: AIConfig):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Please install with: pip install openai")
        
        self.client = openai.OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url
        )
        self.model = config.model
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        
        logger.info(f"AI服务初始化完成: {config.model}")
    
    def analyze_urgency(self, trigger_msg: Message, context_msgs: List[Message], 
                       keywords: List[KeywordConfig]) -> UrgencyAnalysisResult:
        """分析消息紧急程度"""
        
        system_prompt = """你是一个专业的信息优先级分析师，负责分析微信群聊消息的紧急程度。

你的任务是判断是否需要立即推送给用户，必须严格按照JSON格式返回结果。

评估标准：
1. 时效性：是否需要立即行动（会议通知、截止日期、紧急求助等）
2. 重要性：对用户工作/生活的影响程度
3. 行动性：是否需要用户立即回应或采取行动
4. 发送者权重：群主、重要联系人的消息优先级更高

紧急度评分（1-10分）：
- 9-10分：极紧急（立即行动的事件）
- 7-8分：高度紧急（今日内必须处理）
- 5-6分：中等紧急（需要关注但不紧急）
- 1-4分：低紧急或不紧急

推送类型：
- "single"：只推送触发消息
- "context"：推送触发消息和相关上下文
- "none"：不推送"""

        user_prompt = f"""请分析以下群聊消息是否需要立即推送：

【触发关键词】：{[k.keyword for k in keywords]}
【关键词权重】：{[f"{k.keyword}({k.weight})" for k in keywords]}

【群聊信息】：
- 群名：{trigger_msg.chat_name}
- 触发时间：{trigger_msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

【触发消息】：
- 发送人：{trigger_msg.sender_name}
- 消息类型：{trigger_msg.message_type}
- 内容：{trigger_msg.content}
{f"- 提取内容：{trigger_msg.extracted_text}" if trigger_msg.extracted_text and trigger_msg.extracted_text not in ["[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"] else ""}

【当天上下文消息】（前{len(context_msgs)}条）：
{self._format_context_messages(context_msgs)}

请严格按照以下JSON格式返回（不要添加任何其他文字）：
{{
    "is_urgent": true/false,
    "urgency_score": 1-10的整数,
    "push_type": "single/context/none",
    "push_message_ids": ["触发消息ID", "相关消息ID1", "相关消息ID2"],
    "summary": "简要说明分析结果和推送原因，控制在100字以内",
    "key_factors": ["影响因素1", "影响因素2", "影响因素3"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"AI分析原始结果: {result_text}")
            
            # 解析JSON结果
            try:
                result_data = json.loads(result_text)
                return UrgencyAnalysisResult(
                    is_urgent=result_data.get("is_urgent", False),
                    urgency_score=int(result_data.get("urgency_score", 1)),
                    push_type=result_data.get("push_type", "none"),
                    push_message_ids=result_data.get("push_message_ids", [trigger_msg.message_id]),
                    summary=result_data.get("summary", "AI分析完成"),
                    key_factors=result_data.get("key_factors", [])
                )
            except json.JSONDecodeError as e:
                logger.error(f"AI返回结果JSON解析失败: {e}, 原始内容: {result_text}")
                # 返回默认的低紧急度结果
                return UrgencyAnalysisResult(
                    is_urgent=False,
                    urgency_score=3,
                    push_type="none",
                    push_message_ids=[trigger_msg.message_id],
                    summary="AI分析失败，默认为低优先级",
                    key_factors=["AI解析错误"]
                )
                
        except Exception as e:
            logger.error(f"AI紧急度分析失败: {e}")
            # 基于关键词权重的简单评分作为后备方案
            keyword_score = sum(k.weight for k in keywords)
            is_urgent = keyword_score >= 3.0
            
            return UrgencyAnalysisResult(
                is_urgent=is_urgent,
                urgency_score=min(10, max(1, int(keyword_score * 2))),
                push_type="single" if is_urgent else "none",
                push_message_ids=[trigger_msg.message_id],
                summary=f"关键词触发 (权重:{keyword_score:.1f})",
                key_factors=[k.keyword for k in keywords]
            )
    
    def generate_daily_summary(self, chat_name: str, messages: List[Message], 
                             date: str) -> DailySummary:
        """生成每日总结"""
        
        if not messages:
            return DailySummary(
                date=date,
                chat_id="",
                chat_name=chat_name,
                summary_content="今日无消息",
                key_topics=[],
                important_events=[],
                action_items=[],
                message_count=0,
                high_value_count=0,
                source_message_ids=[]
            )
        
        system_prompt = """你是一个专业的群聊总结分析师，擅长从大量聊天记录中提取关键信息。

你的任务是生成高质量的群聊每日总结，包括：
1. 主要话题和讨论要点
2. 重要事件和决策
3. 待办事项和行动计划
4. 有价值的信息和资源

要求：
- 总结简洁明了，突出重点
- 按重要性排序内容
- 识别需要跟进的事项
- 过滤无意义的闲聊内容"""

        # 构建消息摘要
        message_summary = self._build_message_summary(messages)
        
        user_prompt = f"""请为以下群聊生成每日总结：

【群聊名称】：{chat_name}
【日期】：{date}
【消息总数】：{len(messages)}

【消息内容】：
{message_summary}

请严格按照以下JSON格式返回（不要添加任何其他文字）：
{{
    "summary_content": "今日群聊总结，控制在300字以内",
    "key_topics": ["主要话题1", "主要话题2", "主要话题3"],
    "important_events": ["重要事件1", "重要事件2"],
    "action_items": ["待办事项1", "待办事项2"],
    "high_value_message_ids": ["重要消息ID1", "重要消息ID2"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"AI总结原始结果: {result_text[:200]}...")
            
            # 解析JSON结果
            try:
                result_data = json.loads(result_text)
                
                # 计算高价值消息数量
                high_value_ids = result_data.get("high_value_message_ids", [])
                high_value_count = len([mid for mid in high_value_ids if any(m.message_id == mid for m in messages)])
                
                return DailySummary(
                    date=date,
                    chat_id=messages[0].chat_id,
                    chat_name=chat_name,
                    summary_content=result_data.get("summary_content", "AI生成总结失败"),
                    key_topics=result_data.get("key_topics", []),
                    important_events=result_data.get("important_events", []),
                    action_items=result_data.get("action_items", []),
                    message_count=len(messages),
                    high_value_count=high_value_count,
                    source_message_ids=[m.message_id for m in messages]
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"AI总结结果JSON解析失败: {e}")
                return self._generate_fallback_summary(chat_name, messages, date)
                
        except Exception as e:
            logger.error(f"AI每日总结生成失败: {e}")
            return self._generate_fallback_summary(chat_name, messages, date)
    
    def _format_context_messages(self, messages: List[Message]) -> str:
        """格式化上下文消息"""
        formatted = []
        for i, msg in enumerate(messages[-10:], 1):  # 只显示最后10条
            content = msg.content
            if msg.extracted_text and msg.extracted_text not in [
                "[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"
            ]:
                content += f" [提取内容:{msg.extracted_text}]"
            
            formatted.append(f"{i}. {msg.sender_name}({msg.timestamp.strftime('%H:%M')}): {content}")
        
        return "\n".join(formatted)
    
    def _build_message_summary(self, messages: List[Message]) -> str:
        """构建消息摘要"""
        # 按发送者分组统计
        sender_stats = {}
        content_parts = []
        
        for msg in messages:
            sender_stats[msg.sender_name] = sender_stats.get(msg.sender_name, 0) + 1
            
            # 构建内容摘要（只取前50个消息的详细内容）
            if len(content_parts) < 50:
                content = msg.content
                if msg.extracted_text and msg.extracted_text not in [
                    "[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"
                ]:
                    content += f" [提取内容:{msg.extracted_text[:100]}]"
                
                content_parts.append(f"[{msg.timestamp.strftime('%H:%M')}] {msg.sender_name}: {content[:200]}")
        
        # 构建统计信息
        stats_info = f"发言统计：{', '.join([f'{name}({count}条)' for name, count in sorted(sender_stats.items(), key=lambda x: x[1], reverse=True)])}"
        
        return f"{stats_info}\n\n详细内容：\n" + "\n".join(content_parts)
    
    def _generate_fallback_summary(self, chat_name: str, messages: List[Message], date: str) -> DailySummary:
        """生成后备总结（当AI失败时使用）"""
        # 简单的关键词提取
        all_content = " ".join([msg.content for msg in messages])
        
        # 统计发言人
        senders = {}
        for msg in messages:
            senders[msg.sender_name] = senders.get(msg.sender_name, 0) + 1
        
        top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary_content = f"今日{chat_name}共有{len(messages)}条消息。"
        if top_senders:
            summary_content += f"主要发言人：{', '.join([f'{name}({count}条)' for name, count in top_senders])}。"
        
        return DailySummary(
            date=date,
            chat_id=messages[0].chat_id,
            chat_name=chat_name,
            summary_content=summary_content,
            key_topics=["日常交流"],
            important_events=[],
            action_items=[],
            message_count=len(messages),
            high_value_count=0,
            source_message_ids=[m.message_id for m in messages[:10]]  # 只记录前10条
        )