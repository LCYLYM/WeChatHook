"""
WeChat Group Chat Summary Bot

A comprehensive bot for monitoring, analyzing and summarizing WeChat group chats.
Features include real-time message monitoring, AI-powered analysis, and scheduled summaries.
"""

__version__ = "1.0.0"
__author__ = "WeChat Summary Bot Team"

from .models.data_models import Message, RealtimeAlert, KeywordConfig, UrgencyAnalysisResult, DailySummary
from .core.database import DatabaseManager
from .core.message_collector import MessageCollector
from .core.deduplication import DeduplicationEngine
from .core.realtime_alerts import RealtimeAlertEngine
from .core.ai_service import AIAnalysisService

__all__ = [
    'Message',
    'RealtimeAlert', 
    'KeywordConfig',
    'UrgencyAnalysisResult',
    'DailySummary',
    'DatabaseManager',
    'MessageCollector',
    'DeduplicationEngine',
    'RealtimeAlertEngine',
    'AIAnalysisService'
]