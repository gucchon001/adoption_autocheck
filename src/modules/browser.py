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
from ..utils.logging_config import get_logger

class Browser:
    def __init__(self, settings_path='config/settings.ini', selectors_path='config/selectors.csv'):
        self.driver = None
        self.settings = self._load_settings(settings_path)
        self.selectors = self._load_selectors(selectors_path)
        self.wait = None
        self.logger = get_logger(__name__)

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
                if changes_made:  # auto_updateに関わらず更新ボタンをクリック
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
                                    
                                    # auto_update = true の場合は検索ボタンをクリックしない
                                    # 次のループで同じページを再処理
                                    continue
                                except Exception as e:
                                    # 閉じるボタンが表示されない場合は無視
                                    self.logger.info(f"閉じるボタンは表示されませんでした: {str(e)}")
                        
                        except Exception as e:
                            # 確認ダイアログが表示されない場合は無視
                            self.logger.info(f"確認ダイアログは表示されませんでした: {str(e)}")
                        
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
                                    
                                    # 検索ボタンをクリック
                                    try:
                                        search_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
                                        for btn in search_buttons:
                                            if "検索" in btn.text and btn.is_displayed():
                                                self.driver.execute_script("arguments[0].click();", btn)
                                                self.logger.info("検索ボタンをクリックしました")
                                                time.sleep(2)
                                                continue
                                    except:
                                        pass
                        except Exception as recovery_error:
                            self.logger.error(f"リカバリー処理でもエラー: {str(recovery_error)}")
                
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

            self.logger.info(f"✅ 全{len(applicants_to_log)}件の処理が完了しました")
            return all_processed_applicants

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

    def click_checkbox(self, row, selector, max_retries=3):
        """
        JavaScriptを使用してチェックボックスをクリックする
        
        Args:
            row: テーブルの行要素
            selector: チェックボックスのセレクター
            max_retries: 最大リトライ回数
            
        Returns:
            bool: クリックに成功した場合はTrue、失敗した場合はFalse
        """
        for attempt in range(max_retries):
            try:
                # チェックボックスを取得
                checkbox = row.find_element(By.CSS_SELECTOR, selector)
                
                # 現在の状態を確認（チェック済みかどうか）
                is_checked = False
                try:
                    # 標準的なチェックボックスの場合
                    is_checked = checkbox.is_selected()
                except:
                    # カスタムチェックボックスの場合、クラス名やdata属性で判断を試みる
                    try:
                        is_checked = ('checked' in checkbox.get_attribute('class') or 
                                     checkbox.get_attribute('data-checked') == 'true' or
                                     checkbox.get_attribute('aria-checked') == 'true')
                    except:
                        # 属性の取得に失敗した場合は未チェックと仮定
                        is_checked = False
                
                # 既にチェック済みの場合は成功として返す
                if is_checked:
                    self.logger.info("✅ チェックボックスは既にONになっています")
                    return True
                
                # 要素が見えるようにスクロール（中央に配置）
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    checkbox
                )
                time.sleep(1.5)  # スクロールとレンダリングが完了するまで待機
                
                # JavaScriptを使用してクリック
                self.driver.execute_script("arguments[0].click();", checkbox)
                time.sleep(1)  # クリック後の状態変化を待機
                
                # クリック後の状態を確認
                try:
                    # 標準的なチェックボックスの場合
                    is_checked_after = checkbox.is_selected()
                except:
                    # カスタムチェックボックスの場合
                    try:
                        is_checked_after = ('checked' in checkbox.get_attribute('class') or 
                                           checkbox.get_attribute('data-checked') == 'true' or
                                           checkbox.get_attribute('aria-checked') == 'true')
                    except:
                        # 属性の取得に失敗した場合は、クリックは成功したと仮定
                        is_checked_after = True
                
                if is_checked_after:
                    self.logger.info(f"✅ 確認完了チェックボックスをONに設定しました (試行回数: {attempt+1})")
                    return True
                else:
                    # チェックボックスが選択されていない場合は、もう一度試行
                    self.logger.warning(f"チェックボックスがONになっていません。再試行します... (試行回数: {attempt+1})")
                    continue
                    
            except Exception as e:
                self.logger.warning(f"❌ チェックボックスの操作に失敗 (試行回数: {attempt+1}): {str(e)}")
                
                if attempt < max_retries - 1:
                    # 別のスクロール方法を試す
                    try:
                        # 1. 少し上にスクロールしてから再試行
                        self.driver.execute_script("window.scrollBy(0, -100);")
                        time.sleep(1)
                        
                        # 2. 要素の親要素を取得して、そこにスクロール
                        parent_row = row.find_element(By.XPATH, "./..")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", parent_row)
                        time.sleep(1)
                        
                        # 3. 画面の中央に強制的にスクロール
                        viewport_height = self.driver.execute_script("return window.innerHeight")
                        element_y = self.driver.execute_script("return arguments[0].getBoundingClientRect().top", row)
                        scroll_y = element_y - viewport_height / 2
                        self.driver.execute_script(f"window.scrollBy(0, {scroll_y});")
                        time.sleep(1.5)
                    except Exception:
                        # スクロールに失敗しても続行
                        pass
                    
                    self.logger.info(f"リトライします... ({attempt+1}/{max_retries})")
                    time.sleep(2)  # リトライ前に少し待機
                else:
                    self.logger.error(f"❌ チェックボックスの操作に失敗しました (最大試行回数に達しました): {str(e)}")
                    return False
        
        # 最大リトライ回数に達しても成功しなかった場合
        return False 