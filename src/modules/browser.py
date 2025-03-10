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
from ..utils.environment import EnvironmentUtils as env
from .adoption import Adoption
from ..utils.logging_config import get_logger
import traceback

class Browser:
    def __init__(self, settings_path='config/settings.ini', selectors_path='config/selectors.csv'):
        self.driver = None
        self.settings = self._load_settings(settings_path)
        self.selectors = self._load_selectors(selectors_path)
        self.wait = None
        self.logger = get_logger(__name__)
        self.env = env()  # 環境ユーティリティのインスタンスを作成
        self.logger_instance = None  # ロガーインスタンスの初期化

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
                'selector_value': row['selector_value']
            }
        return selectors

    def _get_element(self, page, element, wait=30):
        """指定された要素を取得"""
        selector = self.selectors[page][element]
        by_type = getattr(By, selector['type'].upper())
        return WebDriverWait(self.driver, wait).until(
            EC.visibility_of_element_located((by_type, selector['selector_value']))
        )

    def setup(self):
        """ChromeDriverのセットアップ"""
        self.logger.info("ブラウザのセットアップを開始")
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
            # 基本的なURLパラメータのみ設定
            base_params = {
                's[order]': '1',
                'c[admin_check_flag]': 'false'
            }
            
            # URLパラメータの構築
            params = '&'.join([f'{k}={v}' for k, v in base_params.items()])
            search_url = f"{self.settings.get('URL', 'base_url')}/admin/adoptions?{params}"
            
            print(f"DEBUG: 応募者一覧ページへ遷移: {search_url}")
            self.driver.get(search_url)
            
            # 要素が読み込まれるまで待機
            self.wait.until(EC.presence_of_all_elements_located)
            time.sleep(2)
            
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
        検索条件を設定して検索を実行
        
        Args:
            selectors: セレクター情報
            
        Returns:
            bool: 検索に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            self.logger.info("4. 検索条件の設定...")
            
            # 提出ステータスの設定
            submit_status = self.env.get_config_value('SEARCH', 'submit_status', 0)
            if submit_status > 0:
                submit_status_select = Select(self.driver.find_element(
                    By.CSS_SELECTOR, 
                    selectors['submit_status']['selector_value']
                ))
                submit_status_select.select_by_value(str(submit_status))
                self.logger.info("✅ 提出ステータスを設定しました")
            
            # 提出期限の設定
            submit_deadline = self.env.get_config_value('SEARCH', 'submit_deadline', 0)
            submit_deadline_select = Select(self.driver.find_element(
                By.CSS_SELECTOR, 
                selectors['submit_deadline']['selector_value']
            ))
            submit_deadline_select.select_by_value(str(submit_deadline))
            self.logger.info(f"✅ 提出期限を設定しました（値: {submit_deadline_select.first_selected_option.text}）")
            
            # 検索ボタンをクリック
            try:
                search_button = self.driver.find_element(
                    By.CSS_SELECTOR,
                    selectors['search_button']['selector_value']
                )
                
                # 検索ボタンが見えるようにスクロール
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    search_button
                )
                time.sleep(1.5)  # スクロールが完了するまで待機
                
                # JavaScriptを使用してクリック
                self.driver.execute_script("arguments[0].click();", search_button)
                self.logger.info("✅ 検索ボタンをクリックしました")
                
                # 検索結果の読み込みを待機
                time.sleep(3)
                
                return True
                
            except Exception as e:
                self.logger.error(f"❌ 検索ボタンのクリックでエラー: {str(e)}")
                
                # 別の方法を試す
                try:
                    # 1. フォームを直接送信
                    self.logger.info("別の方法で検索を実行します（フォーム送信）")
                    self.driver.execute_script("""
                        document.querySelector('form').submit();
                    """)
                    time.sleep(3)
                    return True
                except Exception as e2:
                    self.logger.error(f"❌ フォーム送信でもエラー: {str(e2)}")
                    return False
            
        except Exception as e:
            self.logger.error(f"❌ 検索条件の設定でエラー: {str(e)}")
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

    def process_applicants(self, checker, env, process_next_page=True):
        """
        応募者データの処理を実行
        
        Args:
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            process_next_page: 次ページも処理するかどうか
            
        Returns:
            list: 処理した応募者データのリスト
        """
        all_processed_applicants = []
        
        try:
            # 採用確認処理
            self.logger.info("=== 採用確認処理開始 ===")
            
            # セレクター情報をcheckerから取得
            selectors = checker.get_selectors()
            adoption = Adoption(self, selectors, checker=checker, env=env)
            
            # 処理方法の設定を取得
            process_by_id = env.get_config_value('BROWSER', 'process_by_id', False)
            
            if process_by_id:
                # 応募IDごとに処理する方法
                return self._process_by_application_id(checker, env, adoption, process_next_page)
            else:
                # 従来の方法（一括処理）
                return self._process_by_batch(checker, env, adoption, process_next_page)
            
        except Exception as e:
            self.logger.error(f"❌ 応募者データの処理でエラー: {str(e)}")
            return []

    def go_to_next_page(self):
        """
        次のページに移動する
        
        Returns:
            bool: 次のページに移動できた場合はTrue、それ以外はFalse
        """
        try:
            # 次ページボタンを取得
            try:
                next_page_button = self._get_element('adoption', 'next_page_button', wait=5)
            except Exception as e:
                self.logger.info(f"次ページボタンが見つかりません: {str(e)}")
                return False
            
            # 次ページボタンが無効化されているか確認
            parent_li = next_page_button.find_element(By.XPATH, "./..")
            if 'disabled' in parent_li.get_attribute('class'):
                self.logger.info("次ページボタンが無効化されています。")
                return False
            
            # 次ページボタンをクリック
            next_page_button.click()
            
            # モーダルダイアログが表示された場合は確認ボタンをクリック
            try:
                confirm_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#modal-confirm_change_page button.btn-primary"))
                )
                confirm_button.click()
            except Exception:
                # モーダルが表示されない場合は無視
                pass
            
            self.logger.info("次のページに移動しました")
            time.sleep(2)  # ページ読み込みを待機
            return True
            
        except Exception as e:
            self.logger.error(f"次ページへの移動でエラー: {str(e)}")
            return False

    def click_checkbox(self, row_element, selector_value, max_retries=3):
        """
        チェックボックスをクリックする
        
        Args:
            row_element: 行要素
            selector_value: セレクター値
            max_retries: 最大リトライ回数
            
        Returns:
            bool: クリックに成功した場合はTrue、失敗した場合はFalse
        """
        for attempt in range(max_retries):
            try:
                # チェックボックスを見つける
                checkbox = row_element.find_element(By.CSS_SELECTOR, selector_value)
                
                # チェックボックスが見えるようにスクロール
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    checkbox
                )
                time.sleep(1)  # スクロールが完了するまで待機
                
                # JavaScriptを使用してクリック
                self.driver.execute_script("arguments[0].click();", checkbox)
                time.sleep(1)  # クリック後の処理が完了するまで待機
                
                return True
                
            except Exception as e:
                self.logger.warning(f"❌ チェックボックスの操作に失敗 (試行回数: {attempt + 1}): {str(e)}")
                
                # 最後の試行でなければ少し待ってリトライ
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False

    def _process_by_application_id(self, checker, env, adoption, process_next_page=True):
        """
        応募IDごとに処理
        
        Args:
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            adoption: Adoptionクラスのインスタンス
            process_next_page: 次ページも処理するかどうか
            
        Returns:
            list: 処理した応募者データのリスト
        """
        all_processed_applicants = []  # 処理した応募者データを格納するリスト
        
        try:
            # 現在のページ番号を追跡
            current_page = 1
            
            # 処理を続ける限りループ
            while True:
                self.logger.info(f"=== ページ {current_page} の処理を開始 ===")
                
                # ステップ1: 現在のページからチェック対象の応募IDを収集
                application_ids = self._collect_application_ids(checker, adoption)
                
                # チェック対象の応募IDがない場合
                if not application_ids:
                    self.logger.info(f"ページ {current_page} にはチェック対象の応募IDがありません")
                    
                    # 次のページに移動（process_next_pageがTrueの場合のみ）
                    if process_next_page and self.go_to_next_page():
                        current_page += 1
                        continue
                    else:
                        self.logger.info("次のページはありません。処理を終了します。")
                        break
                
                # ステップ2: 収集した応募IDを一つずつ処理
                for app_id in application_ids:
                    self._process_single_application_id(app_id, checker, env, adoption)
                
                # ステップ3: 初期検索条件に戻る（応募IDを指定せずに検索）
                if not self._search_by_application_id():
                    self.logger.warning("初期検索条件への復帰に失敗しました")
                    break
                
                # ステップ4: 現在のページに戻る（必要に応じて）
                if current_page > 1:
                    self.logger.info(f"ページ {current_page} に戻ります")
                    # 現在のページまでページネーションを実行
                    for i in range(1, current_page):
                        if not self.go_to_next_page():
                            self.logger.warning(f"ページ {current_page} への移動に失敗しました")
                            break
                
                # ステップ5: 同じページを再確認（処理済みの応募IDは should_check で除外される）
                self.logger.info(f"ページ {current_page} を再確認します")
                
                # 検索結果の確認
                has_data, record_count = adoption.check_search_results()
                if not has_data:
                    self.logger.info("処理対象のデータがありません")
                    break
            
            self.logger.info(f"✅ 全ての処理が完了しました")
            return all_processed_applicants
            
        except Exception as e:
            self.logger.error(f"❌ 応募IDごとの処理でエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return all_processed_applicants

    def _collect_application_ids(self, checker, adoption):
        """
        現在のページからチェック対象の応募IDを収集
        
        Args:
            checker: ApplicantCheckerクラスのインスタンス
            adoption: Adoptionクラスのインスタンス
            
        Returns:
            list: 収集した応募IDのリスト
        """
        try:
            # 検索結果の確認
            has_data, record_count = adoption.check_search_results()
            if not has_data:
                self.logger.info("処理対象のデータがありません")
                return []
            
            # テーブルの取得
            table = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#recruitment-list table.table-sm"
                ))
            )
            rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            
            # 処理対象の応募IDを収集
            application_ids = []
            
            for record_index in range(record_count):
                try:
                    # get_applicant_info メソッドを使用して応募者データを取得（チェックボックスはクリックしない）
                    applicant_data = adoption.get_applicant_info(rows, record_index)
                    
                    # 応募者データが取得できた場合
                    if applicant_data and 'status' in applicant_data:
                        # パターン判定を行う
                        pattern, reason = checker.check_pattern(applicant_data)
                        
                        # パターン1〜4が対象
                        should_check = 1 <= pattern <= 4
                        
                        if should_check:
                            app_id = applicant_data.get('application_id')
                            if app_id:
                                application_ids.append(app_id)
                                self.logger.info(f"チェック対象の応募ID: {app_id} を追加しました (パターン{pattern}: {reason})")
                except Exception as e:
                    self.logger.error(f"レコード {record_index} の処理でエラー: {str(e)}")
                    traceback.print_exc()  # スタックトレースを出力
                    continue
            
            return application_ids
            
        except Exception as e:
            self.logger.error(f"❌ 応募ID収集でエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return []

    def _process_single_application_id(self, app_id, checker, env, adoption):
        """
        単一の応募IDを処理
        
        Args:
            app_id: 処理する応募ID
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            adoption: Adoptionクラスのインスタンス
            
        Returns:
            bool: 処理に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            self.logger.info(f"応募ID: {app_id} の処理を開始")
            
            # 応募IDで検索
            if not self._search_by_application_id(app_id):
                self.logger.warning(f"応募ID: {app_id} の検索に失敗しました")
                return False
            
            # 検索結果の確認
            has_data, record_count = adoption.check_search_results()
            if not has_data or record_count == 0:
                self.logger.warning(f"応募ID: {app_id} の検索結果がありません")
                return False
            
            # テーブルの取得
            table = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#recruitment-list table.table-sm"
                ))
            )
            rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            
            # 応募者データを取得（チェックボックスはまだクリックしない）
            applicant_data = adoption.get_applicant_info(rows, 0)
            if not applicant_data:
                self.logger.warning(f"応募ID: {app_id} のデータ取得に失敗しました")
                return False
            
            # パターン判定を行う
            pattern, reason = checker.check_pattern(applicant_data)
            applicant_data['pattern'] = str(pattern)
            applicant_data['remark'] = reason
            
            # チェックボックスをクリック
            if not adoption.check_single_record(rows, 0):
                self.logger.warning(f"応募ID: {app_id} のチェックに失敗しました")
                return False
            
            # チェックボックスがクリックされたことを記録
            applicant_data['confirm_checkbox'] = 'チェック'
            
            # 更新ボタンをクリック
            auto_update = env.get_config_value('BROWSER', 'auto_update', False)
            if not self._click_update_button(auto_update):
                self.logger.warning(f"応募ID: {app_id} の更新に失敗しました")
                return False
            
            # 更新状態を記録
            applicant_data['confirm_onoff'] = '更新' if auto_update else '更新キャンセル'
            
            # IDキーの統一（application_id → id）
            if 'application_id' in applicant_data and 'id' not in applicant_data:
                applicant_data['id'] = applicant_data['application_id']
            
            # ログに記録
            if hasattr(self, 'logger_instance') and self.logger_instance:
                try:
                    log_success = self.logger_instance.log_applicants([applicant_data])
                    if log_success:
                        self.logger.info(f"応募ID: {app_id} のデータをログに記録しました")
                    else:
                        self.logger.warning(f"応募ID: {app_id} のデータのログ記録に失敗しました")
                except Exception as log_error:
                    self.logger.error(f"ログ記録中にエラーが発生: {str(log_error)}")
            
            self.logger.info(f"応募ID: {app_id} の処理が完了しました")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 応募ID: {app_id} の処理でエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return False

    def _search_by_application_id(self, application_id=None):
        """
        応募IDで検索を実行
        
        Args:
            application_id: 検索する応募ID（Noneの場合は空で検索）
            
        Returns:
            bool: 検索に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            if application_id:
                self.logger.info(f"応募ID: {application_id} で検索します")
            else:
                self.logger.info("応募IDを指定せずに検索します")
            
            # 検索フォームをクリア
            try:
                # 応募IDフィールドをクリア
                application_id_field = self.driver.find_element(By.CSS_SELECTOR, "#application_number")
                application_id_field.clear()
                time.sleep(0.5)
                
                # 応募IDを入力（指定がある場合のみ）
                if application_id:
                    application_id_field.send_keys(str(application_id))
                    time.sleep(0.5)
                
                # 検索ボタンをクリック
                search_button = self.driver.find_element(
                    By.CSS_SELECTOR,
                    self.selectors['adoption']['search_button']['selector_value']
                )
                
                # 検索ボタンが見えるようにスクロール
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    search_button
                )
                time.sleep(1.5)  # スクロールが完了するまで待機
                
                # JavaScriptを使用してクリック
                self.driver.execute_script("arguments[0].click();", search_button)
                
                # 要素が読み込まれるまで待機
                self.wait.until(EC.presence_of_all_elements_located)
                time.sleep(2)
                
                if application_id:
                    self.logger.info(f"応募ID: {application_id} の検索が完了しました")
                else:
                    self.logger.info("応募IDを指定せずに検索が完了しました")
                return True
                
            except Exception as e:
                self.logger.error(f"応募ID検索でエラー: {str(e)}")
                
                # 別の方法を試す
                try:
                    # フォームを直接送信
                    self.logger.info("別の方法で検索を実行します（フォーム送信）")
                    self.driver.execute_script("""
                        document.querySelector('form').submit();
                    """)
                    time.sleep(3)
                    return True
                except Exception as e2:
                    self.logger.error(f"❌ フォーム送信でもエラー: {str(e2)}")
                    return False
                
        except Exception as e:
            self.logger.error(f"応募ID検索処理でエラー: {str(e)}")
            return False

    def _click_update_button(self, auto_update):
        """
        更新ボタンをクリックする
        
        Args:
            auto_update: 更新を確定するかどうか
            
        Returns:
            bool: 更新に成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 更新ボタンのセレクターを取得
            update_button_selector = self.selectors['adoption']['update_button']['selector_value']
            
            # 更新ボタンを見つける
            update_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, update_button_selector))
            )
            
            # 更新ボタンが見えるようにスクロール
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                update_button
            )
            time.sleep(1.5)  # スクロールが完了するまで待機
            
            # JavaScriptを使用してクリック
            self.driver.execute_script("arguments[0].click();", update_button)
            self.logger.info("更新ボタンをクリックしました")
            time.sleep(2)  # 更新処理の完了を待機
            
            # 確認ダイアログが表示された場合は確認/キャンセルボタンをクリック
            try:
                if auto_update:
                    # 更新確定ボタンをクリック
                    confirm_button_selector = self.selectors['adoption']['update_confirm_button']['selector_value']
                else:
                    # 更新キャンセルボタンをクリック
                    confirm_button_selector = self.selectors['adoption']['update_cancel_button']['selector_value']
                    
                confirm_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_button_selector))
                )
                
                # JavaScriptを使用してクリック
                self.driver.execute_script("arguments[0].click();", confirm_button)
                self.logger.info(f"{'更新確定' if auto_update else '更新キャンセル'}ボタンをクリックしました")
                time.sleep(3)  # 確認処理の完了を待機
                
                # 更新確定後に「閉じる」ボタンが表示される場合があるので対応
                if auto_update:
                    try:
                        close_button_selector = self.selectors['adoption']['close_button']['selector_value']
                        close_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, close_button_selector))
                        )
                        
                        # JavaScriptを使用してクリック
                        self.driver.execute_script("arguments[0].click();", close_button)
                        self.logger.info("閉じるボタンをクリックしました")
                        time.sleep(2)  # 閉じる処理の完了を待機
                    except Exception as e:
                        # 閉じるボタンが表示されない場合は無視
                        self.logger.info(f"閉じるボタンは表示されませんでした: {str(e)}")
            
            except Exception as e:
                # 確認ダイアログが表示されない場合は無視
                self.logger.info(f"確認ダイアログは表示されませんでした: {str(e)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"更新ボタンのクリックでエラー: {str(e)}")
            
            # 別の方法を試す
            try:
                # 1. 別のセレクターを試す
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn-primary")
                for button in buttons:
                    if "更新" in button.text:
                        self.driver.execute_script("arguments[0].click();", button)
                        self.logger.info("テキストで特定した更新ボタンをクリックしました")
                        time.sleep(2)
                        
                        # 確認ダイアログが表示された場合
                        try:
                            if auto_update:
                                # 更新確定ボタンを探す
                                confirm_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".modal-footer .btn-primary")
                            else:
                                # 更新キャンセルボタンを探す
                                confirm_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".modal-footer .btn-secondary")
                            
                            for btn in confirm_buttons:
                                if btn.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", btn)
                                    self.logger.info(f"{'更新確定' if auto_update else '更新キャンセル'}ボタンをクリックしました")
                                    time.sleep(2)
                                    break
                        
                        except:
                            pass
                        
                        return True
            except Exception as recovery_error:
                self.logger.error(f"リカバリー処理でもエラー: {str(recovery_error)}")
                return False 

    def _process_by_batch(self, checker, env, adoption, process_next_page=True):
        """
        従来の一括処理方法
        
        Args:
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            adoption: Adoptionクラスのインスタンス
            process_next_page: 次ページも処理するかどうか
            
        Returns:
            list: 処理した応募者データのリスト
        """
        all_processed_applicants = []
        
        try:
            # 同一ページで処理を繰り返すフラグ
            repeat_same_page = True
            
            while repeat_same_page:
                # 検索結果の確認
                has_data, record_count = adoption.check_search_results()
                if not has_data:
                    self.logger.info("処理対象のデータがありません")
                    return all_processed_applicants
                
                # テーブルの取得
                table = self.wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR, 
                        "#recruitment-list table.table-sm"
                    ))
                )
                rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
                
                # 変更があったかどうかのフラグ
                changes_made = False
                
                # 現在のページの応募者データを処理
                applicants_to_log = []
                for record_index in range(record_count):
                    applicant_data = adoption.process_record(rows, record_index)
                    if applicant_data:
                        applicants_to_log.append(applicant_data)
                        # チェックボックスがクリックされたかどうかを確認
                        if applicant_data.get('confirm_checkbox') == 'チェック':
                            changes_made = True
                
                # 処理した応募者データを記録
                all_processed_applicants.extend(applicants_to_log)
                
                # 変更があった場合のみ更新ボタンをクリック
                auto_update = env.get_config_value('BROWSER', 'auto_update', False)
                if changes_made:
                    if not self._click_update_button(auto_update):
                        self.logger.warning("更新ボタンのクリックに失敗しました")
                    
                    # auto_update = false の場合のみ検索ボタンをクリック
                    if not auto_update:
                        try:
                            # 検索ボタンをクリック
                            search_button_selector = self.selectors['adoption']['search_button']['selector_value']
                            search_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, search_button_selector))
                            )
                            
                            # JavaScriptを使用してクリック
                            self.driver.execute_script("arguments[0].click();", search_button)
                            self.logger.info("検索ボタンをクリックして同じページを再読み込みしました")
                            time.sleep(3)  # 検索処理の完了を待機
                        except Exception as e:
                            self.logger.error(f"検索ボタンのクリックでエラー: {str(e)}")
                            # エラーが発生しても処理を続行
                
                # 変更がなかった場合、または更新後の再検索が完了した場合は同一ページの繰り返し処理を終了
                repeat_same_page = False
                
                # 次のページに移動（process_next_pageがTrueの場合のみ）
                if process_next_page:
                    # go_to_next_pageメソッドを使用して次ページに移動
                    if self.go_to_next_page():
                        # 再帰的に次のページを処理
                        next_page_applicants = self.process_applicants(checker, env, process_next_page)
                        all_processed_applicants.extend(next_page_applicants)
                    else:
                        self.logger.info("次のページはありません。処理を終了します。")
                
                self.logger.info(f"✅ 全{len(all_processed_applicants)}件の処理が完了しました")
                return all_processed_applicants
                
        except Exception as e:
            self.logger.error(f"❌ 応募者データの一括処理でエラー: {str(e)}")
            return all_processed_applicants 