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
        
        # 検索条件の設定と検索実行をテスト
        print("\n4. 検索条件の設定テスト...")
        try:
            # ページが完全に読み込まれるまで待機
            browser.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#form_search"
                ))
            )
            time.sleep(1)

            # 提出ステータスの設定
            status_value = env.get_config_value('SEARCH', 'submit_status', '0')
            try:
                if status_value != "0":
                    # 値が設定されている場合
                    selector_type = selectors['submit_status']['selector_type'].upper()
                    selector_value = selectors['submit_status']['selector_value']
                    
                    # value属性を動的に設定
                    if status_value:
                        selector_value = f"{selector_value}[value='{status_value}']"
                    
                    submit_status = browser.wait.until(
                        EC.element_to_be_clickable((
                            getattr(By, selector_type),
                            selector_value
                        ))
                    )
                    submit_status.click()
                    status_text = {
                        1: "未提出",
                        2: "提出中",
                        3: "差戻し",
                        4: "完了"
                    }.get(str(status_value), "不明")
                    print(f"✅ 提出ステータスを設定: {status_text}")
                else:
                    # 指定なしの場合
                    selector_type = selectors['submit_status']['selector_type'].upper()
                    selector_value = f"{selectors['submit_status']['selector_value']}[value='']"
                    submit_status = browser.wait.until(
                        EC.element_to_be_clickable((
                            getattr(By, selector_type),
                            selector_value
                        ))
                    )
                    submit_status.click()
                    print("✅ 提出ステータス: 指定なし")
            except Exception as e:
                print(f"❌ 提出ステータスの設定でエラー: {str(e)}")

            # 提出期限の設定
            deadline_value = env.get_config_value('SEARCH', 'submit_deadline', '')
            
            try:
                # 文字列の二重引用符を除去して判定
                cleaned_deadline = deadline_value.strip('"')
                if cleaned_deadline:
                    # 値が設定されている場合（今月末または期限超過）のみ処理
                    selector_type = selectors['submit_deadline']['selector_type'].upper()
                    selector_value = selectors['submit_deadline']['selector_value']
                    
                    if cleaned_deadline != "":
                        selector_value = f"{selector_value}[value='{cleaned_deadline}']"
                    
                    submit_deadline = browser.wait.until(
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
                    # 指定なしの場合は何もしない（デフォルトで選択済み）
                    print("✅ 提出期限: 指定なし")
            except Exception as e:
                print(f"❌ 提出期限の設定でエラー: {str(e)}")

            # 検索ボタンクリック
            try:
                selector_type = selectors['search_button']['selector_type'].upper()
                selector_value = selectors['search_button']['selector_value']
                
                # フォーム検索の完了を待機
                browser.wait.until(
                    EC.presence_of_element_located((
                        getattr(By, selector_type),
                        "#form_search"
                    ))
                )
                
                # 検索ボタンが操作可能になるまで待機
                search_button = browser.wait.until(
                    EC.element_to_be_clickable((
                        getattr(By, selector_type),
                        selector_value
                    ))
                )
                search_button.click()
                
                # ローディング表示の消失を待機
                browser.wait.until(
                    EC.invisibility_of_element_located((
                        getattr(By, selector_type),
                        ".loading"
                    ))
                )
                
                # テーブルの再読み込みを待機
                browser.wait.until(
                    EC.presence_of_element_located((
                        getattr(By, selector_type),
                        "#recruitment-list table.table-sm"
                    ))
                )
                print("✅ 検索ボタンをクリックし、結果を読み込み完了")
            except Exception as e:
                print(f"❌ 検索ボタンのクリックでエラー: {str(e)}")
                raise e  # エラーの詳細を確認するために例外を再送出
            
            # 検索結果の読み込みを待機（より長い待機時間を設定）
            browser.wait = WebDriverWait(browser.driver, 20)  # タイムアウトを20秒に延長
            
            # まずローディング表示の消失を待機
            try:
                loading = browser.wait.until(
                    EC.invisibility_of_element_located((
                        By.CSS_SELECTOR, 
                        ".loading"
                    ))
                )
                print("✅ ローディング完了")
            except Exception as e:
                print(f"⚠️ ローディング要素の待機でエラー: {str(e)}")

            # テーブルの読み込みを待機
            table = browser.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR, 
                    "#recruitment-list table.table-sm"
                ))
            )
            time.sleep(2)  # 追加の待機時間
            print("✅ テーブルの読み込み完了")

        except Exception as e:
            print(f"❌ 検索条件の設定でエラー: {str(e)}")
            raise e

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
        
        try:
            # "該当する採用確認が見つかりませんでした"のメッセージを確認
            no_data_message = table.find_element(
                By.CSS_SELECTOR, 
                "tbody tr td[colspan='10']"
            ).text.strip()
            
            if "該当する採用確認が見つかりませんでした" in no_data_message:
                print("検索結果が0件のため、処理を終了します")
                return
                
        except Exception as e:
            # メッセージが見つからない場合は通常の行数チェックを実行
            rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            total_rows = len(rows)
            record_count = total_rows // 3
            print(f"取得した行数: {total_rows} (レコード数: {record_count})")
            
            if total_rows == 0:
                print("検索結果が0件のため、処理を終了します")
                return
        
        # レコード分の情報を取得してパターンマッチング
        for record_index in range(record_count):
            record_offset = record_index * 3
            print(f"\n=== {record_index + 1}レコード目の情報取得とパターン分析 ===")
            
            try:
                # データ収集
                applicant_data = {}
                
                # 応募IDを取得
                selector_type = selectors['applicant_id']['selector_type'].upper()
                selector_value = selectors['applicant_id']['selector_value']
                applicant_id = rows[record_offset].find_element(
                    getattr(By, selector_type), selector_value
                ).text.strip()
                applicant_data['id'] = applicant_id
                print(f"✅ {selectors['applicant_id']['description']}: {applicant_id}")
                
                # ステータス取得
                selector_type = selectors['status']['selector_type'].upper()
                selector_value = selectors['status']['selector_value']
                status_select = Select(rows[record_offset].find_element(
                    getattr(By, selector_type), selector_value
                ))
                applicant_data['status'] = status_select.first_selected_option.text
                print(f"✅ {selectors['status']['description']}: {applicant_data['status']}")
                
                # 研修初日取得
                selector_type = selectors['training_start_date']['selector_type'].upper()
                selector_value = selectors['training_start_date']['selector_value']
                training_date = rows[record_offset].find_element(
                    getattr(By, selector_type), selector_value
                ).text.strip()
                applicant_data['training_start_date'] = training_date
                print(f"✅ {selectors['training_start_date']['description']}: {training_date}")
                
                # 在籍確認取得
                selector_type = selectors['zaiseki_ok']['selector_type'].upper()
                selector_value = selectors['zaiseki_ok']['selector_value']
                zaiseki_select = Select(rows[record_offset + 1].find_element(
                    getattr(By, selector_type), selector_value
                ))
                applicant_data['zaiseki'] = zaiseki_select.first_selected_option.text
                print(f"✅ {selectors['zaiseki_ok']['description']}: {applicant_data['zaiseki']}")
                
                # 3行目の要素を取得（お祝い、備考）
                print("\n【3行目】")
                for element, key in [('celebration', 'oiwai'), ('remark', 'remark')]:
                    if element in selectors:
                        try:
                            element_info = selectors[element]
                            selector_type = element_info['selector_type'].upper()
                            selector_value = element_info['selector_value']
                            element_obj = rows[record_offset + 2].find_element(
                                getattr(By, selector_type), selector_value
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
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # タイムスタンプを追加
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
                        selector_type = selectors['confirm_checkbox']['selector_type'].upper()
                        selector_value = selectors['confirm_checkbox']['selector_value']
                        checkbox = rows[record_offset + 2].find_element(
                            getattr(By, selector_type), selector_value
                        )
                        checkbox.click()
                        log_entry['confirm_checkbox'] = 'チェック'
                        check_changes_made = True
                        print("✅ 確認完了チェックボックスをONに設定")
                        
                        # auto_updateの設定を取得して更新状態を設定
                        auto_update = env.get_config_value('BROWSER', 'auto_update', default=False)
                        log_entry['confirm_onoff'] = '更新' if auto_update else '更新キャンセル'
                        
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
                selector_type = selectors['update_button']['selector_type'].upper()
                selector_value = selectors['update_button']['selector_value']
                update_button = browser.driver.find_element(
                    getattr(By, selector_type),
                    selector_value
                )
                update_button.click()
                
                # モーダルの表示を待機
                selector_type = selectors['update_confirm_button']['selector_type'].upper()
                browser.wait.until(
                    EC.visibility_of_element_located((
                        getattr(By, selector_type), 
                        "#modal-confirm_update_application"
                    ))
                )
                
                # auto_updateの設定をEnvironmentUtilsから取得
                auto_update = env.get_config_value('BROWSER', 'auto_update', default=False)
                
                if auto_update:
                    # 更新を確定
                    selector_type = selectors['update_confirm_button']['selector_type'].upper()
                    selector_value = selectors['update_confirm_button']['selector_value']
                    update_confirm_button = browser.wait.until(
                        EC.element_to_be_clickable((
                            getattr(By, selector_type),
                            selector_value
                        ))
                    )
                    update_confirm_button.click()
                    
                    # 更新完了を待機（モーダルの消失）
                    browser.wait.until(
                        EC.invisibility_of_element_located((
                            getattr(By, selector_type), 
                            "#modal-confirm_update_application"
                        ))
                    )
                    print("✅ 更新を確定しました")
                    # 更新確定後にログエントリを更新
                    for entry in applicants_to_log:
                        if entry['confirm_checkbox'] == 'チェック':
                            entry['confirm_onoff'] = '更新'
                else:
                    # 更新をキャンセル
                    selector_type = selectors['update_cancel_button']['selector_type'].upper()
                    selector_value = selectors['update_cancel_button']['selector_value']
                    update_cancel_button = browser.driver.find_element(
                        getattr(By, selector_type),
                        selector_value
                    )
                    update_cancel_button.click()
                    print("✅ 更新をキャンセルしました")
                    # キャンセル後にログエントリを更新
                    for entry in applicants_to_log:
                        if entry['confirm_checkbox'] == 'チェック':
                            entry['confirm_onoff'] = '更新キャンセル'
                
                # 最終的な要素の読み込み待機
                browser.wait.until(
                    EC.presence_of_element_located((
                        getattr(By, selector_type),
                        "#recruitment-list"
                    ))
                )
                time.sleep(1)  # 短い待機時間に変更
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