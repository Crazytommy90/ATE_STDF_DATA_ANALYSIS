"""
日志配置模块 - 应用关闭时备份日志
"""
from loguru import logger
import os
import shutil
from datetime import datetime

class LoggerManager:
    _instance = None
    _logger = None
    _handler_id = None
    _log_file = None
    _max_backups = 5
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def setup_logger(self, log_file='logger.log', max_bytes=10*1024, backup_count=5):
        """
        配置日志记录器
        :param log_file: 日志文件路径
        :param max_bytes: 单个日志文件最大字节数（仅用于提示，不实际限制）
        :param backup_count: 保留的备份文件数量（默认5个）
        """
        self._log_file = log_file
        self._max_backups = backup_count
        
        # 如果已有handler，先移除
        if self._handler_id is not None:
            try:
                logger.remove(self._handler_id)
            except:
                pass
            self._handler_id = None
        
        # 如果是第一次，移除默认handler
        if self._logger is None:
            try:
                logger.remove()
            except:
                pass
        
        # 添加文件handler，不设置轮转（在应用运行期间持续写入同一文件）
        self._handler_id = logger.add(
            log_file,
            format="[{time:YYYY-MM-DD HH:mm:ss}] {message}",
            level="INFO",
            encoding='utf-8',
            enqueue=True  # 异步写入，避免阻塞
        )
        
        self._logger = logger
        return self._logger
    
    def get_logger(self):
        """获取logger实例"""
        if self._logger is None:
            self.setup_logger()
        return self._logger
    
    def log_app_start(self):
        """记录应用启动"""
        if self._logger:
            self._logger.info('='*80)
            self._logger.info('Application Started')
            self._logger.info('='*80)
    
    def log_app_close(self):
        """记录应用关闭并备份日志文件"""
        if self._logger:
            self._logger.info('Application Closed')
            self._logger.info('')
            
            # 刷新日志确保写入完成
            if self._handler_id is not None:
                logger.complete()  # 等待所有异步日志写入完成
                logger.remove(self._handler_id)
                self._handler_id = None
            
            # 备份日志文件
            self._backup_log_file()
    
    def _backup_log_file(self):
        """备份日志文件并清理旧备份"""
        if not self._log_file or not os.path.exists(self._log_file):
            return
        
        # 生成备份文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_name = f"{self._log_file}.{timestamp}"
        
        try:
            # 复制当前日志为备份
            shutil.copy2(self._log_file, backup_name)
            
            # 清理旧备份，只保留最近的N个
            self._cleanup_old_backups()
            
            # 清空当前日志文件（为下次启动准备）
            with open(self._log_file, 'w', encoding='utf-8') as f:
                pass
                
        except Exception as e:
            print(f"备份日志文件失败: {e}")
    
    def _cleanup_old_backups(self):
        """清理旧的备份文件，只保留最近的N个"""
        if not self._log_file:
            return
        
        # 获取所有备份文件
        dir_path = os.path.dirname(self._log_file) or '.'
        base_name = os.path.basename(self._log_file)
        
        backups = []
        for f in os.listdir(dir_path):
            if f.startswith(base_name + '.') and f != base_name:
                full_path = os.path.join(dir_path, f)
                backups.append((full_path, os.path.getmtime(full_path)))
        
        # 按修改时间排序（最新的在前）
        backups.sort(key=lambda x: x[1], reverse=True)
        
        # 删除超出数量的旧备份
        for backup_path, _ in backups[self._max_backups:]:
            try:
                os.remove(backup_path)
            except Exception as e:
                print(f"删除旧备份失败 {backup_path}: {e}")