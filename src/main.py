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

def main(test_mode: bool = False):
    """
    メイン処理を実行します。

    Args:
        test_mode (bool): テストモードで実行するかどうか
    """
    # アプリケーションロガーの取得
    app_logger = get_logger(__name__)
    
    app_logger.info(f"実行モード: {'テスト' if test_mode else '本番'}")
    
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

        # SpreadSheetクラスのインスタンス化
        spreadsheet_settings = env.get_spreadsheet_settings()
        spreadsheet = SpreadSheet(
            credentials_path=spreadsheet_settings['credentials_path'],
            spreadsheet_key=spreadsheet_settings['spreadsheet_key']
        )
        
        # Notifierクラスのインスタンス化（schedulerを渡す）
        webhook_url = env.get_env_var('SLACK_WEBHOOK', '')
        app_logger.debug(f"Slack webhook: {webhook_url if webhook_url else '未設定'}")
        
        if not webhook_url:
            app_logger.warning("Slack webhook URLが設定されていません。通知は無効化されます。")
            notifier = None
        else:
            notifier = Notifier(webhook_url)
        
        # スプレッドシートに接続
        if not spreadsheet.connect():
            raise Exception("スプレッドシートへの接続に失敗しました")
        
        # SpreadSheet用のLoggerクラスのインスタンス化
        spreadsheet_logger = Logger(spreadsheet)
        
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
        # process_applicantsメソッドにrepeat_until_emptyを渡す
        applicants_to_log = browser.process_applicants(checker, env, process_next_page=repeat_until_empty)

        # ログの記録（全件まとめて）
        if applicants_to_log:
            if not spreadsheet_logger.log_applicants(applicants_to_log):
                raise Exception("ログの記録に失敗しました")
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
                    spreadsheet_key=spreadsheet_settings['spreadsheet_key'],
                    test_mode=test_mode,
                    scheduler=scheduler  # schedulerを追加
                )

    except Exception as e:
        app_logger.error(f"❌ エラーが発生しました: {str(e)}")
        # エラー通知
        if notifier:
            notifier.send_slack_notification(
                status="error",
                error_message=str(e),
                spreadsheet_key=spreadsheet_settings['spreadsheet_key'],
                test_mode=test_mode,
                scheduler=scheduler  # schedulerを追加
            )
        raise
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