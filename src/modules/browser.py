from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import configparser
import time
import pandas as pd
from selenium.webdriver.support.select import Select
from ..utils.environment import EnvironmentUtils
from .adoption import Adoption

class Browser:
    def __init__(self, settings_path='config/settings.ini', selectors_path='config/selectors.csv'):
        self.driver = None
        self.settings = self._load_settings(settings_path)
        self.selectors = self._load_selectors(selectors_path)
        self.wait = None

    def _load_settings(self, settings_path):
        """設定ファイルを読み込む"""
        config = configparser.ConfigParser()
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                config.read_file(f)
            return config
        except Exception as e:
            print(f"設定ファイルの読み込みでエラー: {str(e)}")
            raise

    def _load_selectors(self, selectors_path):
        """セレクター設定の読み込み"""
        df = pd.read_csv(selectors_path)
        # DataFrameをディクショナリに変換
        selectors = {}
        for _, row in df.iterrows():
            if row['page'] not in selectors:
                selectors[row['page']] = {}
            selectors[row['page']][row['element']] = {
                'type': row['selector_type'],
                'value': row['selector_value']
            }
        return selectors

    def _get_element(self, page, element, wait=30):
        """指定された要素を取得"""
        selector = self.selectors[page][element]
        by_type = getattr(By, selector['type'].upper())
        return WebDriverWait(self.driver, wait).until(
            EC.visibility_of_element_located((by_type, selector['value']))
        )

    def setup(self):
        """ChromeDriverのセットアップ"""
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        
        if self.settings.getboolean('BROWSER', 'headless', fallback=True):
            options.add_argument('--headless=new')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 20)
        self.driver.maximize_window()

    def login(self, url, basic_auth, login_credentials):
        """サービスへのログイン処理"""
        base_url = url.replace('https://', '')
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        auth_url = f'https://{basic_auth["id"]}:{basic_auth["password"]}@{base_url}/login'
        
        self.driver.get(auth_url)
        time.sleep(2)

        # ログインフォームの入力
        username_field = self._get_element('login', 'username')
        username_field.send_keys(login_credentials['id'])
        time.sleep(1)
        
        password_field = self._get_element('login', 'password')
        password_field.send_keys(login_credentials['password'])
        time.sleep(1)
        
        submit_button = self._get_element('login', 'submit_button')
        submit_button.click()
        time.sleep(3)

    def go_to_adoptions(self, test_mode=False):
        """応募者一覧ページへ遷移"""
        try:
            # 検索条件を含むURLを構築
            base_params = {
                's[order]': '1',
                'c[submit_status_enum]': '2',
                'c[admin_check_flag]': 'false'
            }
            
            # URLパラメータの構築
            params = '&'.join([f'{k}={v}' for k, v in base_params.items()])
            search_url = f"{self.settings.get('URL', 'base_url')}/admin/adoptions?{params}&commit=検索"
            
            print(f"DEBUG: 応募者一覧ページへ遷移: {search_url}")
            self.driver.get(search_url)
            
            # 要素が読み込まれるまで待機
            self.wait.until(EC.presence_of_all_elements_located)
            time.sleep(1)
            
            print("応募者一覧ページへの遷移完了")
            return True
            
        except Exception as e:
            print(f"応募者一覧ページへの遷移でエラー: {str(e)}")
            return False

    def get_page_title(self):
        """ページタイトルを取得"""
        try:
            print("DEBUG: ページタイトルの取得を試みます")
            title_element = self._get_element('top', 'page_title')
            title_text = title_element.text
            print(f"DEBUG: 取得したタイトル = {title_text}")
            return title_text
        except Exception as e:
            print(f"DEBUG: タイトル取得でエラー: {str(e)}")
            print(f"DEBUG: 現在のページソース: {self.driver.page_source[:500]}")
            raise

    def get_page_heading(self):
        """ページ見出しを取得"""
        try:
            print("DEBUG: ページ見出しの取得を試みます")
            heading_element = self._get_element('top', 'page_heading')
            heading_text = heading_element.text
            print(f"DEBUG: 取得した見出し = {heading_text}")
            return heading_text
        except Exception as e:
            print(f"DEBUG: 見出し取得でエラー: {str(e)}")
            print(f"DEBUG: 現在のURL = {self.driver.current_url}")
            print(f"DEBUG: 現在のページソース: {self.driver.page_source[:500]}")
            raise

    def quit(self):
        """ブラウザを終了"""
        if self.driver:
            self.driver.quit()

    def search_applicants(self, selectors):
        """
        絞込条件を設定して検索を実行
        """
        try:
            print("検索条件を設定中...")
            
            # 提出ステータスを設定
            submit_status = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    selectors['submit_status']['selector_value']
                ))
            )
            status_value = EnvironmentUtils.get_config_value('SEARCH', 'submit_status', '0')
            if status_value != "0":
                Select(submit_status).select_by_value(status_value)
            
            # 提出期限を設定
            deadline_value = EnvironmentUtils.get_config_value('SEARCH', 'submit_deadline', '')
            if deadline_value:
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    selectors['submit_deadline']['selector_value']
                ).click()
                
            # 検索ボタンをクリック
            search_button = self.driver.find_element(
                By.CSS_SELECTOR,
                selectors['search_button']['selector_value']
            )
            search_button.click()
            
            # 要素が読み込まれるまで待機
            self.wait.until(EC.presence_of_all_elements_located)
            time.sleep(1)
            
            print("✅ 検索完了")
            return True
            
        except Exception as e:
            print(f"❌ 検索処理でエラー: {str(e)}")
            return False

    def go_to_adoptions_and_search(self, test_mode=False):
        """
        採用確認ページに遷移して検索条件で絞り込みを実行
        """
        try:
            # まず採用確認ページへ遷移
            if not self.go_to_adoptions(test_mode):
                return False
            
            # 検索条件を設定して検索実行
            if not self.search_applicants(self.selectors['adoption']):
                return False
            
            print("✅ 採用確認ページの遷移と検索が完了しました")
            return True
            
        except Exception as e:
            print(f"❌ 採用確認ページの遷移と検索でエラー: {str(e)}")
            return False

    def process_applicants(self, checker, env):
        """
        応募者データの処理を実行
        
        Args:
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            
        Returns:
            list: 処理した応募者データのリスト
        """
        applicants_to_log = []
        
        try:
            # 採用確認処理
            print("\n=== 採用確認処理開始 ===")
            # セレクター情報をcheckerから取得
            selectors = checker.get_selectors()
            adoption = Adoption(self, selectors, checker=checker, env=env)
            
            # 検索結果の確認
            has_data, record_count = adoption.check_search_results()
            if not has_data:
                print("処理対象のデータがありません")
                return []

            # テーブルの取得
            table = self.wait.until(
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
            return applicants_to_log

        except Exception as e:
            print(f"❌ 応募者データの処理でエラー: {str(e)}")
            return [] 