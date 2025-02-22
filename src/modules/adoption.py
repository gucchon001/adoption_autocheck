from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from datetime import datetime
import time
from ..utils.logging_config import get_logger

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
                try:
                    # チェックボックスの操作
                    selector_type = self.selectors['confirm_checkbox']['selector_type'].upper()
                    selector_value = self.selectors['confirm_checkbox']['selector_value']
                    checkbox = rows[record_offset + 2].find_element(
                        getattr(By, selector_type), selector_value
                    )
                    checkbox.click()
                    applicant_data['confirm_checkbox'] = 'チェック'
                    self.check_changes_made = True
                    self.logger.info("✅ 確認完了チェックボックスをONに設定")
                    
                    # auto_updateの設定を取得して更新状態を設定
                    auto_update = self.env.get_config_value('BROWSER', 'auto_update', default=False)
                    applicant_data['confirm_onoff'] = '更新' if auto_update else '更新キャンセル'
                    
                except Exception as e:
                    self.logger.error(f"❌ チェックボックスの操作に失敗: {str(e)}")

            return applicant_data

        except Exception as e:
            self.logger.error(f"❌ レコード処理でエラー: {str(e)}")
            return None 