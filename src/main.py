from src.modules.spreadsheet import SpreadSheet
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser import Browser
from src.modules.logger import Logger  # SpreadSheetのロギング用
from src.modules.checker import ApplicantChecker
from src.modules.login import Login
from src.modules.search import Search
from src.utils.notifications import Notifier
from src.modules.scheduler import Scheduler
from collections import Counter
import time
from pathlib import Path
from src.utils.logging_config import get_logger
import traceback

def main(test_mode: bool = False):
    """
    メイン処理を実行します。

    Args:
        test_mode (bool): テストモードで実行するかどうか
    """
    # アプリケーションロガーの取得
    app_logger = get_logger(__name__)
    
    app_logger.info(f"実行モード: {'テスト' if test_mode else '本番'}")
    
    browser = None
    
    try:
        # 環境設定の読み込み
        env.load_env(test_mode=test_mode)
        
        # スケジューラーの初期化
        scheduler = Scheduler(
            list(map(int, env.get_config_value('SCHEDULE', 'exec_time1', '12:00').split(':'))),
            list(map(int, env.get_config_value('SCHEDULE', 'exec_time2', '18:00').split(':')))
        )
        
        # スケジューラーが有効な場合、実行時刻まで待機
        if scheduler.enabled:
            app_logger.info(f"スケジュール実行: {scheduler.get_schedule_text()}")
            scheduler.wait_for_execution_time()
        else:
            app_logger.info("スケジューラー無効: 即時実行")

        # SpreadSheet用のLoggerクラスのインスタンス化
        spreadsheet_logger = None
        try:
            spreadsheet_settings = env.get_spreadsheet_settings()
            if not spreadsheet_settings or not spreadsheet_settings.get('credentials_path') or not spreadsheet_settings.get('spreadsheet_key'):
                app_logger.warning("スプレッドシートの設定が不完全です。ロギングは無効化されます。")
            else:
                spreadsheet = SpreadSheet(
                    credentials_path=spreadsheet_settings['credentials_path'],
                    spreadsheet_key=spreadsheet_settings['spreadsheet_key']
                )
                # 接続を確認
                if spreadsheet.connect():
                    spreadsheet_logger = Logger(spreadsheet)
                    app_logger.info("✅ スプレッドシートへの接続に成功しました")
                else:
                    app_logger.error("スプレッドシートへの接続に失敗しました")
                    app_logger.warning("スプレッドシートへの接続なしで処理を続行します")
        except Exception as e:
            app_logger.error(f"スプレッドシートへの接続に失敗: {str(e)}")
            app_logger.warning("スプレッドシートへの接続なしで処理を続行します")
            # 接続失敗時はエラーを発生させず、Noneのままにする
        
        # Notifierクラスのインスタンス化（schedulerを渡す）
        webhook_url = env.get_env_var('SLACK_WEBHOOK', '')
        app_logger.debug(f"Slack webhook: {webhook_url if webhook_url else '未設定'}")
        
        if not webhook_url:
            app_logger.warning("Slack webhook URLが設定されていません。通知は無効化されます。")
            notifier = None
        else:
            notifier = Notifier(webhook_url)
        
        # セレクター情報の読み込み
        checker = ApplicantChecker(
            Path("config/selectors.csv"),
            Path("config/judge_list.csv")
        )
        selectors = checker.get_selectors()
        
        # ブラウザ設定の読み込み
        browser = Browser(
            settings_path='config/settings.ini',
            selectors_path='config/selectors.csv'
        )
        
        # ロガーインスタンスをブラウザに設定（存在する場合のみ）
        if spreadsheet_logger:
            browser.logger_instance = spreadsheet_logger
        
        print("\n=== ブラウザテスト開始 ===")
        print("1. ブラウザを起動中...")
        browser.setup()
        
        # ログイン処理
        print("2. ログイン処理を開始...")
        login = Login(browser)
        success, url = login.execute()
        if not success:
            raise Exception("ログイン処理に失敗しました")

        print("\n=== 検索処理開始 ===")
        print("\n3. 採用確認ページへ遷移中...")
        adoptions_url = f"{url}/adoptions"
        browser.driver.get(adoptions_url)
        time.sleep(2)

        # repeat_until_emptyの設定を読み込み
        repeat_until_empty = env.get_config_value('BROWSER', 'repeat_until_empty', False)

        # 検索条件を設定して検索を実行
        search = Search(browser, selectors)
        if not search.execute():
            raise Exception("検索処理に失敗しました")

        # 全ページを処理するループ
        applicants_to_log = browser.process_applicants(checker, env, process_next_page=repeat_until_empty)
        
        # 処理結果のログ出力
        app_logger.info(f"✅ 全{len(applicants_to_log)}件の処理が完了しました")

        # 成功通知（schedulerの情報を含める）
        if notifier:
            # パターン99をフィルタリングした統計情報
            include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)
            pattern_counts = Counter(applicant['pattern'] for applicant in applicants_to_log if 'pattern' in applicant)
            filtered_patterns = {
                k: v for k, v in pattern_counts.items() 
                if k != '99' or include_pattern_99
            }
            
            stats = {
                'total': len(applicants_to_log),
                'patterns': filtered_patterns
            }
            
            notifier.send_slack_notification(
                status="success",
                stats=stats,
                spreadsheet_key=env.get_spreadsheet_settings()['spreadsheet_key'],
                test_mode=test_mode,
                scheduler=scheduler  # schedulerを追加
            )

        return True
        
    except Exception as e:
        app_logger.error(f"❌ エラーが発生しました: {str(e)}")
        traceback.print_exc()
        # エラー通知
        if notifier:
            notifier.send_slack_notification(
                status="error",
                error_message=str(e),
                spreadsheet_key=env.get_spreadsheet_settings()['spreadsheet_key'],
                test_mode=test_mode,
                scheduler=scheduler  # schedulerを追加
            )
        return False
    finally:
        # ブラウザを終了
        if browser and browser.driver:
            browser.driver.quit()
            app_logger.info("✅ ブラウザを終了しました")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='採用確認自動チェックシステム')
    parser.add_argument('--test', action='store_true', help='テストモードで実行')
    args = parser.parse_args()
    
    main(test_mode=args.test) 