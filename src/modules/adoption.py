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
            try:
                selector_type = self.selectors['training_start_date']['selector_type'].upper()
                selector_value = self.selectors['training_start_date']['selector_value']
                training_element = rows[record_offset].find_element(
                    getattr(By, selector_type), selector_value
                )
                
                # data-value属性から日付を取得
                training_date = training_element.get_attribute('data-value')
                if not training_date:
                    # data-valueが空の場合は「未定」とする
                    training_date = '未定'
                
                applicant_data['training_start_date'] = training_date
                self.logger.info(f"✅ {self.selectors['training_start_date']['description']}: {training_date}")
            except Exception as e:
                self.logger.warning(f"研修日の取得に失敗: {str(e)}")
                applicant_data['training_start_date'] = '未定'
            
            # 在籍確認取得
            selector_type = self.selectors['zaiseki_ok']['selector_type'].upper()
            selector_value = self.selectors['zaiseki_ok']['selector_value']
            zaiseki_select = Select(rows[record_offset + 1].find_element(
                getattr(By, selector_type), selector_value
            ))
            applicant_data['zaiseki'] = zaiseki_select.first_selected_option.text
            self.logger.info(f"✅ {self.selectors['zaiseki_ok']['description']}: {applicant_data['zaiseki']}")
            
            # 3行目の要素を取得（お祝い、パターン判定理由、管理者メモなど）
            self.logger.info("\n【3行目】")
            for element, key in [('celebration', 'oiwai'), ('pattern_reason', 'pattern_reason'), ('remark', 'remark')]:
                if element in self.selectors:
                    try:
                        element_info = self.selectors[element]
                        selector_type = element_info['selector_type'].upper()
                        selector_value = element_info['selector_value']
                        element_obj = rows[record_offset + 2].find_element(
                            getattr(By, selector_type), selector_value
                        )
                        
                        if key == 'pattern_reason' or key == 'remark':
                            # パターン判定理由と備考欄はボタンのテキストを取得
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
            
            # パターン判定理由を追加（pattern_reason - パターン判定の結果を格納）
            self.logger.info(f"DEBUG: adoption.py - パターン判定理由を設定前の値: {applicant_data.get('pattern_reason', '未設定')}")
            applicant_data['pattern_reason'] = reason
            self.logger.info(f"DEBUG: adoption.py - パターン判定理由を設定後 -> key: 'pattern_reason', value: '{applicant_data['pattern_reason']}'")
            
            # 備考欄が設定されていない場合は空文字を設定（remark - ユーザーが入力する備考欄）
            if 'remark' not in applicant_data:
                applicant_data['remark'] = ''
                self.logger.info("備考欄(remark): 未設定のため空文字を設定")
            else:
                self.logger.info(f"備考欄(remark): {applicant_data['remark']}")
            
            # お祝いフラグが未設定の場合は空文字で初期化
            if 'oiwai' not in applicant_data:
                applicant_data['oiwai'] = ''
            
            applicant_data['confirm_checkbox'] = ''
            applicant_data['confirm_onoff'] = ''

            # スキップ条件をチェック
            should_skip = self._should_skip_confirmation_process(applicant_data)
            
            # パターン99以外かつスキップ条件に該当しない場合の処理
            if pattern != 99 and not should_skip:
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
            elif should_skip:
                # スキップ条件に該当する場合
                applicant_data['confirm_checkbox'] = 'スキップ'
                applicant_data['confirm_onoff'] = 'スキップ（備考欄記載あり）'
                self.logger.info(f"✅ 確認完了処理をスキップしました")
            elif pattern == 99:
                # パターン99の場合（従来通り）
                self.logger.info(f"パターン99のため確認完了処理をスキップ")
                applicant_data['confirm_checkbox'] = 'パターン99'
                applicant_data['confirm_onoff'] = 'パターン99対象外'

            return applicant_data

        except Exception as e:
            self.logger.error(f"❌ レコード処理でエラー: {str(e)}")
            return None

    def _should_skip_confirmation_process(self, applicant_data):
        """
        確認完了処理をスキップすべきかどうかを判定
        
        スキップ条件:
        ①ステータス「採用」+ 研修初日「未定」+ 備考欄に記載あり
        ②ステータス「採用」+ 研修初日「日付入力あり」+ 備考欄に記載あり  
        ③ステータス「採用」+ 研修初日「日付入力あり」+ 在籍確認「〇または×」+ 備考欄に記載あり
        
        Args:
            applicant_data (dict): 応募者データ
            
        Returns:
            bool: スキップする場合はTrue
        """
        try:
            status = applicant_data.get('status', '').strip()
            training_date = applicant_data.get('training_start_date', '').strip()
            zaiseki = applicant_data.get('zaiseki', '').strip()
            remark = applicant_data.get('remark', '').strip()
            
            # ステータスが「採用」でない場合はスキップしない
            if status != '採用':
                return False
            
            # 備考欄が空の場合はスキップしない
            if not remark:
                return False
            
            # 条件①: ステータス「採用」+ 研修初日「未定」+ 備考欄に記載あり
            if training_date == '未定':
                self.logger.warning(f"🚫 スキップ条件①に該当: ステータス「{status}」+ 研修初日「{training_date}」+ 備考欄記載あり")
                return True
            
            # 条件②③: 研修初日に日付が入力されている場合
            if training_date and training_date != '未定' and training_date != '':
                # 条件③: 在籍確認が「〇」または「×」の場合
                if zaiseki and (zaiseki == '〇' or '×' in zaiseki):
                    self.logger.warning(f"🚫 スキップ条件③に該当: ステータス「{status}」+ 研修初日「{training_date}」+ 在籍確認「{zaiseki}」+ 備考欄記載あり")
                    return True
                
                # 条件②: 在籍確認がない場合でも研修日+備考欄があればスキップ
                self.logger.warning(f"🚫 スキップ条件②に該当: ステータス「{status}」+ 研修初日「{training_date}」+ 備考欄記載あり")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"スキップ条件判定でエラー: {str(e)}")
            return False

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
                training_element = row1.find_element(
                    getattr(By, selector_type), selector_value
                )
                
                # data-value属性から日付を取得
                training_date = training_element.get_attribute('data-value')
                if not training_date:
                    # data-valueが空の場合は「未定」とする
                    training_date = '未定'
                
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
            
            # 備考欄取得（remark - ユーザーが入力するフリーテキスト）
            try:
                if 'remark' in self.selectors:
                    selector_type = self.selectors['remark']['selector_type'].upper()
                    selector_value = self.selectors['remark']['selector_value']
                    if row_index + 2 < len(rows):  # 3行目が存在する場合
                        remark_element = rows[row_index + 2].find_element(
                            getattr(By, selector_type), selector_value
                        )
                        # ボタン要素からテキスト取得（get_attributeではなく.textを使用）
                        remark_text = remark_element.text.strip()
                        applicant_data['remark'] = remark_text
                        self.logger.info(f"✅ {self.selectors['remark']['description']}(remark): {remark_text}")
                    else:
                        applicant_data['remark'] = ''
                        self.logger.warning("備考欄(remark)取得のための3行目が存在しません")
                else:
                    applicant_data['remark'] = ''
                    self.logger.warning("備考欄(remark)のセレクター定義がありません")
            except Exception as e:
                self.logger.warning(f"備考欄(remark)の取得に失敗: {str(e)}")
                self.logger.warning(f"エラーの詳細: {traceback.format_exc()}")
                applicant_data['remark'] = ''
            
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