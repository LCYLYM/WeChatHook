"""
数据库管理器 - 负责SQLite数据库操作和消息存储
"""
import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..models.data_models import Message, RealtimeAlert, DailySummary, KeywordConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "./data/wechat_bot.db"):
        self.db_path = db_path
        # 只有非内存数据库才需要创建目录
        if db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir:  # 确保目录不为空
                os.makedirs(db_dir, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 消息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    extracted_text TEXT,
                    content_hash TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    is_important BOOLEAN DEFAULT FALSE,
                    value_score INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 群聊信息表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    chat_name TEXT NOT NULL,
                    chat_type TEXT DEFAULT 'group',
                    is_active BOOLEAN DEFAULT TRUE,
                    priority INTEGER DEFAULT 0,
                    last_message_time DATETIME,
                    total_messages INTEGER DEFAULT 0,
                    last_summary_date TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 每日总结表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT NOT NULL,
                    summary_content TEXT NOT NULL,
                    key_topics TEXT,
                    important_events TEXT,
                    action_items TEXT,
                    message_count INTEGER NOT NULL,
                    high_value_count INTEGER DEFAULT 0,
                    source_message_ids TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, chat_id)
                )
            """)
            
            # 实时推送记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_message_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    chat_name TEXT NOT NULL,
                    alert_content TEXT NOT NULL,
                    trigger_keywords TEXT,
                    context_message_ids TEXT,
                    urgency_score INTEGER,
                    push_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 关键词配置表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    weight FLOAT DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 系统配置表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)",
                "CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp ON messages(chat_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_messages_content_hash ON messages(content_hash)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_date ON daily_summaries(date)",
                "CREATE INDEX IF NOT EXISTS idx_summaries_chat_date ON daily_summaries(chat_id, date)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_push_time ON realtime_alerts(push_time)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            # 插入默认关键词
            default_keywords = [
                ('紧急', 'urgent', 2.0),
                ('急', 'urgent', 1.8),
                ('重要', 'urgent', 1.5),
                ('deadline', 'urgent', 2.0),
                ('截止', 'urgent', 2.0),
                ('会议取消', 'urgent', 1.8),
                ('故障', 'urgent', 1.8),
                ('出事了', 'urgent', 2.0),
                ('求助', 'urgent', 1.6),
                ('@所有人', 'work', 1.5),
                ('通知', 'work', 1.2),
                ('会议', 'work', 1.0),
                ('任务', 'work', 1.0),
                ('项目', 'work', 0.8)
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO alert_keywords (keyword, category, weight) 
                VALUES (?, ?, ?)
            """, default_keywords)
            
            # 插入默认系统配置
            default_configs = [
                ('target_user', '', '接收推送的用户微信ID'),
                ('daily_summary_time', '20:00', '每日总结生成时间'),
                ('urgency_threshold', '6', '实时推送的紧急度阈值'),
                ('max_context_messages', '10', '上下文消息最大数量'),
                ('data_retention_days', '180', '数据保留天数')
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO system_config (config_key, config_value, description) 
                VALUES (?, ?, ?)
            """, default_configs)
            
            conn.commit()
            logger.info("数据库初始化完成")
    
    def save_message(self, message: Message) -> bool:
        """保存消息到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO messages 
                    (message_id, chat_id, chat_name, sender_id, sender_name, 
                     message_type, content, extracted_text, content_hash, timestamp,
                     is_important, value_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.message_id, message.chat_id, message.chat_name,
                    message.sender_id, message.sender_name, message.message_type,
                    message.content, message.extracted_text, message.content_hash,
                    message.timestamp, message.is_important, message.value_score
                ))
                
                # 更新群聊信息
                self._update_chat_info(conn, message.chat_id, message.chat_name, message.timestamp)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False
    
    def _update_chat_info(self, conn: sqlite3.Connection, chat_id: str, chat_name: str, last_message_time: datetime):
        """更新群聊信息"""
        conn.execute("""
            INSERT OR REPLACE INTO chats 
            (chat_id, chat_name, last_message_time, total_messages, updated_at)
            VALUES (
                ?, ?, ?, 
                COALESCE((SELECT total_messages FROM chats WHERE chat_id = ?), 0) + 1,
                CURRENT_TIMESTAMP
            )
        """, (chat_id, chat_name, last_message_time, chat_id))
    
    def get_messages_by_date_range(self, chat_id: str, start_date: datetime, 
                                   end_date: datetime, limit: Optional[int] = None) -> List[Message]:
        """根据日期范围获取消息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                sql = """
                    SELECT message_id, chat_id, chat_name, sender_id, sender_name,
                           message_type, content, extracted_text, content_hash, timestamp,
                           is_important, value_score
                    FROM messages 
                    WHERE chat_id = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                """
                params = [chat_id, start_date, end_date]
                
                if limit:
                    sql += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(sql, params)
                messages = []
                for row in cursor.fetchall():
                    message = Message(
                        message_id=row[0], chat_id=row[1], chat_name=row[2],
                        sender_id=row[3], sender_name=row[4], message_type=row[5],
                        content=row[6], extracted_text=row[7] or "", 
                        timestamp=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9],
                        is_important=bool(row[10]), value_score=row[11]
                    )
                    message.content_hash = row[8]
                    messages.append(message)
                return messages
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    def get_active_keywords(self) -> List[KeywordConfig]:
        """获取活跃的关键词"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT keyword, category, weight FROM alert_keywords 
                    WHERE is_active = TRUE
                    ORDER BY weight DESC
                """)
                return [KeywordConfig(row[0], row[1], row[2]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取关键词失败: {e}")
            return []
    
    def save_realtime_alert(self, alert: RealtimeAlert) -> bool:
        """保存实时推送记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO realtime_alerts 
                    (trigger_message_id, chat_id, chat_name, alert_content, 
                     trigger_keywords, context_message_ids, urgency_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.trigger_message_id, alert.chat_id, alert.chat_name,
                    alert.alert_content, json.dumps(alert.trigger_keywords),
                    json.dumps(alert.context_message_ids), alert.urgency_score
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存推送记录失败: {e}")
            return False
    
    def save_daily_summary(self, summary: DailySummary) -> bool:
        """保存每日总结"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_summaries 
                    (date, chat_id, chat_name, summary_content, key_topics, 
                     important_events, action_items, message_count, high_value_count, source_message_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    summary.date, summary.chat_id, summary.chat_name, summary.summary_content,
                    json.dumps(summary.key_topics), json.dumps(summary.important_events),
                    json.dumps(summary.action_items), summary.message_count,
                    summary.high_value_count, json.dumps(summary.source_message_ids)
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"保存每日总结失败: {e}")
            return False
    
    def get_config(self, key: str, default: str = "") -> str:
        """获取系统配置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT config_value FROM system_config WHERE config_key = ?
                """, (key,))
                result = cursor.fetchone()
                return result[0] if result else default
        except Exception as e:
            logger.error(f"获取配置失败 {key}: {e}")
            return default
    
    def set_config(self, key: str, value: str, description: str = "") -> bool:
        """设置系统配置"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, value, description))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"设置配置失败 {key}: {e}")
            return False
    
    def get_active_chats(self) -> List[Dict[str, Any]]:
        """获取活跃的群聊列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT chat_id, chat_name, total_messages, last_message_time, last_summary_date
                    FROM chats 
                    WHERE is_active = TRUE
                    ORDER BY last_message_time DESC
                """)
                return [
                    {
                        'chat_id': row[0],
                        'chat_name': row[1], 
                        'total_messages': row[2],
                        'last_message_time': row[3],
                        'last_summary_date': row[4]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取活跃群聊失败: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 180):
        """清理过期数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                # 清理过期消息
                cursor = conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_date,))
                deleted_messages = cursor.rowcount
                
                # 清理过期推送记录
                cursor = conn.execute("DELETE FROM realtime_alerts WHERE push_time < ?", (cutoff_date,))
                deleted_alerts = cursor.rowcount
                
                # 清理过期总结（保留更长时间）
                summary_cutoff = datetime.now() - timedelta(days=retention_days * 2)
                cursor = conn.execute("DELETE FROM daily_summaries WHERE created_at < ?", (summary_cutoff,))
                deleted_summaries = cursor.rowcount
                
                conn.commit()
                logger.info(f"数据清理完成: 消息{deleted_messages}条, 推送{deleted_alerts}条, 总结{deleted_summaries}条")
                
        except Exception as e:
            logger.error(f"数据清理失败: {e}")