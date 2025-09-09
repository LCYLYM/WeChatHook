"""
Data models for the WeChat Summary Bot
"""
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class Message:
    """消息数据模型"""
    message_id: str
    chat_id: str
    chat_name: str
    sender_id: str
    sender_name: str
    message_type: str  # 'text', 'image', 'voice', 'emoji', 'video'
    content: str
    timestamp: datetime
    extracted_text: str = ""  # OCR/语音转文字结果
    content_hash: str = field(default="", init=False)
    is_important: bool = False
    value_score: int = 0
    
    def __post_init__(self):
        """计算内容hash用于去重"""
        if not self.content_hash:
            content_parts = [self.content]
            if self.extracted_text and self.extracted_text not in [
                "[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"
            ]:
                content_parts.append(self.extracted_text)
            
            combined_content = " ".join(content_parts).strip()
            self.content_hash = hashlib.md5(combined_content.encode('utf-8')).hexdigest()


@dataclass
class KeywordConfig:
    """关键词配置"""
    keyword: str
    category: str  # 'urgent', 'work', 'personal'
    weight: float = 1.0
    is_active: bool = True


@dataclass
class UrgencyAnalysisResult:
    """AI紧急度分析结果"""
    is_urgent: bool
    urgency_score: int  # 1-10
    push_type: str  # 'single', 'context', 'none'
    push_message_ids: List[str]
    summary: str
    key_factors: List[str]


@dataclass
class RealtimeAlert:
    """实时推送记录"""
    trigger_message_id: str
    chat_id: str
    chat_name: str
    alert_content: str
    trigger_keywords: List[str]
    context_message_ids: List[str]
    urgency_score: int
    push_time: datetime = field(default_factory=datetime.now)


@dataclass
class DailySummary:
    """每日总结"""
    date: str  # YYYY-MM-DD
    chat_id: str
    chat_name: str
    summary_content: str
    key_topics: List[str]
    important_events: List[str]
    action_items: List[str]
    message_count: int
    high_value_count: int
    source_message_ids: List[str]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AlertConfig:
    """推送配置"""
    enable_realtime_alerts: bool = True
    urgency_threshold: int = 6
    max_context_messages: int = 10
    target_user: str = ""


@dataclass
class AIConfig:
    """AI配置"""
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.3


@dataclass
class BotConfig:
    """机器人配置"""
    database_path: str = "./data/wechat_bot.db"
    data_retention_days: int = 180
    daily_summary_time: str = "20:00"
    cleanup_interval_hours: int = 24
    log_level: str = "INFO"
    alert_config: AlertConfig = field(default_factory=AlertConfig)
    ai_config: AIConfig = field(default_factory=lambda: AIConfig(openai_api_key=""))