"""
配置管理模块 - 管理机器人的各种配置参数
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import asdict

from ..models.data_models import BotConfig, AlertConfig, AIConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "./config/bot_config.json"):
        self.config_file = config_file
        self.config_dir = os.path.dirname(config_file)
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载或创建默认配置
        self.config = self.load_config()
    
    def load_config(self) -> BotConfig:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 从字典创建配置对象
                alert_config_data = config_data.get('alert_config', {})
                alert_config = AlertConfig(
                    enable_realtime_alerts=alert_config_data.get('enable_realtime_alerts', True),
                    urgency_threshold=alert_config_data.get('urgency_threshold', 6),
                    max_context_messages=alert_config_data.get('max_context_messages', 10),
                    target_user=alert_config_data.get('target_user', '')
                )
                
                ai_config_data = config_data.get('ai_config', {})
                ai_config = AIConfig(
                    openai_api_key=ai_config_data.get('openai_api_key', ''),
                    openai_base_url=ai_config_data.get('openai_base_url', 'https://api.openai.com/v1'),
                    model=ai_config_data.get('model', 'gpt-4'),
                    max_tokens=ai_config_data.get('max_tokens', 2000),
                    temperature=ai_config_data.get('temperature', 0.3)
                )
                
                config = BotConfig(
                    database_path=config_data.get('database_path', './data/wechat_bot.db'),
                    data_retention_days=config_data.get('data_retention_days', 180),
                    daily_summary_time=config_data.get('daily_summary_time', '20:00'),
                    cleanup_interval_hours=config_data.get('cleanup_interval_hours', 24),
                    log_level=config_data.get('log_level', 'INFO'),
                    alert_config=alert_config,
                    ai_config=ai_config
                )
                
                logger.info(f"配置文件加载成功: {self.config_file}")
                return config
                
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return self.create_default_config()
        else:
            logger.info("配置文件不存在，创建默认配置")
            return self.create_default_config()
    
    def create_default_config(self) -> BotConfig:
        """创建默认配置"""
        config = BotConfig()
        self.save_config(config)
        return config
    
    def save_config(self, config: BotConfig = None) -> bool:
        """保存配置到文件"""
        try:
            if config is None:
                config = self.config
            
            config_dict = asdict(config)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置保存成功: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """更新配置"""
        try:
            updated = False
            
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    updated = True
                    logger.info(f"配置更新: {key} = {value}")
                elif key.startswith('alert_'):
                    # 更新推送配置
                    alert_key = key[6:]  # 移除 'alert_' 前缀
                    if hasattr(self.config.alert_config, alert_key):
                        setattr(self.config.alert_config, alert_key, value)
                        updated = True
                        logger.info(f"推送配置更新: {alert_key} = {value}")
                elif key.startswith('ai_'):
                    # 更新AI配置
                    ai_key = key[3:]  # 移除 'ai_' 前缀
                    if hasattr(self.config.ai_config, ai_key):
                        setattr(self.config.ai_config, ai_key, value)
                        updated = True
                        logger.info(f"AI配置更新: {ai_key} = {value}")
                else:
                    logger.warning(f"未知的配置项: {key}")
            
            if updated:
                return self.save_config()
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            if '.' in key:
                # 支持嵌套配置访问，如 'alert_config.target_user'
                keys = key.split('.')
                value = self.config
                for k in keys:
                    if hasattr(value, k):
                        value = getattr(value, k)
                    else:
                        return default
                return value
            else:
                return getattr(self.config, key, default)
        except Exception as e:
            logger.error(f"获取配置值失败 {key}: {e}")
            return default
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置有效性"""
        issues = {}
        
        # 验证AI配置
        if not self.config.ai_config.openai_api_key:
            issues['ai_api_key'] = "OpenAI API Key未配置"
        
        # 验证推送配置
        if self.config.alert_config.enable_realtime_alerts and not self.config.alert_config.target_user:
            issues['target_user'] = "启用了实时推送但未设置目标用户"
        
        # 验证数据库路径
        db_dir = os.path.dirname(self.config.database_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                issues['database_path'] = f"数据库目录创建失败: {e}"
        
        # 验证日志级别
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.log_level.upper() not in valid_log_levels:
            issues['log_level'] = f"无效的日志级别: {self.config.log_level}"
        
        # 验证时间格式
        try:
            from datetime import datetime
            datetime.strptime(self.config.daily_summary_time, '%H:%M')
        except ValueError:
            issues['daily_summary_time'] = f"无效的时间格式: {self.config.daily_summary_time}"
        
        return issues
    
    def create_config_template(self) -> str:
        """创建配置模板文件"""
        template = {
            "database_path": "./data/wechat_bot.db",
            "data_retention_days": 180,
            "daily_summary_time": "20:00",
            "cleanup_interval_hours": 24,
            "log_level": "INFO",
            "alert_config": {
                "enable_realtime_alerts": True,
                "urgency_threshold": 6,
                "max_context_messages": 10,
                "target_user": "your_wechat_id_here"
            },
            "ai_config": {
                "openai_api_key": "your_openai_api_key_here",
                "openai_base_url": "https://api.openai.com/v1",
                "model": "gpt-4",
                "max_tokens": 2000,
                "temperature": 0.3
            }
        }
        
        template_file = os.path.join(self.config_dir, "bot_config_template.json")
        
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            logger.info(f"配置模板创建成功: {template_file}")
            return template_file
        except Exception as e:
            logger.error(f"创建配置模板失败: {e}")
            return ""
    
    def export_config(self, export_file: str = None) -> str:
        """导出当前配置"""
        if export_file is None:
            export_file = os.path.join(self.config_dir, f"config_backup_{int(time.time())}.json")
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
            logger.info(f"配置导出成功: {export_file}")
            return export_file
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return ""
    
    def import_config(self, import_file: str) -> bool:
        """导入配置"""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # 备份当前配置
            backup_file = self.export_config()
            
            # 应用导入的配置
            if self.update_config(**imported_data):
                logger.info(f"配置导入成功: {import_file}")
                return True
            else:
                logger.error("配置导入失败")
                return False
                
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            # 备份当前配置
            backup_file = self.export_config()
            
            # 创建新的默认配置
            self.config = BotConfig()
            
            # 保存配置
            if self.save_config():
                logger.info(f"配置已重置为默认值，备份保存至: {backup_file}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> BotConfig:
    """获取当前配置"""
    return config_manager.config


def update_config(**kwargs) -> bool:
    """更新配置的便捷函数"""
    return config_manager.update_config(**kwargs)


def save_config() -> bool:
    """保存配置的便捷函数"""
    return config_manager.save_config()