# utils\logging_config.py
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from .environment import EnvironmentUtils as env
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

class LoggingConfig:
    _initialized = False

    def __init__(self):
        """
        ログ設定を初期化します。
        """
        if LoggingConfig._initialized:
            return  # 再初期化を防止

        # 環境ユーティリティを使用して現在の環境を取得
        envutils = env.get_environment()
        
        # 環境に応じたログレベルを設定
        self.log_level = self.get_log_level(envutils)
        
        self.log_dir = Path("logs")
        self.log_format = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

        self.setup_logging()

        LoggingConfig._initialized = True  # 初期化済みフラグを設定

    def get_log_level(self, envutils: str) -> int:
        """
        環境に応じたログレベルを取得します。

        Args:
            env (str): 現在の環境 ('development' または 'production')

        Returns:
            int: ログレベル
        """
        # settings.ini から LOG_LEVEL を取得
        log_level_str = env.get_config_value(section=envutils, key="LOG_LEVEL", default="INFO")
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        return log_level

    def setup_logging(self) -> None:
        """
        ロギング設定をセットアップします。
        """
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

        handlers = [
            logging.handlers.TimedRotatingFileHandler(
                log_file, when="midnight", interval=1, backupCount=30, encoding="utf-8"
            ),
            logging.StreamHandler(),
        ]

        logging.basicConfig(
            level=self.log_level,
            format=self.log_format,
            handlers=handlers,
        )

        logging.getLogger().info("Logging setup complete.")

def load_log_settings() -> Dict:
    """設定ファイルからログ設定を読み込む"""
    return {
        'max_file_size_mb': env.get_config_value('log_settings', 'max_file_size_mb', 10),
        'backup_count': env.get_config_value('log_settings', 'backup_count', 30),
        'max_age_days': env.get_config_value('log_settings', 'max_age_days', 90),
        'max_total_size_mb': env.get_config_value('log_settings', 'max_total_size_mb', 1000),
        'log_dir': env.get_config_value('log_settings', 'log_dir', 'logs')
    }

def get_logger(name: str) -> logging.Logger:
    """ロガーの設定"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        settings = load_log_settings()
        logger.setLevel(logging.DEBUG)
        
        # ログディレクトリの作成
        log_dir = Path(settings['log_dir'])
        log_dir.mkdir(exist_ok=True)
        
        # ファイル名の設定
        log_file = log_dir / f"app.log"
        
        # RotatingFileHandlerの設定
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=settings['max_file_size_mb'] * 1024 * 1024,
            backupCount=settings['backup_count'],
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

def cleanup_old_logs() -> None:
    """古いログファイルをクリーンアップ"""
    settings = load_log_settings()
    log_path = Path(settings['log_dir'])
    
    if not log_path.exists():
        return
        
    logger = logging.getLogger(__name__)
    
    try:
        # 合計サイズの確認
        total_size = sum(f.stat().st_size for f in log_path.glob("**/*") if f.is_file())
        total_size_mb = total_size / (1024 * 1024)
        
        if total_size_mb > settings['max_total_size_mb']:
            logger.warning(f"ログディレクトリのサイズが {total_size_mb:.2f}MB を超えています")
        
        # 古いファイルの削除
        cutoff_date = datetime.now() - timedelta(days=settings['max_age_days'])
        
        for log_file in log_path.glob("*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    logger.info(f"古いログファイルを削除: {log_file}")
            except Exception as e:
                logger.error(f"ログファイル {log_file} の削除中にエラー: {e}")
                
    except Exception as e:
        logger.error(f"ログクリーンアップ中にエラー: {e}")
