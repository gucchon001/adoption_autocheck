from src.utils.environment import EnvironmentUtils
from src.modules.browser import Browser
from src.modules.adoption import Adoption
from src.modules.spreadsheet import SpreadSheet
from src.modules.scheduler import Scheduler
from src.modules.log_manager import LogManager
from src.utils.notifications import Notifier
import time

def main(test_mode: bool = False):
    """
    メイン処理を実行します。

    Args:
        test_mode (bool): テストモードで実行するかどうか
    """
    print(f"実行モード: {'テスト' if test_mode else '本番'}")
    
    # 環境設定の読み込み（テストモード指定）
    EnvironmentUtils.load_env(test_mode=test_mode)
    
    # 各サービスの初期化
    scheduler = Scheduler(
        list(map(int, EnvironmentUtils.get_config_value("SCHEDULE", "exec_time1").split(":"))),
        list(map(int, EnvironmentUtils.get_config_value("SCHEDULE", "exec_time2").split(":")))
    )
    
    # ログファイルのパスを /log/log.txt に修正
    log_path = EnvironmentUtils.get_project_root() / "log" / "log.txt"
    log_manager = LogManager(log_path)
    
    notifier = Notifier(EnvironmentUtils.get_env_var("SLACK_WEBHOOK"))
    
    domain = EnvironmentUtils.get_env_var("ADMIN_URL").replace('https://', '').split('/')[0]
    spreadsheet_key = EnvironmentUtils.get_env_var("SPREADSHEET_KEY")

    while True:
        # 実行時間待機（テストモードの場合はスキップ）
        if not test_mode:
            print("待機中")
            scheduler.wait_for_execution_time()
        else:
            print("[テストモード] スケジュール待機をスキップします")

        try:
            print("処理を開始します...")
            # スプレッドシートの初期化
            spreadsheet = SpreadSheet(
                EnvironmentUtils.get_service_account_file(),
                spreadsheet_key
            )
            if not spreadsheet.connect():
                raise Exception("スプレッドシートへの接続に失敗しました")

            # ブラウザの初期化と操作
            browser = Browser()
            browser.setup()
            browser.login(
                f"https://{domain}/admin/",
                {
                    "id": EnvironmentUtils.get_env_var("BASIC_AUTH_ID"),
                    "password": EnvironmentUtils.get_env_var("BASIC_AUTH_PASSWORD")
                },
                {
                    "id": EnvironmentUtils.get_env_var("LOGIN_ID"),
                    "password": EnvironmentUtils.get_env_var("LOGIN_PASSWORD")
                }
            )

            # 採用確認ページへ遷移して検索実行
            if not browser.go_to_adoptions_and_search(test_mode):
                raise Exception("採用確認ページの遷移または検索に失敗しました")

            # 応募者情報の取得と処理
            adoption = Adoption(browser.driver, browser.wait)
            applicants_data = adoption.get_applicants_data()
            checked_applicants = adoption.apply_checks(applicants_data, log_manager.get_processed_ids())

            # ログの記録とSlack通知
            if checked_applicants and spreadsheet.append_logs(checked_applicants):
                notifier.send_slack_notification(
                    '@channel 採用確認の自動チェックが完了しました！',
                    spreadsheet_key
                )
                log_manager.save_processed_ids(
                    [applicant["id"] for applicant in checked_applicants]
                )

        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
        finally:
            if 'browser' in locals():
                browser.quit()

        print("実行終了")
        
        # テストモードの場合は1回で終了
        if test_mode:
            break
        else:
            print("60秒後に次の実行を開始します...")
            time.sleep(60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='採用確認自動チェックシステム')
    parser.add_argument('--test', action='store_true', help='テストモードで実行')
    args = parser.parse_args()
    
    main(test_mode=args.test) 