from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from ..utils.environment import EnvironmentUtils as env
import time

class Search:
    def __init__(self, browser, selectors):
        """
        検索機能を管理するクラス
        
        Args:
            browser: Browserクラスのインスタンス
            selectors: セレクター情報
        """
        self.browser = browser
        self.selectors = selectors

    def execute(self):
        """
        検索処理を実行
        
        Returns:
            bool: 検索成功時True、失敗時False
        """
        try:
            # 検索条件の設定と検索実行をテスト
            print("\n4. 検索条件の設定...")
            
            # ページが完全に読み込まれるまで待機
            self.browser.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#form_search"
                ))
            )
            time.sleep(1)

            # 提出ステータスの設定
            if not self._set_submit_status():
                return False

            # 提出期限の設定
            if not self._set_submit_deadline():
                return False

            # 検索ボタンクリック
            if not self._click_search_button():
                return False

            return True

        except Exception as e:
            print(f"❌ 検索処理でエラー: {str(e)}")
            return False

    def _set_submit_status(self):
        """提出ステータスを設定"""
        try:
            # ページが完全に読み込まれるまで待機
            self.browser.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "input[name='submission_status']"
                ))
            )
            time.sleep(1)

            # JavaScriptを使用して要素をクリック
            radio_button = self.browser.driver.find_element(
                By.CSS_SELECTOR, 
                "input[name='submission_status'][value='2']"
            )
            self.browser.driver.execute_script("arguments[0].click();", radio_button)
            
            print("✅ 提出ステータスを設定しました")
            return True

        except Exception as e:
            print(f"❌ 提出ステータスの設定でエラー: {str(e)}")
            return False

    def _set_submit_deadline(self):
        """提出期限を設定"""
        try:
            deadline_value = env.get_config_value('SEARCH', 'submit_deadline', '')
            cleaned_deadline = deadline_value.strip('"')

            if cleaned_deadline:
                selector_type = self.selectors['submit_deadline']['selector_type'].upper()
                selector_value = self.selectors['submit_deadline']['selector_value']
                
                if cleaned_deadline != "":
                    selector_value = f"{selector_value}[value='{cleaned_deadline}']"
                
                submit_deadline = self.browser.wait.until(
                    EC.element_to_be_clickable((
                        getattr(By, selector_type),
                        selector_value
                    ))
                )
                submit_deadline.click()
                
                deadline_text = {
                    1: "今月末",
                    2: "期限超過"
                }.get(cleaned_deadline, "不明")
                print(f"✅ 提出期限を設定: {deadline_text}")
            else:
                print("✅ 提出期限: 指定なし")

            return True

        except Exception as e:
            print(f"❌ 提出期限の設定でエラー: {str(e)}")
            return False

    def _click_search_button(self):
        """検索ボタンをクリック"""
        try:
            selector_type = self.selectors['search_button']['selector_type'].upper()
            selector_value = self.selectors['search_button']['selector_value']
            
            # フォーム検索の完了を待機
            self.browser.wait.until(
                EC.presence_of_element_located((
                    getattr(By, selector_type),
                    "#form_search"
                ))
            )
            
            # 検索ボタンが操作可能になるまで待機
            search_button = self.browser.wait.until(
                EC.element_to_be_clickable((
                    getattr(By, selector_type),
                    selector_value
                ))
            )
            search_button.click()
            
            # ローディング表示の消失を待機
            self.browser.wait.until(
                EC.invisibility_of_element_located((
                    getattr(By, selector_type),
                    ".loading"
                ))
            )
            
            # テーブルの再読み込みを待機
            self.browser.wait.until(
                EC.presence_of_element_located((
                    getattr(By, selector_type),
                    "#recruitment-list table.table-sm"
                ))
            )
            print("✅ 検索ボタンをクリックし、結果を読み込み完了")
            return True

        except Exception as e:
            print(f"❌ 検索ボタンのクリックでエラー: {str(e)}")
            return False 