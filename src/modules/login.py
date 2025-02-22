from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os

class Login:
    def __init__(self, browser):
        """
        ログイン機能を管理するクラス
        
        Args:
            browser: Browserクラスのインスタンス
        """
        self.browser = browser
        
    def execute(self):
        """
        ログイン処理を実行
        
        Returns:
            tuple: (bool, str) - (ログイン成功フラグ, 管理画面のURL)
        """
        try:
            # 環境変数からログイン情報を取得
            url = os.getenv('ADMIN_URL')
            if not url:
                raise ValueError("ADMIN_URLが設定されていません")

            basic_auth = {
                'id': os.getenv('BASIC_AUTH_ID'),
                'password': os.getenv('BASIC_AUTH_PASSWORD')
            }
            if not all(basic_auth.values()):
                raise ValueError("Basic認証情報が不完全です")

            login_credentials = {
                'id': os.getenv('LOGIN_ID'),
                'password': os.getenv('LOGIN_PASSWORD')
            }
            if not all(login_credentials.values()):
                raise ValueError("ログイン認証情報が不完全です")

            # ログイン実行
            base_url = url.replace('https://', '')
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            auth_url = f'https://{basic_auth["id"]}:{basic_auth["password"]}@{base_url}/login'
            
            self.browser.driver.get(auth_url)
            time.sleep(2)

            # ログインフォームの入力
            print("ユーザー名を入力中...")
            username_field = self.browser.wait.until(
                EC.element_to_be_clickable((
                    getattr(By, self.browser.selectors['login']['username']['type'].upper()),
                    self.browser.selectors['login']['username']['value']
                ))
            )
            username_field.clear()  # 既存の入力をクリア
            username_field.send_keys(login_credentials['id'])
            time.sleep(1)

            print("パスワードを入力中...")
            password_field = self.browser.wait.until(
                EC.element_to_be_clickable((
                    getattr(By, self.browser.selectors['login']['password']['type'].upper()),
                    self.browser.selectors['login']['password']['value']
                ))
            )
            password_field.clear()  # 既存の入力をクリア
            password_field.send_keys(login_credentials['password'])
            time.sleep(1)

            print("ログインボタンをクリック...")
            submit_button = self.browser.wait.until(
                EC.element_to_be_clickable((
                    getattr(By, self.browser.selectors['login']['submit_button']['type'].upper()),
                    self.browser.selectors['login']['submit_button']['value']
                ))
            )
            submit_button.click()
            time.sleep(3)

            # ログイン成功の確認
            try:
                heading = self.browser.wait.until(
                    EC.presence_of_element_located((
                        getattr(By, self.browser.selectors['top']['page_heading']['type'].upper()),
                        self.browser.selectors['top']['page_heading']['value']
                    ))
                ).text
                print(f"✅ ログイン成功 - ページ見出し: {heading}")
                return True, url  # URLも返す
            except Exception as e:
                print(f"⚠️ ページ見出しの取得に失敗: {str(e)}")
                raise Exception("ログイン後の画面確認に失敗しました")

        except Exception as e:
            print(f"❌ ログイン処理でエラー: {str(e)}")
            return False, None 