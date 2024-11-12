import os
import logging
from datetime import datetime
from utils import read_settings

def setup_logging(debug_mode: bool = False):
    """アプリケーション全体のロギング設定

    Args:
        debug_mode (bool): Trueの場合、ログレベルをDEBUGに設定。Falseの場合はINFO
    """
    try:
        # 設定ファイルから source_directory を取得
        settings = read_settings()
        source_dir = settings.get('source_directory', os.getcwd())
        
        # ログフォルダを作成（プロジェクトのルートディレクトリ直下）
        log_dir = os.path.join(source_dir, 'log')
        os.makedirs(log_dir, exist_ok=True)

        # ログファイルのパス
        log_file = os.path.join(log_dir, 'application.log')

        # 既存のハンドラを削除（重複を防ぐ）
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # ログレベルの設定
        log_level = logging.DEBUG if debug_mode else logging.INFO

        # 基本設定
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                # コンソール出力用ハンドラ
                logging.StreamHandler(),
                # ファイル出力用ハンドラ
                logging.FileHandler(log_file, encoding='utf-8', mode='a')
            ]
        )

        # 実行開始のログを記録
        logging.info("="*50)
        logging.info(f"Application started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Log Level: {'DEBUG' if debug_mode else 'INFO'}")
        logging.info(f"Log Directory: {log_dir}")
        logging.info("="*50)

    except Exception as e:
        print(f"ログ設定中にエラーが発生しました: {e}")
        # 最低限のログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.error(f"Failed to setup logging: {e}")