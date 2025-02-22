# utils\logging_config.py
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from .environment import EnvironmentUtils as env

class PatternFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)

    def filter(self, record):
        # パターン99に関するログをフィルタリング
        if hasattr(record, 'pattern') and record.pattern == '99':
            return self.include_pattern_99
        return True

def get_logger(name: str) -> logging.Logger:
    """ロガーの設定"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # ハンドラーが未設定の場合のみ追加
        # ログディレクトリの作成
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # ログファイルの設定
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        
        # フォーマッターの作成
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # ファイルハンドラーの設定
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # コンソールハンドラーの設定
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # ロガーの設定
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # パターンフィルターを追加
        pattern_filter = PatternFilter()
        logger.addFilter(pattern_filter)
        
        # 伝播を防止
        logger.propagate = False
    
    return logger

def cleanup_old_logs() -> None:
    """古いログファイルをクリーンアップ"""
    logger = get_logger(__name__)
    log_dir = Path("logs")
    
    if not log_dir.exists():
        return
    
    try:
        # 30日以上前のログを削除
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for log_file in log_dir.glob("app_*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    logger.info(f"古いログファイルを削除: {log_file}")
            except Exception as e:
                logger.error(f"ログファイル {log_file} の削除中にエラー: {e}")
                
    except Exception as e:
        logger.error(f"ログクリーンアップ中にエラー: {e}")
