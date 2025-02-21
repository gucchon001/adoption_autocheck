import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.modules.browser import Browser
from src.modules.checker import ApplicantChecker
import os
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

def test_browser():
    # 環境変数の読み込み
    load_dotenv('config/secrets_test.env')
    
    # セレクター情報の読み込み
    checker = ApplicantChecker(
        Path("config/selectors.csv"),
        Path("config/judge_list.csv")
    )
    selectors = checker.get_selectors()
    
    # デバッグ: 読み込んだセレクター情報を表示
    print("\nセレクター情報:")
    for element_name, info in selectors.items():
        print(f"{info['description']}:")
        print(f"  セレクタータイプ: {info['selector_type']}")
        print(f"  セレクター値: {info['selector_value']}")
        print()

    print("セレクター情報の読み込みテスト完了")

    # ブラウザでの要素取得テスト
    browser = Browser()
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
        for record_index in range(30):
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
                ).text.strip() or "未定"
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
                
                # パターン3: 採用_実行月以降
                elif (applicant_data['status'] == '採用' and 
                      applicant_data['training_start_date'] and 
                      applicant_data['training_start_date'] != '未定' and
                      not applicant_data['zaiseki'] and
                      applicant_data['oiwai'] == '' and 
                      applicant_data['remark'] == ''):
                    pattern = 3
                    
                    # 日付判定の詳細を取得
                    try:
                        training_date = datetime.strptime(applicant_data['training_start_date'], "%Y/%m/%d")
                        current_date = datetime.now()
                        
                        # 実行月以降かどうかの判定
                        is_future_month = (training_date.year > current_date.year) or (
                            training_date.year == current_date.year and 
                            training_date.month >= current_date.month
                        )
                        
                        date_status = "実行月以降" if is_future_month else "実行月より前"
                        reason = f"研修日({applicant_data['training_start_date']})・{date_status}・在籍確認未実施・お祝い空白・備考空白"
                    except ValueError:
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
                
            except Exception as e:
                print(f"❌ データ取得またはパターンマッチングでエラー: {str(e)}")
            
            print("-" * 50)

    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生: {str(e)}")
    
    finally:
        print("\n=== テスト終了 ===")
        browser.quit()

if __name__ == "__main__":
    test_browser()