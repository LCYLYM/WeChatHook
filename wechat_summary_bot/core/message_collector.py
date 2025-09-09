"""
消息收集器 - 监听微信消息事件并处理多媒体内容
"""
import os
import time
import logging
from datetime import datetime
from typing import Optional

from wxhook import Bot, events
from wxhook.model import Event

from ..models.data_models import Message
from .database import DatabaseManager
from .deduplication import DeduplicationEngine
from .realtime_alerts import RealtimeAlertEngine

logger = logging.getLogger(__name__)


class MessageCollector:
    """消息收集器"""
    
    def __init__(self, bot: Bot, db: DatabaseManager, dedup_engine: DeduplicationEngine, 
                 alert_engine: RealtimeAlertEngine):
        self.bot = bot
        self.db = db
        self.dedup_engine = dedup_engine
        self.alert_engine = alert_engine
        
        # 统计信息
        self.stats = {
            'total_messages': 0,
            'filtered_messages': 0,
            'processed_messages': 0,
            'error_messages': 0
        }
        
        # 注册消息处理器
        self.setup_message_handlers()
        logger.info("消息收集器初始化完成")
        
    def setup_message_handlers(self):
        """设置消息处理器"""
        
        @self.bot.handle(events.TEXT_MESSAGE)
        def handle_text(bot: Bot, event: Event):
            """处理文本消息"""
            try:
                message = self.extract_message_info(event, "text")
                if message:
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理文本消息异常: {e}")
                self.stats['error_messages'] += 1
        
        @self.bot.handle(events.IMAGE_MESSAGE) 
        def handle_image(bot: Bot, event: Event):
            """处理图片消息"""
            try:
                message = self.extract_message_info(event, "image")
                if message:
                    # 处理图片OCR
                    self.process_image_ocr(message, event)
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理图片消息异常: {e}")
                self.stats['error_messages'] += 1
        
        @self.bot.handle(events.VOICE_MESSAGE)
        def handle_voice(bot: Bot, event: Event):
            """处理语音消息"""
            try:
                message = self.extract_message_info(event, "voice")
                if message:
                    # 处理语音转文字
                    self.process_voice_to_text(message, event)
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理语音消息异常: {e}")
                self.stats['error_messages'] += 1
        
        @self.bot.handle(events.EMOJI_MESSAGE)
        def handle_emoji(bot: Bot, event: Event):
            """处理表情消息"""
            try:
                message = self.extract_message_info(event, "emoji")
                if message:
                    message.content = "[表情包]"
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理表情消息异常: {e}")
                self.stats['error_messages'] += 1
        
        @self.bot.handle(events.VIDEO_MESSAGE)
        def handle_video(bot: Bot, event: Event):
            """处理视频消息"""
            try:
                message = self.extract_message_info(event, "video")
                if message:
                    message.content = "[视频消息]"
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理视频消息异常: {e}")
                self.stats['error_messages'] += 1
        
        @self.bot.handle(events.CARD_MESSAGE)
        def handle_card(bot: Bot, event: Event):
            """处理卡片消息"""
            try:
                message = self.extract_message_info(event, "card")
                if message:
                    message.content = "[卡片消息]"
                    self.process_message(message)
            except Exception as e:
                logger.error(f"处理卡片消息异常: {e}")
                self.stats['error_messages'] += 1
    
    def extract_message_info(self, event: Event, message_type: str) -> Optional[Message]:
        """从Event中提取消息信息"""
        try:
            # 增加消息计数
            self.stats['total_messages'] += 1
            
            # 判断是否为群聊消息
            is_group = event.fromUser and event.fromUser.endswith("@chatroom")
            
            # 跳过非群聊消息（根据需求可以调整）
            if not is_group:
                logger.debug("跳过非群聊消息")
                return None
            
            # 提取发送者信息和内容
            if event.content and isinstance(event.content, str):
                # 群聊消息格式：发送者ID:消息内容
                if ":" in event.content and is_group:
                    parts = event.content.split(":", 1)
                    if len(parts) == 2:
                        sender_id, content = parts
                        sender_name = self.get_sender_name(sender_id.strip(), event.fromUser)
                    else:
                        sender_id = "unknown"
                        sender_name = "系统消息"
                        content = str(event.content)
                else:
                    # 可能是系统消息或其他格式
                    sender_id = event.fromUser or "unknown"
                    sender_name = "系统消息"
                    content = str(event.content)
            else:
                # 处理非文本内容
                sender_id = "unknown"
                sender_name = "系统消息"
                content = f"[{message_type}消息]"
            
            # 获取群聊名称
            chat_name = self.get_chat_name(event.fromUser)
            
            # 创建消息对象
            message = Message(
                message_id=str(event.msgId) if event.msgId else str(int(time.time() * 1000)),
                chat_id=event.fromUser,
                chat_name=chat_name,
                sender_id=sender_id,
                sender_name=sender_name,
                message_type=message_type,
                content=content.strip(),
                timestamp=datetime.fromtimestamp(event.createTime) if event.createTime else datetime.now(),
                extracted_text=""
            )
            
            logger.debug(f"提取消息信息: {chat_name} - {sender_name} - {message_type}")
            return message
            
        except Exception as e:
            logger.error(f"提取消息信息失败: {e}")
            return None
    
    def process_image_ocr(self, message: Message, event: Event):
        """处理图片OCR"""
        try:
            # 尝试提取图片路径
            image_path = self.extract_image_path(event)
            
            if image_path and os.path.exists(image_path):
                logger.debug(f"开始OCR处理: {image_path}")
                ocr_result = self.bot.ocr(image_path)
                
                if hasattr(ocr_result, 'code') and ocr_result.code == 200:
                    if hasattr(ocr_result, 'data') and ocr_result.data:
                        ocr_text = ocr_result.data.get('ocrResult', '')
                        if ocr_text:
                            message.extracted_text = ocr_text
                            logger.debug(f"OCR成功: {ocr_text[:50]}...")
                        else:
                            message.extracted_text = "[图片无文字内容]"
                    else:
                        message.extracted_text = "[OCR无结果]"
                else:
                    error_msg = getattr(ocr_result, 'msg', '未知错误')
                    logger.warning(f"OCR失败: {error_msg}")
                    message.extracted_text = "[图片OCR失败]"
            else:
                logger.warning(f"图片路径无效: {image_path}")
                message.extracted_text = "[图片路径获取失败]"
                
        except Exception as e:
            logger.error(f"图片OCR处理异常: {e}")
            message.extracted_text = "[图片处理异常]"
    
    def process_voice_to_text(self, message: Message, event: Event):
        """处理语音转文字"""
        try:
            if not event.msgId:
                message.extracted_text = "[语音消息ID缺失]"
                return
            
            # 创建临时目录
            store_dir = "./temp/voice"
            os.makedirs(store_dir, exist_ok=True)
            
            logger.debug(f"开始获取语音文件: msgId={event.msgId}")
            voice_result = self.bot.get_voice_by_msg_id(event.msgId, store_dir)
            
            if hasattr(voice_result, 'code') and voice_result.code == 200:
                if hasattr(voice_result, 'data') and voice_result.data:
                    voice_file_path = voice_result.data.get('voicePath', '')
                    if voice_file_path and os.path.exists(voice_file_path):
                        # 这里可以添加语音转文字的逻辑
                        # 由于WeChatHook可能不直接支持语音转文字，我们先记录文件路径
                        message.extracted_text = f"[语音文件已保存: {os.path.basename(voice_file_path)}]"
                        logger.debug(f"语音文件获取成功: {voice_file_path}")
                    else:
                        message.extracted_text = "[语音文件路径无效]"
                else:
                    message.extracted_text = "[语音获取无数据]"
            else:
                error_msg = getattr(voice_result, 'msg', '未知错误')
                logger.warning(f"语音获取失败: {error_msg}")
                message.extracted_text = "[语音获取失败]"
                
        except Exception as e:
            logger.error(f"语音处理异常: {e}")
            message.extracted_text = "[语音处理异常]"
    
    def process_message(self, message: Message):
        """处理消息的核心逻辑"""
        try:
            # 1. 去重检查
            if self.dedup_engine.is_duplicate(message):
                logger.debug(f"重复消息已过滤: {message.content[:50]}")
                self.stats['filtered_messages'] += 1
                return
            
            # 2. 存储消息
            success = self.db.save_message(message)
            if not success:
                logger.error("消息存储失败")
                return
            
            logger.debug(f"消息已保存: {message.chat_name} - {message.sender_name}")
            self.stats['processed_messages'] += 1
            
            # 3. 实时推送检查
            if self.alert_engine:
                self.alert_engine.check_and_process(message)
                
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.stats['error_messages'] += 1
    
    def get_sender_name(self, wxid: str, room_id: str = None) -> str:
        """获取发送者昵称"""
        try:
            if room_id and room_id.endswith("@chatroom"):
                # 群聊中的用户，尝试获取群内昵称
                room_members = self.bot.get_room_members(room_id)
                if hasattr(room_members, 'data') and room_members.data:
                    member_info = room_members.data
                    # 解析群成员信息获取昵称
                    nickname = self.parse_member_nickname(wxid, member_info)
                    if nickname:
                        return nickname
            
            # 获取联系人信息
            contact = self.bot.get_contact_detail(wxid)
            if hasattr(contact, 'data') and contact.data:
                return getattr(contact.data, 'nickname', wxid)
            
            return wxid
            
        except Exception as e:
            logger.debug(f"获取用户昵称失败 {wxid}: {e}")
            return wxid
    
    def parse_member_nickname(self, wxid: str, member_info) -> str:
        """解析群成员昵称"""
        try:
            # 这里需要根据实际的RoomMembers结构来解析
            # 暂时返回wxid，需要根据具体API调整
            if hasattr(member_info, 'memberNickname'):
                return member_info.memberNickname
            elif hasattr(member_info, 'members') and wxid in str(member_info.members):
                # 可能需要进一步解析members字段
                pass
            
            return wxid
        except Exception as e:
            logger.debug(f"解析群成员昵称失败: {e}")
            return wxid
    
    def get_chat_name(self, chat_id: str) -> str:
        """获取聊天名称"""
        try:
            if chat_id.endswith("@chatroom"):
                # 群聊
                room = self.bot.get_room(chat_id)
                if hasattr(room, 'data') and room.data:
                    return getattr(room.data, 'chatRoomId', chat_id)
            else:
                # 私聊
                contact = self.bot.get_contact_detail(chat_id)
                if hasattr(contact, 'data') and contact.data:
                    return getattr(contact.data, 'nickname', chat_id)
            
            return chat_id
            
        except Exception as e:
            logger.debug(f"获取聊天名称失败 {chat_id}: {e}")
            return chat_id
    
    def extract_image_path(self, event: Event) -> str:
        """从事件中提取图片路径"""
        try:
            # 根据WeChatHook的实际实现来提取图片路径
            # 这可能需要根据具体的事件结构调整
            if hasattr(event, 'content') and event.content:
                # 可能图片路径在content中
                content = str(event.content)
                # 检查是否为文件路径格式
                if content.endswith(('.jpg', '.png', '.jpeg', '.gif', '.bmp')):
                    return content
                    
            # 如果有其他字段包含图片信息，可以在这里添加
            return ""
            
        except Exception as e:
            logger.debug(f"提取图片路径失败: {e}")
            return ""
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['success_rate'] = (
            stats['processed_messages'] / max(stats['total_messages'], 1)
        ) * 100 if stats['total_messages'] > 0 else 0
        
        return stats
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            'total_messages': 0,
            'filtered_messages': 0,
            'processed_messages': 0,
            'error_messages': 0
        }
        logger.info("统计信息已重置")