#\utils.environment.py
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any
import configparser

class EnvironmentUtils:
    """プロジェクト全体で使用する環境関連のユーティリティクラス"""

    # プロジェクトルートのデフォルト値
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def set_project_root(path: Path) -> None:
        """
        プロジェクトのルートディレクトリを設定します。

        Args:
            path (Path): 新しいプロジェクトルート
        """
        EnvironmentUtils.BASE_DIR = path

    @staticmethod
    def get_project_root() -> Path:
        """
        プロジェクトのルートディレクトリを取得します。

        Returns:
            Path: プロジェクトのルートディレクトリ
        """
        return EnvironmentUtils.BASE_DIR

    @staticmethod
    def load_env(test_mode: bool = False) -> None:
        """
        環境変数を .env ファイルからロードします。

        Args:
            test_mode (bool): テストモードで実行するかどうか
        """
        env_file = (
            EnvironmentUtils.BASE_DIR / "config" / 
            ("secrets_test.env" if test_mode else "secrets.env")
        )

        if not env_file.exists():
            raise FileNotFoundError(f"{env_file} が見つかりません。")

        load_dotenv(env_file)
        
        # 設定ファイルのパスを設定
        EnvironmentUtils._settings_file = (
            EnvironmentUtils.BASE_DIR / "config" / 
            ("settings_test.ini" if test_mode else "settings.ini")
        )

    @staticmethod
    def get_env_var(var_name: str, default: Optional[Any] = None) -> Any:
        """
        環境変数を取得します。見つからない場合はデフォルト値を返します。

        Args:
            var_name (str): 環境変数名
            default (Optional[Any]): 環境変数が見つからなかった場合に返すデフォルト値

        Returns:
            Any: 環境変数の値またはデフォルト値
        """
        value = os.getenv(var_name, default)
        if value is None:
            raise ValueError(f"環境変数 {var_name} が設定されていません。")
        return value

    @staticmethod
    def get_config_file(file_name: str = "settings.ini") -> Path:
        """
        設定ファイルのパスを取得します。

        Args:
            file_name (str): 設定ファイル名

        Returns:
            Path: 設定ファイルのパス

        Raises:
            FileNotFoundError: 指定された設定ファイルが見つからない場合
        """
        config_path = EnvironmentUtils.BASE_DIR / "config" / file_name
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        return config_path

    @staticmethod
    def get_config_value(section: str, key: str, default: Optional[Any] = None) -> Any:
        """
        設定ファイルから指定のセクションとキーの値を取得します。

        Args:
            section (str): セクション名
            key (str): キー名
            default (Optional[Any]): デフォルト値

        Returns:
            Any: 設定値
        """
        config_path = EnvironmentUtils.get_config_file()
        config = configparser.ConfigParser()

        # utf-8 エンコーディングで読み込む
        config.read(config_path, encoding='utf-8')

        if not config.has_section(section):
            return default
        if not config.has_option(section, key):
            return default

        value = config.get(section, key, fallback=default)

        # 型変換
        if value.isdigit():
            return int(value)
        if value.replace('.', '', 1).isdigit():
            return float(value)
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        return value

    @staticmethod
    def resolve_path(path: str) -> Path:
        """
        指定されたパスをプロジェクトルートに基づいて絶対パスに変換します。

        Args:
            path (str): 相対パスまたは絶対パス

        Returns:
            Path: 解決された絶対パス
        """
        resolved_path = Path(path)
        if not resolved_path.is_absolute():
            resolved_path = EnvironmentUtils.get_project_root() / resolved_path

        if not resolved_path.exists():
            raise FileNotFoundError(f"Resolved path does not exist: {resolved_path}")

        return resolved_path

    @staticmethod
    def get_service_account_file() -> Path:
        """
        Google Service Account の認証情報JSONファイルのパスを取得します。

        Returns:
            Path: 認証情報JSONファイルのパス
        """
        # settings.ini から認証情報ファイルのパスを取得
        service_account_path_str = EnvironmentUtils.get_config_value(
            "SERVICE", 
            "service_account_file", 
            "config/data.json"  # デフォルト値
        )
        
        # パスを解決
        service_account_path = EnvironmentUtils.resolve_path(service_account_path_str)
        
        if not service_account_path.exists():
            raise FileNotFoundError(
                f"Service account file not found: {service_account_path}\n"
                f"Please check the path in settings.ini"
            )
        
        return service_account_path

    @staticmethod
    def get_environment() -> str:
        """
        環境変数 APP_ENV を取得します。
        デフォルト値は 'development' です。

        Returns:
            str: 現在の環境（例: 'development', 'production'）
        """
        return EnvironmentUtils.get_env_var("APP_ENV", "development")

    @staticmethod
    def get_openai_api_key():
        """
        Get the OpenAI API key from the environment variables.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY が設定されていません。環境変数を確認してください。")
        return api_key

    @staticmethod
    def get_openai_model():
        """
        OpenAI モデル名を settings.ini ファイルから取得します。
        設定がない場合はデフォルト値 'gpt-4o' を返します。
        """
        return EnvironmentUtils.get_config_value("OPENAI", "model", default="gpt-4o")

    @staticmethod
    def get_spreadsheet_settings():
        """
        スプレッドシート関連の設定を取得します。

        Returns:
            dict: {
                'credentials_path': Path,  # サービスアカウントの認証情報JSONファイルのパス
                'spreadsheet_key': str     # スプレッドシートのキー
            }
        
        Raises:
            ValueError: 必要な設定が見つからない場合
        """
        try:
            # 認証情報ファイルのパスを取得
            credentials_path = EnvironmentUtils.get_service_account_file()
            
            # スプレッドシートキーを環境変数から取得
            spreadsheet_key = EnvironmentUtils.get_env_var("SPREADSHEET_KEY")
            
            return {
                'credentials_path': credentials_path,
                'spreadsheet_key': spreadsheet_key
            }
        except Exception as e:
            raise ValueError(f"スプレッドシートの設定取得に失敗: {str(e)}")