"""
去重处理引擎 - 基于SQLite实现高效消息去重
"""
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from ..models.data_models import Message

logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """消息去重引擎"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_dedup_table()
    
    def init_dedup_table(self):
        """初始化去重表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_dedup (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    first_message_id TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dedup_hash ON message_dedup(content_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dedup_last_seen ON message_dedup(last_seen)")
            conn.commit()
            logger.debug("去重表初始化完成")
    
    def calculate_content_hash(self, message: Message) -> str:
        """计算消息内容hash"""
        # 合并所有文本内容
        content_parts = [message.content]
        if message.extracted_text and message.extracted_text not in [
            "[图片OCR失败]", "[语音获取失败]", "[图片处理异常]", "[语音处理异常]"
        ]:
            content_parts.append(message.extracted_text)
        
        combined_content = " ".join(content_parts).strip()
        return hashlib.md5(combined_content.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, message: Message) -> bool:
        """检查是否为重复消息"""
        if not message.content.strip():
            return False  # 空消息不进行去重
        
        content_hash = self.calculate_content_hash(message)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 检查24小时内是否有相同hash的消息
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                cursor = conn.execute("""
                    SELECT id, occurrence_count FROM message_dedup 
                    WHERE content_hash = ? AND last_seen > ?
                """, (content_hash, cutoff_time))
                
                result = cursor.fetchone()
                
                if result:
                    # 更新计数和时间
                    conn.execute("""
                        UPDATE message_dedup 
                        SET occurrence_count = occurrence_count + 1, 
                            last_seen = CURRENT_TIMESTAMP
                        WHERE content_hash = ?
                    """, (content_hash,))
                    conn.commit()
                    
                    logger.debug(f"检测到重复消息 (hash: {content_hash[:8]}...): {message.content[:50]}...")
                    return True
                else:
                    # 新消息，插入记录
                    conn.execute("""
                        INSERT INTO message_dedup (content_hash, first_message_id, last_seen)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (content_hash, message.message_id))
                    conn.commit()
                    return False
                    
        except Exception as e:
            logger.error(f"去重检查失败: {e}")
            return False  # 出错时不过滤消息
    
    def get_duplicate_stats(self) -> dict:
        """获取去重统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 总去重记录数
                cursor = conn.execute("SELECT COUNT(*) FROM message_dedup")
                total_records = cursor.fetchone()[0]
                
                # 24小时内的去重记录数
                cutoff_time = datetime.now() - timedelta(hours=24)
                cursor = conn.execute("SELECT COUNT(*) FROM message_dedup WHERE last_seen > ?", (cutoff_time,))
                recent_records = cursor.fetchone()[0]
                
                # 总重复次数
                cursor = conn.execute("SELECT SUM(occurrence_count) FROM message_dedup")
                total_occurrences = cursor.fetchone()[0] or 0
                
                # 平均重复率
                cursor = conn.execute("SELECT AVG(CAST(occurrence_count AS FLOAT)) FROM message_dedup")
                avg_duplicates = cursor.fetchone()[0] or 0
                
                return {
                    'total_records': total_records,
                    'recent_records': recent_records,
                    'total_occurrences': total_occurrences,
                    'average_duplicates': round(avg_duplicates, 2),
                    'duplicate_rate': round((total_occurrences - total_records) / max(total_occurrences, 1), 2)
                }
        except Exception as e:
            logger.error(f"获取去重统计失败: {e}")
            return {}
    
    def cleanup_old_records(self):
        """清理过期的去重记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cutoff_time = datetime.now() - timedelta(days=7)  # 保留7天
                cursor = conn.execute("DELETE FROM message_dedup WHERE last_seen < ?", (cutoff_time,))
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"清理了{deleted}条过期去重记录")
        except Exception as e:
            logger.error(f"清理去重记录失败: {e}")
    
    def force_add_duplicate(self, message: Message) -> bool:
        """强制添加到去重表（用于测试或特殊情况）"""
        try:
            content_hash = self.calculate_content_hash(message)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO message_dedup (content_hash, first_message_id, last_seen)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (content_hash, message.message_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"强制添加去重记录失败: {e}")
            return False