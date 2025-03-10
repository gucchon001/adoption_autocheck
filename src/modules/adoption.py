from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from datetime import datetime
import time
from ..utils.logging_config import get_logger
import traceback

class Adoption:
    def __init__(self, browser, selectors, checker=None, env=None):
        """
        採用確認機能を管理するクラス
        
        Args:
            browser: Browserクラスのインスタンス
            selectors: セレクター情報
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
        """
        self.browser = browser
        self.selectors = selectors
        self.checker = checker
        self.env = env
        self.check_changes_made = False
        self.logger = get_logger(__name__)
        
    def check_search_results(self):
        """
        検索結果を確認
        
        Returns:
            tuple: (bool, int) - (データ有無, レコード数)
        """
        try:
            # テーブルの読み込みを待機
            table = self.browser.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#recruitment-list table.table-sm"
                ))
            )
            time.sleep(2)
            self.logger.info("✅ テーブルの読み込み完了")

            # 検索結果の確認
            try:
                # "該当する採用確認が見つかりませんでした"のメッセージを確認
                no_data_message = table.find_element(
                    By.CSS_SELECTOR, 
                    "tbody tr td[colspan='10']"
                ).text.strip()
                
                if "該当する採用確認が見つかりませんでした" in no_data_message:
                    self.logger.info("検索結果が0件のため、処理を終了します")
                    return False, 0
                    
            except Exception:
                # メッセージが見つからない場合は通常の行数チェックを実行
                rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
                total_rows = len(rows)
                record_count = total_rows // 3
                self.logger.info(f"取得した行数: {total_rows} (レコード数: {record_count})")
                
                if total_rows == 0:
                    self.logger.info("検索結果が0件のため、処理を終了します")
                    return False, 0
                    
                return True, record_count

        except Exception as e:
            self.logger.error(f"❌ 検索結果の確認でエラー: {str(e)}")
            return False, 0

    def process_record(self, rows, record_index):
        """
        1レコード分の情報を処理
        
        Args:
            rows: テーブルの行要素リスト
            record_index: レコードのインデックス
            
        Returns:
            dict: 処理したレコードの情報
        """
        try:
            record_offset = record_index * 3
            self.logger.info(f"\n=== {record_index + 1}レコード目の情報取得とパターン分析 ===")
            
            # データ収集
            applicant_data = {}
            
            # 応募IDを取得
            try:
                selector_type = self.selectors['applicant_id']['selector_type'].upper()
                selector_value = self.selectors['applicant_id']['selector_value']
                applicant_id = rows[record_offset].find_element(
                    getattr(By, selector_type), selector_value
                ).text.strip()
                applicant_data['id'] = applicant_id
                self.logger.info(f"✅ {self.selectors['applicant_id']['description']}: {applicant_id}")
            except Exception as e:
                self.logger.error(f"❌ 応募IDの取得に失敗: {str(e)}")
                return None

            # ステータス取得
            selector_type = self.selectors['status']['selector_type'].upper()
            selector_value = self.selectors['status']['selector_value']
            status_select = Select(rows[record_offset].find_element(
                getattr(By, selector_type), selector_value
            ))
            applicant_data['status'] = status_select.first_selected_option.text
            self.logger.info(f"✅ {self.selectors['status']['description']}: {applicant_data['status']}")
            
            # 研修初日取得
            selector_type = self.selectors['training_start_date']['selector_type'].upper()
            selector_value = self.selectors['training_start_date']['selector_value']
            training_date = rows[record_offset].find_element(
                getattr(By, selector_type), selector_value
            ).text.strip()
            applicant_data['training_start_date'] = training_date
            self.logger.info(f"✅ {self.selectors['training_start_date']['description']}: {training_date}")
            
            # 在籍確認取得
            selector_type = self.selectors['zaiseki_ok']['selector_type'].upper()
            selector_value = self.selectors['zaiseki_ok']['selector_value']
            zaiseki_select = Select(rows[record_offset + 1].find_element(
                getattr(By, selector_type), selector_value
            ))
            applicant_data['zaiseki'] = zaiseki_select.first_selected_option.text
            self.logger.info(f"✅ {self.selectors['zaiseki_ok']['description']}: {applicant_data['zaiseki']}")
            
            # 3行目の要素を取得（お祝い、備考）
            self.logger.info("\n【3行目】")
            for element, key in [('celebration', 'oiwai'), ('remark', 'remark')]:
                if element in self.selectors:
                    try:
                        element_info = self.selectors[element]
                        selector_type = element_info['selector_type'].upper()
                        selector_value = element_info['selector_value']
                        element_obj = rows[record_offset + 2].find_element(
                            getattr(By, selector_type), selector_value
                        )
                        
                        if key == 'remark':
                            value = element_obj.text.strip() if element_obj.text.strip() else ''
                        else:
                            value = element_obj.text if element_info['action_type'] == 'get_text' else ''
                            
                        applicant_data[key] = value
                        self.logger.info(f"✅ {element_info['description']}: {value}")
                    except Exception as e:
                        self.logger.error(f"❌ {element_info['description']}の取得に失敗: {str(e)}")
                        applicant_data[key] = ''

            # パターン判定
            pattern, reason = self.checker.check_pattern(applicant_data)
            self.logger.info(f"\n判定結果: パターン{pattern}")
            self.logger.info(f"判定理由: {reason}")
            
            # パターン情報を追加
            applicant_data['pattern'] = str(pattern)
            applicant_data['confirm_checkbox'] = ''
            applicant_data['confirm_onoff'] = ''

            # パターン99以外の場合の処理
            if pattern != 99:
                # チェックボックスの操作
                selector_type = self.selectors['confirm_checkbox']['selector_type'].upper()
                selector_value = self.selectors['confirm_checkbox']['selector_value']
                
                # browser.pyのclick_checkboxメソッドを使用
                click_success = self.browser.click_checkbox(
                    rows[record_offset + 2], 
                    selector_value, 
                    max_retries=3
                )
                
                if click_success:
                    applicant_data['confirm_checkbox'] = 'チェック'
                    self.check_changes_made = True
                    
                    # auto_updateの設定を取得して更新状態を設定
                    auto_update = self.env.get_config_value('BROWSER', 'auto_update', default=False)
                    applicant_data['confirm_onoff'] = '更新' if auto_update else '更新キャンセル'
                else:
                    applicant_data['confirm_checkbox'] = 'エラー'

            return applicant_data

        except Exception as e:
            self.logger.error(f"❌ レコード処理でエラー: {str(e)}")
            return None

    def get_applicant_info(self, rows, record_index):
        """
        応募者情報のみを取得（チェックはしない）
        
        Args:
            rows: テーブルの行要素のリスト
            record_index: 処理対象のレコードインデックス
            
        Returns:
            dict: 応募者データ
        """
        try:
            # 3行で1レコードなので、インデックスを3倍する
            row_index = record_index * 3
            
            # 行数チェック
            if row_index >= len(rows):
                self.logger.warning(f"指定されたインデックス {record_index} は範囲外です")
                return None
            
            # 1行目（基本情報）
            row1 = rows[row_index]
            # 2行目（在籍確認など）
            row2 = rows[row_index + 1] if row_index + 1 < len(rows) else None
            
            # 応募者情報を取得
            applicant_data = {}
            
            # 応募ID
            try:
                application_id_element = row1.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                application_id = application_id_element.text.strip()
                applicant_data['application_id'] = application_id
            except Exception as e:
                self.logger.warning(f"応募IDの取得に失敗: {str(e)}")
            
            # 応募者名
            try:
                applicant_name_element = row1.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
                applicant_name = applicant_name_element.text.strip()
                applicant_data['applicant_name'] = applicant_name
            except Exception as e:
                self.logger.warning(f"応募者名の取得に失敗: {str(e)}")
            
            # ステータス取得（パターン判定に必要）
            try:
                selector_type = self.selectors['status']['selector_type'].upper()
                selector_value = self.selectors['status']['selector_value']
                status_select = Select(row1.find_element(
                    getattr(By, selector_type), selector_value
                ))
                applicant_data['status'] = status_select.first_selected_option.text
                self.logger.info(f"✅ {self.selectors['status']['description']}: {applicant_data['status']}")
            except Exception as e:
                self.logger.warning(f"ステータスの取得に失敗: {str(e)}")
                applicant_data['status'] = ''
            
            # 研修初日取得（パターン判定に必要）
            try:
                selector_type = self.selectors['training_start_date']['selector_type'].upper()
                selector_value = self.selectors['training_start_date']['selector_value']
                training_date = row1.find_element(
                    getattr(By, selector_type), selector_value
                ).text.strip()
                applicant_data['training_start_date'] = training_date
                self.logger.info(f"✅ {self.selectors['training_start_date']['description']}: {training_date}")
            except Exception as e:
                self.logger.warning(f"研修日の取得に失敗: {str(e)}")
                applicant_data['training_start_date'] = '未定'
            
            # 在籍確認取得（パターン判定に必要）
            if row2:
                try:
                    selector_type = self.selectors['zaiseki_ok']['selector_type'].upper()
                    selector_value = self.selectors['zaiseki_ok']['selector_value']
                    zaiseki_select = Select(row2.find_element(
                        getattr(By, selector_type), selector_value
                    ))
                    applicant_data['zaiseki'] = zaiseki_select.first_selected_option.text
                    self.logger.info(f"✅ {self.selectors['zaiseki_ok']['description']}: {applicant_data['zaiseki']}")
                except Exception as e:
                    self.logger.warning(f"在籍確認の取得に失敗: {str(e)}")
                    applicant_data['zaiseki'] = ''
            
            return applicant_data
            
        except Exception as e:
            self.logger.error(f"応募者情報の取得でエラー: {str(e)}")
            return None

    def check_single_record(self, rows, record_index):
        """
        単一レコードのチェックボックスをクリック
        
        Args:
            rows: テーブルの行要素のリスト
            record_index: 処理対象のレコードインデックス
            
        Returns:
            bool: チェックに成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # 3行で1レコードなので、インデックスを3倍する
            row_offset = record_index * 3
            
            # 行数チェック
            if row_offset + 2 >= len(rows):
                self.logger.warning(f"指定されたインデックス {record_index} は範囲外です")
                return False
            
            # 3行目（チェックボックスがある行）
            row3 = rows[row_offset + 2]
            
            # チェックボックスの操作
            selector_value = self.selectors['confirm_checkbox']['selector_value']
            self.logger.info(f"チェックボックスのセレクター値: {selector_value}")
            
            # デバッグ情報: 行のHTML構造を出力
            row_html = row3.get_attribute('outerHTML')
            self.logger.info(f"行のHTML構造: {row_html[:200]}...")  # 長すぎる場合は切り詰める
            
            # browser.pyのclick_checkboxメソッドを使用
            click_success = self.browser.click_checkbox(
                row3, 
                selector_value, 
                max_retries=3
            )
            
            if click_success:
                self.logger.info(f"応募ID のチェックボックスをクリックしました")
                return True
            else:
                self.logger.warning(f"応募ID のチェックボックスのクリックに失敗しました")
                
                # 別の方法を試す
                try:
                    # 直接JavaScriptでチェックボックスを探してクリック
                    self.logger.info("別の方法でチェックボックスをクリックします")
                    self.browser.driver.execute_script("""
                        var rows = document.querySelectorAll("#recruitment-list table.table-sm tbody > tr");
                        var checkboxes = rows[2].querySelectorAll("input[type='checkbox']");
                        if (checkboxes.length > 0) {
                            checkboxes[0].click();
                            return true;
                        }
                        return false;
                    """)
                    time.sleep(1)
                    return True
                except Exception as e2:
                    self.logger.error(f"別の方法でのチェックボックスクリックにも失敗: {str(e2)}")
                    return False
            
        except Exception as e:
            self.logger.error(f"単一レコードのチェックでエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return False

    def _process_single_application_id(self, app_id, checker, env, adoption):
        """
        単一の応募IDを処理
        
        Args:
            app_id: 処理対象の応募ID
            checker: ApplicantCheckerクラスのインスタンス
            env: EnvironmentUtilsクラス
            adoption: Adoptionクラスのインスタンス
            
        Returns:
            dict: 処理した応募者データ（処理失敗時はNone）
        """
        try:
            self.logger.info(f"応募ID: {app_id} の処理を開始")
            
            # 応募IDで検索
            if not self._search_by_application_id(app_id):
                self.logger.warning(f"応募ID: {app_id} の検索に失敗しました")
                return None
            
            # 検索結果の確認
            has_data, record_count = adoption.check_search_results()
            if not has_data or record_count == 0:
                self.logger.warning(f"応募ID: {app_id} の検索結果がありません")
                return None
            
            # テーブルから行を取得
            table = self.browser.driver.find_element(By.CSS_SELECTOR, "#recruitment-list table.table-sm")
            rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            
            # 応募者情報の取得
            applicant_data = adoption.process_record(rows, 0)
            if not applicant_data:
                self.logger.warning(f"応募ID: {app_id} の情報取得に失敗しました")
                return None
            
            # パターン判定
            pattern = checker.check_pattern(applicant_data)
            applicant_data['pattern'] = pattern
            
            # パターンに応じた処理
            if pattern != '99':  # パターン99以外は処理を実行
                # チェックボックスをクリック
                if adoption.check_single_record(rows, 0):
                    # 更新ボタンをクリック
                    if self._click_update_button():
                        # 更新確定ボタンをクリック
                        if self._click_confirm_button():
                            applicant_data['confirm_checkbox'] = 'ON'
                            applicant_data['confirm_onoff'] = 'ON'
                            self.logger.info(f"応募ID: {app_id} の更新が完了しました")
                        else:
                            applicant_data['confirm_checkbox'] = 'ON'
                            applicant_data['confirm_onoff'] = 'OFF'
                            self.logger.warning(f"応募ID: {app_id} の更新確定に失敗しました")
                    else:
                        applicant_data['confirm_checkbox'] = 'ON'
                        applicant_data['confirm_onoff'] = 'OFF'
                        self.logger.warning(f"応募ID: {app_id} の更新ボタンクリックに失敗しました")
                else:
                    applicant_data['confirm_checkbox'] = 'OFF'
                    applicant_data['confirm_onoff'] = 'OFF'
                    self.logger.warning(f"応募ID: {app_id} のチェックボックスクリックに失敗しました")
            else:
                # パターン99は処理しない
                applicant_data['confirm_checkbox'] = '-'
                applicant_data['confirm_onoff'] = '-'
                self.logger.info(f"応募ID: {app_id} はパターン99のため処理をスキップします")
            
            # 閉じるボタンをクリック
            self._click_close_button()
            
            # ログに記録
            if hasattr(self, 'logger_instance') and self.logger_instance:
                try:
                    log_success = self.logger_instance.log_single_applicant(applicant_data)
                    if log_success:
                        self.logger.info(f"応募ID: {app_id} のデータをログに記録しました")
                    else:
                        self.logger.warning(f"応募ID: {app_id} のデータのログ記録に失敗しました")
                except Exception as log_error:
                    self.logger.error(f"ログ記録中にエラーが発生: {str(log_error)}")
                    # エラーが発生しても処理は続行
            
            self.logger.info(f"応募ID: {app_id} の処理が完了しました")
            return applicant_data
            
        except Exception as e:
            self.logger.error(f"応募ID: {app_id} の処理でエラー: {str(e)}")
            return None