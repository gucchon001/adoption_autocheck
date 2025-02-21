import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.modules.browser import Browser
from src.modules.checker import ApplicantChecker
from src.utils.environment import EnvironmentUtils as env
import os
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.modules.spreadsheet import SpreadSheet

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
    
    # 転記対象のデータを保持するリスト
    applicants_to_log = []
    # チェックボックスの変更があったかどうかのフラグ
    check_changes_made = False
    
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
    
    # デバッグ: 読み込んだセレクター情報を表示
    print("\nセレクター情報:")
    for element_name, info in selectors.items():
        print(f"{info['description']}:")
        print(f"  セレクタータイプ: {info['selector_type']}")
        print(f"  セレクター値: {info['selector_value']}")
        print()

    print("セレクター情報の読み込みテスト完了")

    # ブラウザでの要素取得テスト
    try:
        print("\n=== ブラウザテスト開始 ===")
        print("1. ブラウザを起動中...")
        browser.setup()
        
        print("2. ログイン処理を開始...")
        url = os.getenv('ADMIN_URL')
        basic_auth = {
            'id': os.getenv('BASIC_AUTH_ID'),
            'password': os.getenv('BASIC_AUTH_PASSWORD')
        }
        login_credentials = {
            'id': os.getenv('LOGIN_ID'),
            'password': os.getenv('LOGIN_PASSWORD')
        }
        browser.login(url, basic_auth, login_credentials)
        print("✅ ログイン完了")

        # 採用確認ページへ遷移
        print("\n3. 採用確認ページへ遷移中...")
        adoptions_url = f"{url}/adoptions"
        browser.driver.get(adoptions_url)
        
        # ページ読み込み完了を待機
        wait = WebDriverWait(browser.driver, 10)
        print("テーブルの読み込みを待機中...")
        
        # メインテーブルを取得
        table = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, 
                "#recruitment-list table.table-sm"
            ))
        )
        print("✅ テーブルを取得")
        
        # tbody内の行を取得
        rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
        print(f"取得した行数: {len(rows)}")
        
        # 5レコード分の情報を取得してパターンマッチング
        for record_index in range(10):
            record_offset = record_index * 3
            print(f"\n=== {record_index + 1}レコード目の情報取得とパターン分析 ===")
            
            try:
                # データ収集
                applicant_data = {}
                
                # 応募IDを取得
                applicant_id = rows[record_offset].find_element(
                    By.CSS_SELECTOR, selectors['applicant_id']['selector_value']
                ).text.strip()
                applicant_data['id'] = applicant_id
                print(f"✅ {selectors['applicant_id']['description']}: {applicant_id}")
                
                # ステータス取得
                status_select = Select(rows[record_offset].find_element(
                    By.CSS_SELECTOR, selectors['status']['selector_value']
                ))
                applicant_data['status'] = status_select.first_selected_option.text
                print(f"✅ {selectors['status']['description']}: {applicant_data['status']}")
                
                # 研修初日取得
                training_date = rows[record_offset].find_element(
                    By.CSS_SELECTOR, selectors['training_start_date']['selector_value']
                ).text.strip()
                applicant_data['training_start_date'] = training_date
                print(f"✅ {selectors['training_start_date']['description']}: {training_date}")
                
                # 在籍確認取得
                zaiseki_select = Select(rows[record_offset + 1].find_element(
                    By.CSS_SELECTOR, selectors['zaiseki_ok']['selector_value']
                ))
                applicant_data['zaiseki'] = zaiseki_select.first_selected_option.text
                print(f"✅ {selectors['zaiseki_ok']['description']}: {applicant_data['zaiseki']}")
                
                # 3行目の要素を取得（お祝い、備考）
                print("\n【3行目】")
                for element, key in [('celebration', 'oiwai'), ('remark', 'remark')]:
                    if element in selectors:
                        try:
                            element_info = selectors[element]
                            element_obj = rows[record_offset + 2].find_element(
                                By.CSS_SELECTOR, 
                                element_info['selector_value']
                            )
                            
                            if key == 'remark':
                                # 備考の場合は、buttonのテキストを確認
                                value = element_obj.text.strip() if element_obj.text.strip() else ''
                            else:
                                value = element_obj.text if element_info['action_type'] == 'get_text' else ''
                                
                            applicant_data[key] = value
                            print(f"✅ {element_info['description']}: {value}")
                        except Exception as e:
                            print(f"❌ {element_info['description']}の取得に失敗: {str(e)}")
                
                # パターン判定
                pattern = 99  # デフォルトパターン
                reason = "該当パターンなし"
                
                # パターン2: 採用_未定
                if (applicant_data['status'] == '採用' and 
                    applicant_data['training_start_date'] == '未定' and 
                    not applicant_data['zaiseki'] and
                    applicant_data['oiwai'] == '' and 
                    applicant_data['remark'] == ''):
                    pattern = 2
                    reason = "研修日未定・在籍確認未実施・お祝い空白・備考空白"
                
                # パターン3: 研修日確定（実行月以降）
                elif (applicant_data['status'] == '採用' and 
                      applicant_data['training_start_date'] and 
                      applicant_data['training_start_date'] != '未定' and
                      not applicant_data['zaiseki'] and
                      applicant_data['oiwai'] == '' and 
                      applicant_data['remark'] == ''):
                    
                    # 日付判定の詳細を取得
                    try:
                        training_date = datetime.strptime(applicant_data['training_start_date'], "%Y/%m/%d")
                        current_date = datetime.now()
                        
                        # 実行月以降かどうかの判定
                        is_future_month = (training_date.year > current_date.year) or (
                            training_date.year == current_date.year and 
                            training_date.month >= current_date.month
                        )
                        
                        if is_future_month:
                            pattern = 3
                            reason = f"研修日({applicant_data['training_start_date']})・実行月以降・在籍確認未実施・お祝い空白・備考空白"
                        else:
                            pattern = 99
                            reason = f"研修日({applicant_data['training_start_date']})・実行月より前・在籍確認未実施・お祝い空白・備考空白"
                    except ValueError:
                        pattern = 99
                        reason = f"研修日の日付形式エラー({applicant_data['training_start_date']})・在籍確認未実施・お祝い空白・備考空白"
                
                # パターン4: 採用_1ヶ月以上経過_◯
                elif (applicant_data['status'] == '採用' and 
                      applicant_data['training_start_date'] and 
                      applicant_data['training_start_date'] != '未定' and
                      applicant_data['zaiseki'] == '〇' and
                      applicant_data['oiwai'] == '' and 
                      applicant_data['remark'] == ''):
                    
                    # 日付判定の詳細を取得
                    try:
                        training_date = datetime.strptime(applicant_data['training_start_date'], "%Y/%m/%d")
                        current_date = datetime.now()
                        one_month_ago = current_date - relativedelta(months=1)
                        is_one_month_passed = training_date <= one_month_ago
                        
                        if is_one_month_passed:
                            pattern = 4
                            reason = f"研修日({applicant_data['training_start_date']})・1ヶ月以上経過・在籍確認済み・お祝い空白・備考空白"
                        else:
                            pattern = 99
                            reason = f"研修日({applicant_data['training_start_date']})・1ヶ月経過していない・在籍確認済み・お祝い空白・備考空白"
                    except ValueError:
                        pattern = 99
                        reason = f"研修日の日付形式エラー({applicant_data['training_start_date']})・在籍確認済み・お祝い空白・備考空白"
                
                # パターン1: 不採用等確定
                elif (applicant_data['status'] in ['保留', '不合格', '連絡取れず', '辞退', '欠席'] and
                      applicant_data['oiwai'] == '' and 
                      applicant_data['remark'] == ''):
                    pattern = 1
                    reason = f"不採用等確定（{applicant_data['status']}）・お祝い空白・備考空白"
                
                print(f"\n判定結果: パターン{pattern}")
                print(f"判定理由: {reason}")
                print(f"データ: {applicant_data}")
                
                # パターン判定のデバッグ情報
                print("\nパターン判定の詳細:")
                print(f"ステータス: {applicant_data['status']}")
                print(f"研修初日: {applicant_data['training_start_date']}")
                print(f"在籍確認: {applicant_data['zaiseki']}")
                print(f"お祝い: {applicant_data['oiwai']}")
                print(f"備考: {applicant_data['remark']}")
                
                if pattern == 99:
                    print("パターン99の理由:")
                    if applicant_data['status'] == '採用':
                        if applicant_data['training_start_date'] == '未定':
                            if applicant_data['zaiseki'] or applicant_data['oiwai'] or applicant_data['remark']:
                                print("→ 採用_未定だが、他の項目が空でない")
                        elif applicant_data['training_start_date']:
                            if applicant_data['zaiseki'] == '〇':
                                print("→ 採用で在籍確認済みだが、1ヶ月経過していない")
                            else:
                                print("→ 採用だが在籍確認未実施")
                    else:
                        print(f"→ ステータスが不採用等確定({applicant_data['status']})以外")
                
                # パターンマッチング結果をログ用データに追加
                log_entry = {
                    'id': applicant_data['id'],
                    'status': applicant_data['status'],
                    'pattern': str(pattern),
                    'oiwai': applicant_data['oiwai'],
                    'remark': applicant_data['remark'],
                    'training_start_date': applicant_data['training_start_date'],
                    'zaiseki': applicant_data['zaiseki'],
                    'confirm_checkbox': '',  # デフォルトは空文字
                    'confirm_onoff': ''     # 更新状態を追加
                }

                # パターン99以外の場合の処理
                if pattern != 99:
                    try:
                        # チェックボックスの操作
                        checkbox = rows[record_offset + 2].find_element(
                            By.CSS_SELECTOR, selectors['confirm_checkbox']['selector_value']
                        )
                        checkbox.click()
                        log_entry['confirm_checkbox'] = 'チェック'
                        check_changes_made = True
                        print("✅ 確認完了チェックボックスをONに設定")
                        
                    except Exception as e:
                        print(f"❌ チェックボックスの操作に失敗: {str(e)}")
                        log_entry['confirm_checkbox'] = ''
                        log_entry['confirm_onoff'] = ''

                applicants_to_log.append(log_entry)
                print(f"✅ ログ記録対象に追加: パターン{pattern}")
                
            except Exception as e:
                print(f"❌ データ取得またはパターンマッチングでエラー: {str(e)}")
            
            print("-" * 50)

        # すべてのチェックボックス操作が完了した後に更新処理を実行
        if check_changes_made:
            try:
                # 更新ボタンクリック
                update_button = browser.driver.find_element(
                    By.CSS_SELECTOR, selectors['update_button']['selector_value']
                )
                update_button.click()
                browser.wait.until(EC.presence_of_all_elements_located)
                time.sleep(1)
                print("✅ 更新ボタンをクリックしました")
                
                # auto_updateの設定をEnvironmentUtilsから取得
                auto_update = env.get_config_value('BROWSER', 'auto_update', default=False)
                
                # 更新状態を設定（この時点で全てのチェック済みエントリに対して設定）
                for entry in applicants_to_log:
                    if entry['confirm_checkbox'] == 'チェック':
                        entry['confirm_onoff'] = '更新' if auto_update else '更新キャンセル'
                
                if auto_update:
                    # 更新を確定
                    update_confirm_button = browser.driver.find_element(
                        By.CSS_SELECTOR, selectors['update_confirm_button']['selector_value']
                    )
                    update_confirm_button.click()
                    print("✅ 更新を確定しました")
                else:
                    # 更新をキャンセル
                    update_cancel_button = browser.driver.find_element(
                        By.CSS_SELECTOR, selectors['update_cancel_button']['selector_value']
                    )
                    update_cancel_button.click()
                    print("✅ 更新をキャンセルしました")
                
                browser.wait.until(EC.presence_of_all_elements_located)
                time.sleep(2.5)
            except Exception as e:
                print(f"❌ 更新処理でエラーが発生: {str(e)}")

    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生: {str(e)}")
    
    finally:
        # テスト終了前にスプレッドシートへの転記を実行
        if applicants_to_log:
            print("\n=== スプレッドシートへの転記を開始 ===")
            try:
                if spreadsheet.append_logs(applicants_to_log):
                    print(f"✅ {len(applicants_to_log)}件のデータを転記しました")
                else:
                    print("❌ データの転記に失敗しました")
            except Exception as e:
                print(f"❌ スプレッドシート転記中にエラー: {str(e)}")
        
        print("\n=== テスト終了 ===")
        browser.quit()

if __name__ == "__main__":
    test_browser()