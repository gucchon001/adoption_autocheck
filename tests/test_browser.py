import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from datetime import datetime

from src.modules.browser import Browser
from src.modules.login import Login
from src.modules.search import Search
from src.modules.adoption import Adoption
from src.modules.logger import Logger
from src.modules.checker import ApplicantChecker
from src.utils.environment import EnvironmentUtils as env
from src.modules.spreadsheet import SpreadSheet
import time
import os

def test_browser():
    # 環境変数の読み込み
    env.load_env(test_mode=True)
    
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
    
    # 転記対象のデータを保持するリスト
    applicants_to_log = []
    
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

        # 採用確認処理
        print("\n=== 採用確認処理開始 ===")
        adoption = Adoption(browser, selectors, checker=checker, env=env)
        
        # 検索結果の確認
        has_data, record_count = adoption.check_search_results()
        if not has_data:
            print("処理対象のデータがありません")
            return

        # テーブルの取得
        table = browser.wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "#recruitment-list table.table-sm"
            ))
        )
        rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")

        # レコードの処理
        for record_index in range(record_count):
            applicant_data = adoption.process_record(rows, record_index)
            if applicant_data:
                applicants_to_log.append(applicant_data)

        print(f"\n✅ 全{record_count}件の処理が完了しました")

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
    test_browser()