"""
工具函数模块 - 提供通用的辅助功能
"""
import os
import time
import logging
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """设置日志配置"""
    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # 控制台输出
        ]
    )
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    
    logger.info(f"日志系统初始化完成，级别: {log_level}")


def ensure_directory(directory: str) -> bool:
    """确保目录存在"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {directory}: {e}")
        return False


def safe_int(value: Any, default: int = 0) -> int:
    """安全转换为整数"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    try:
        return timestamp.strftime(format_str)
    except Exception:
        return str(timestamp)


def parse_time_string(time_str: str) -> Optional[tuple]:
    """解析时间字符串 (HH:MM) 返回 (hour, minute)"""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:
            hour = int(parts[0])
            minute = int(parts[1])
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
    except ValueError:
        pass
    
    logger.warning(f"无效的时间格式: {time_str}")
    return None


def calculate_date_range(days_back: int = 1) -> tuple:
    """计算日期范围"""
    end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    start_date = (end_date - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start_date, end_date


def get_date_string(date: datetime = None, format_str: str = "%Y-%m-%d") -> str:
    """获取日期字符串"""
    if date is None:
        date = datetime.now()
    return date.strftime(format_str)


def validate_wxid(wxid: str) -> bool:
    """验证微信ID格式"""
    if not wxid:
        return False
    
    # 基本的微信ID格式检查
    # 微信ID通常是字母数字组合，可能包含下划线和连字符
    import re
    pattern = r'^[a-zA-Z0-9_-]+(@chatroom)?$'
    return bool(re.match(pattern, wxid))


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.running = False
        self.jobs = []
    
    def add_daily_job(self, func, time_str: str, *args, **kwargs):
        """添加每日定时任务"""
        job = schedule.every().day.at(time_str).do(func, *args, **kwargs)
        self.jobs.append(job)
        logger.info(f"添加每日任务: {func.__name__} at {time_str}")
        return job
    
    def add_interval_job(self, func, interval_hours: int, *args, **kwargs):
        """添加间隔任务"""
        job = schedule.every(interval_hours).hours.do(func, *args, **kwargs)
        self.jobs.append(job)
        logger.info(f"添加间隔任务: {func.__name__} every {interval_hours} hours")
        return job
    
    def start(self):
        """启动调度器"""
        self.running = True
        logger.info("任务调度器启动")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止调度器")
                break
            except Exception as e:
                logger.error(f"调度器运行异常: {e}")
                time.sleep(60)
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("任务调度器停止")
    
    def clear_jobs(self):
        """清除所有任务"""
        schedule.clear()
        self.jobs.clear()
        logger.info("所有任务已清除")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def record_metric(self, name: str, value: float):
        """记录指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'timestamp': time.time()
        })
        
        # 保留最近1000个数据点
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]
    
    def get_average(self, name: str, window_seconds: int = 3600) -> Optional[float]:
        """获取指定时间窗口内的平均值"""
        if name not in self.metrics:
            return None
        
        cutoff_time = time.time() - window_seconds
        recent_values = [
            m['value'] for m in self.metrics[name] 
            if m['timestamp'] > cutoff_time
        ]
        
        if not recent_values:
            return None
        
        return sum(recent_values) / len(recent_values)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            'uptime_seconds': time.time() - self.start_time,
            'metrics_count': len(self.metrics),
            'metrics': {}
        }
        
        for name, data in self.metrics.items():
            if data:
                values = [m['value'] for m in data[-100:]]  # 最近100个数据点
                stats['metrics'][name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[-1] if values else None
                }
        
        return stats


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
    
    def can_proceed(self) -> bool:
        """检查是否可以继续执行"""
        now = time.time()
        
        # 清理过期的调用记录
        cutoff_time = now - self.window_seconds
        self.calls = [call_time for call_time in self.calls if call_time > cutoff_time]
        
        # 检查是否超过限制
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """计算需要等待的时间"""
        if not self.calls:
            return 0
        
        oldest_call = min(self.calls)
        return max(0, self.window_seconds - (time.time() - oldest_call))


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logger.warning(f"{func.__name__} 第{attempt + 1}次尝试失败，{wait_time:.1f}秒后重试: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} 重试{max_retries}次后仍然失败: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


def measure_execution_time(func):
    """测量执行时间的装饰器"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} 执行时间: {execution_time:.3f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 (耗时{execution_time:.3f}秒): {e}")
            raise
    
    return wrapper


def cleanup_temp_files(temp_dir: str = "./temp", max_age_hours: int = 24):
    """清理临时文件"""
    try:
        if not os.path.exists(temp_dir):
            return
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    logger.debug(f"删除临时文件失败 {file_path}: {e}")
        
        logger.info(f"临时文件清理完成，删除了{deleted_count}个文件")
        
    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def get_system_info() -> Dict[str, Any]:
    """获取系统信息"""
    import platform
    import psutil
    
    try:
        return {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': format_file_size(psutil.virtual_memory().total),
            'memory_available': format_file_size(psutil.virtual_memory().available),
            'disk_usage': format_file_size(psutil.disk_usage('/').used)
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return {'error': str(e)}