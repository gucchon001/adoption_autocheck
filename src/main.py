from src.modules.spreadsheet import SpreadSheet
from src.utils.environment import EnvironmentUtils as env
from src.modules.browser import Browser
from src.modules.logger import Logger
from src.modules.checker import ApplicantChecker
from src.modules.login import Login
from src.modules.search import Search
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
    
    try:
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

        # 検索処理
        search = Search(browser, selectors)
        if not search.execute():
            raise Exception("検索処理に失敗しました")

        # 応募者データの処理（セレクター情報を直接渡す）
        applicants_to_log = browser.process_applicants(checker, env)

        # ログの記録
        if applicants_to_log:
            print("\n=== ログ記録処理開始 ===")
            if not logger.log_applicants(applicants_to_log):
                raise Exception("ログの記録に失敗しました")

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
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