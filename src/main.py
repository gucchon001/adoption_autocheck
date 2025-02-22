from src.modules.spreadsheet import SpreadSheet
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser import Browser
from src.modules.logger import Logger
from src.modules.checker import ApplicantChecker
from src.modules.login import Login
from src.modules.search import Search
from src.utils.notifications import Notifier
from collections import Counter
import time
from pathlib import Path

def main(test_mode: bool = False):
    """
    メイン処理を実行します。

    Args:
        test_mode (bool): テストモードで実行するかどうか
    """
    print(f"実行モード: {'テスト' if test_mode else '本番'}")
    
    # 環境設定の読み込み
    env.load_env(test_mode=test_mode)
    
    # SpreadSheetクラスのインスタンス化
    spreadsheet_settings = env.get_spreadsheet_settings()
    spreadsheet = SpreadSheet(
        credentials_path=spreadsheet_settings['credentials_path'],
        spreadsheet_key=spreadsheet_settings['spreadsheet_key']
    )
    
    # Notifierクラスのインスタンス化
    webhook_url = env.get_env_var('SLACK_WEBHOOK', '')
    print(f"\nDEBUG: Slack webhook: {webhook_url if webhook_url else '未設定'}")
    
    if not webhook_url:
        print("警告: Slack webhook URLが設定されていません。通知は無効化されます。")
        notifier = None
    else:
        notifier = Notifier(webhook_url)
    
    try:
        # スプレッドシートに接続
        if not spreadsheet.connect():
            raise Exception("スプレッドシートへの接続に失敗しました")
        
        # Loggerクラスのインスタンス化
        logger = Logger(spreadsheet)
        
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

        # 繰り返し処理の設定を読み込み
        repeat_until_empty = env.get_config_value('BROWSER', 'repeat_until_empty', False)
        all_applicants = []
        first_search = True
        pattern_counts = Counter()

        while True:
            if first_search:
                # 初回のみ検索条件を設定
                search = Search(browser, selectors)
                if not search.execute():
                    raise Exception("検索処理に失敗しました")
                first_search = False
            else:
                # 2回目以降は単純にページをリロード
                browser.driver.refresh()
                time.sleep(2)  # ページの読み込みを待機

            # 応募者データの処理
            applicants_to_log = browser.process_applicants(checker, env)
            
            if not applicants_to_log:
                print("処理対象のデータがありません")
                break
                
            # パターンのカウント
            for applicant in applicants_to_log:
                if 'pattern' in applicant:
                    pattern_counts[applicant['pattern']] += 1
            
            all_applicants.extend(applicants_to_log)
            
            if not repeat_until_empty:
                break
                
            time.sleep(2)  # 次の処理前に待機

        # ログの記録（全件まとめて）
        if all_applicants:
            if not logger.log_applicants(all_applicants):
                raise Exception("ログの記録に失敗しました")
            print(f"\n✅ 全{len(all_applicants)}件の処理が完了しました")

            # 成功通知
            if notifier:
                stats = {
                    'total': len(all_applicants),
                    'patterns': dict(pattern_counts)
                }
                notifier.send_slack_notification(
                    status="success",
                    stats=stats,
                    spreadsheet_key=spreadsheet_settings['spreadsheet_key'],
                    test_mode=test_mode
                )

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        # エラー通知
        if notifier:
            notifier.send_slack_notification(
                status="error",
                error_message=str(e),
                spreadsheet_key=spreadsheet_settings['spreadsheet_key'],
                test_mode=test_mode
            )
        raise
    finally:
        # ブラウザを終了
        if browser and browser.driver:
            browser.driver.quit()
            print("\n✅ ブラウザを終了しました")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='採用確認自動チェックシステム')
    parser.add_argument('--test', action='store_true', help='テストモードで実行')
    args = parser.parse_args()
    
    main(test_mode=args.test) 