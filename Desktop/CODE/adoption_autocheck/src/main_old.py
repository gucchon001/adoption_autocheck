import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.select import Select
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tkinter import messagebox
import requests, json
import os


def get_txt(file_name, list_name):
    with open(f'{file_name}', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "\n" == line:
                continue
            list_name.append(re.sub("\n", "", line))

user_id_ls = []
get_txt(os.path.abspath('.')+"\\log.txt", user_id_ls)


# 設定ファイルの読み込み
domain = ""
spreadsheet_key = ""
webhook = ""
username = ""
password = ""
username2 = ""
password2 = ""
exec_time1 = ""
exec_time2 = ""
TEST = None
try:
    with open(f'{os.path.abspath(".")}\\setting.txt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "\n" == line:
                continue
            line = re.sub("\n", "", line)
            if "domain" in line:
                domain = line.split("=")[1]
            elif "SpreadSheetKey" in line:
                spreadsheet_key = line.split("=")[1]
            elif "webhook" in line:
                webhook = line.split("=")[1]
            elif "BasicId" in line:
                username = line.split("=")[1]
            elif "BasicPw" in line:
                password = line.split("=")[1]
            elif "LoginId" in line:
                username2 = line.split("=")[1]
            elif "LoginPw" in line:
                password2 = line.split("=")[1]
            elif "exec_time1" in line:
                exec_time1 = list(map(int, line.split("=")[1].split(":")))
            elif "exec_time2" in line:
                exec_time2 = list(map(int, line.split("=")[1].split(":")))
            elif "TEST" in line:
                bool_val = line.split("=")[1].lower()
                if bool_val == "true":
                    TEST = True
                else:
                    TEST = False
except:
    print("setting.txtに誤りがあります。")






while True:
    # テスト用変数
    last_row = 0
    # ログを格納するリスト
    log_list = []
    # 今日の日付
    current_date = None
    print("待機中")
    while True:
        current_date = datetime.now()
        # 待機処理
        if str(current_date.hour) == str(exec_time1[0]) and str(current_date.minute) == str(exec_time1[1]):
            print("実行スタート")
            break
        elif str(current_date.hour) == str(exec_time2[0]) and str(current_date.minute) == str(exec_time2[1]):
            print("実行スタート")
            break
        else:
            time.sleep(1)
            continue



    # スプレッドシート設定
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(f'{os.path.abspath(".")}\\data.json', scope)
    gc = gspread.authorize(credentials)
    # シート指定
    worksheet = gc.open_by_key(spreadsheet_key).sheet1

    # 最終行取得
    last_row = len(worksheet.col_values(1))

    # driver起動



    driver = None
    while True:
        try:
            print("ドライバー起動開始")
            service = Service(executable_path=f'{os.path.abspath(".")}\\chromedriver.exe')
            driver = webdriver.Chrome(service=service)
            wait = WebDriverWait(driver=driver, timeout=20)
            driver.maximize_window()
            print("ドライバー起動完了")
            break
        except Exception as e:
            print(f"ERROR:{e}")
            time.sleep(10)

    # ベーシック認証
    url_with_credentials = f"https://{username}:{password}@{domain}/admin/"
    driver.get(url_with_credentials)
    # 要素が全て検出できるまで待機する
    wait.until(EC.presence_of_all_elements_located)
    print("Basic認証 認証完了")
    time.sleep(1)
    # サービスログイン
    driver.find_element(By.NAME, "login").send_keys(username2)
    driver.find_element(By.NAME, "password").send_keys(password2)
    time.sleep(0.5)
    driver.find_element(By.NAME, "commit").click()
    print("サービスログイン完了")
    time.sleep(1)

    # 採用確認ページにアクセス（URLのパラメーター内容➡　　提出ステータス：提出中、採用ステータス：未選択、提出期限：今月末、確認完了：未確認）

    if TEST:
        # テスト版
        driver.get(f"https://{domain}/admin/adoptions?s%5Border%5D=1&c%5Bcompany_id_or_company_code%5D=&c%5Bcompany_name%5D=&c%5Bclassroom_id%5D=&c%5Bclassroom_name%5D=&c%5Bclassroom_group_id%5D=&c%5Breservation_month_count%5D=&c%5Bclassroom_prefecture_id%5D=&c%5Bjob_candidate_name%5D=&c%5Bjob_candidate_email%5D=&c%5Bjob_candidate_disp_id%5D=&c%5Bapply_site_enum%5D=&c%5Badoption_status_id%5D=&c%5Bbelong_1month_enum%5D=&c%5Bsubmit_expired_on%5D=&c%5Bsubmit_status_enum_client%5D=&c%5Bexpired_month_count%5D=&c%5Bsubmit_status_enum%5D=2&c%5Badmin_check_flag%5D=false&c%5Bquestion_employ%5D=&c%5Btutor_no%5D=&c%5Bdiffer%5D=&c%5Btraining_first_on%5D=0&c%5Bdivide_grade%5D=&c%5Bfrom_candidate_at%281i%29%5D=&c%5Bfrom_candidate_at%282i%29%5D=&c%5Bfrom_candidate_at%283i%29%5D=&c%5Bfrom_candidate_at%284i%29%5D=&c%5Bfrom_candidate_at%285i%29%5D=&c%5Bfrom_candidate_at%286i%29%5D=&c%5Bto_candidate_at%281i%29%5D=&c%5Bto_candidate_at%282i%29%5D=&c%5Bto_candidate_at%283i%29%5D=&c%5Bto_candidate_at%284i%29%5D=&c%5Bto_candidate_at%285i%29%5D=&c%5Bto_candidate_at%286i%29%5D=&c%5Bfrom_last_submitted_at%281i%29%5D=&c%5Bfrom_last_submitted_at%282i%29%5D=&c%5Bfrom_last_submitted_at%283i%29%5D=&c%5Bfrom_last_submitted_at%284i%29%5D=&c%5Bfrom_last_submitted_at%285i%29%5D=&c%5Bfrom_last_submitted_at%286i%29%5D=&c%5Bto_last_submitted_at%281i%29%5D=&c%5Bto_last_submitted_at%282i%29%5D=&c%5Bto_last_submitted_at%283i%29%5D=&c%5Bto_last_submitted_at%284i%29%5D=&c%5Bto_last_submitted_at%285i%29%5D=&c%5Bto_last_submitted_at%286i%29%5D=&c%5Bfrom_training_first_on%281i%29%5D=&c%5Bfrom_training_first_on%282i%29%5D=&c%5Bfrom_training_first_on%283i%29%5D=&c%5Bfrom_training_first_on%284i%29%5D=&c%5Bfrom_training_first_on%285i%29%5D=&c%5Bfrom_training_first_on%286i%29%5D=&c%5Bto_training_first_on%281i%29%5D=&c%5Bto_training_first_on%282i%29%5D=&c%5Bto_training_first_on%283i%29%5D=&c%5Bto_training_first_on%284i%29%5D=&c%5Bto_training_first_on%285i%29%5D=&c%5Bto_training_first_on%286i%29%5D=&c%5Bfrom_updated_at%281i%29%5D=&c%5Bfrom_updated_at%282i%29%5D=&c%5Bfrom_updated_at%283i%29%5D=&c%5Bfrom_updated_at%284i%29%5D=&c%5Bfrom_updated_at%285i%29%5D=&c%5Bfrom_updated_at%286i%29%5D=&c%5Bto_updated_at%281i%29%5D=&c%5Bto_updated_at%282i%29%5D=&c%5Bto_updated_at%283i%29%5D=&c%5Bto_updated_at%284i%29%5D=&c%5Bto_updated_at%285i%29%5D=&c%5Bto_updated_at%286i%29%5D=&commit=検索")
    else:
        # 本番版
        driver.get(f"https://{domain}/admin/adoptions?s%5Border%5D=1&c%5Bcompany_id_or_company_code%5D=&c%5Bcompany_name%5D=&c%5Bclassroom_id%5D=&c%5Bclassroom_name%5D=&c%5Bclassroom_group_id%5D=&c%5Breservation_month_count%5D=&c%5Bclassroom_prefecture_id%5D=&c%5Bjob_candidate_name%5D=&c%5Bjob_candidate_email%5D=&c%5Bjob_candidate_disp_id%5D=&c%5Bapply_site_enum%5D=&c%5Badoption_status_id%5D=&c%5Bbelong_1month_enum%5D=&c%5Bsubmit_expired_on%5D=1&c%5Bsubmit_status_enum_client%5D=&c%5Bexpired_month_count%5D=&c%5Bsubmit_status_enum%5D=2&c%5Badmin_check_flag%5D=false&c%5Bquestion_employ%5D=&c%5Btutor_no%5D=&c%5Bdiffer%5D=&c%5Btraining_first_on%5D=0&c%5Bdivide_grade%5D=&c%5Bfrom_candidate_at%281i%29%5D=&c%5Bfrom_candidate_at%282i%29%5D=&c%5Bfrom_candidate_at%283i%29%5D=&c%5Bfrom_candidate_at%284i%29%5D=&c%5Bfrom_candidate_at%285i%29%5D=&c%5Bfrom_candidate_at%286i%29%5D=&c%5Bto_candidate_at%281i%29%5D=&c%5Bto_candidate_at%282i%29%5D=&c%5Bto_candidate_at%283i%29%5D=&c%5Bto_candidate_at%284i%29%5D=&c%5Bto_candidate_at%285i%29%5D=&c%5Bto_candidate_at%286i%29%5D=&c%5Bfrom_last_submitted_at%281i%29%5D=&c%5Bfrom_last_submitted_at%282i%29%5D=&c%5Bfrom_last_submitted_at%283i%29%5D=&c%5Bfrom_last_submitted_at%284i%29%5D=&c%5Bfrom_last_submitted_at%285i%29%5D=&c%5Bfrom_last_submitted_at%286i%29%5D=&c%5Bto_last_submitted_at%281i%29%5D=&c%5Bto_last_submitted_at%282i%29%5D=&c%5Bto_last_submitted_at%283i%29%5D=&c%5Bto_last_submitted_at%284i%29%5D=&c%5Bto_last_submitted_at%285i%29%5D=&c%5Bto_last_submitted_at%286i%29%5D=&c%5Bfrom_training_first_on%281i%29%5D=&c%5Bfrom_training_first_on%282i%29%5D=&c%5Bfrom_training_first_on%283i%29%5D=&c%5Bfrom_training_first_on%284i%29%5D=&c%5Bfrom_training_first_on%285i%29%5D=&c%5Bfrom_training_first_on%286i%29%5D=&c%5Bto_training_first_on%281i%29%5D=&c%5Bto_training_first_on%282i%29%5D=&c%5Bto_training_first_on%283i%29%5D=&c%5Bto_training_first_on%284i%29%5D=&c%5Bto_training_first_on%285i%29%5D=&c%5Bto_training_first_on%286i%29%5D=&c%5Bfrom_updated_at%281i%29%5D=&c%5Bfrom_updated_at%282i%29%5D=&c%5Bfrom_updated_at%283i%29%5D=&c%5Bfrom_updated_at%284i%29%5D=&c%5Bfrom_updated_at%285i%29%5D=&c%5Bfrom_updated_at%286i%29%5D=&c%5Bto_updated_at%281i%29%5D=&c%5Bto_updated_at%282i%29%5D=&c%5Bto_updated_at%283i%29%5D=&c%5Bto_updated_at%284i%29%5D=&c%5Bto_updated_at%285i%29%5D=&c%5Bto_updated_at%286i%29%5D=&commit=検索")




    # 要素が全て検出できるまで待機する
    while True:
        wait.until(EC.presence_of_all_elements_located)
        time.sleep(0.5)
        tr_tags = driver.find_elements(By.CLASS_NAME, "w_900")[1].find_elements(By.TAG_NAME, "tr")
        count = 0
        user_id = ""
        user_dic = {}
        check_flg = False
        # 応募者ごとの情報をuser_dicに収集
        for tr in tr_tags:
            # ヘッダー情報はコンティニュー
            if len(tr.find_elements(By.TAG_NAME, "th")) != 0:
                continue
            count += 1

            if count == 1:
                print("--------------------")
                # ⑦応募者ID
                user_id = tr.find_element(By.CLASS_NAME, "no").text.strip()
                # ③採用ステータス
                status = Select(tr.find_element(By.CLASS_NAME, "job_adoptions__adoption_status_id")).first_selected_option.text
                # ④研修初日
                first_work = tr.find_element(By.CLASS_NAME, "job_adoptions__training_first_on").get_attribute("value")
                print(f"応募者ID:{user_id}\n"
                      f"採用ステータス:{status}\n"
                      f"研修初日:{first_work}")
                user_dic[user_id] = {"status": status, "first_work": first_work}
            elif count == 2:
                # ⑤在籍確認
                enrollment = ""
                if len(tr.find_elements(By.CLASS_NAME, "job_adoptions__belong_1month_enum")) > 0:
                    enrollment = Select(tr.find_element(By.CLASS_NAME, "job_adoptions__belong_1month_enum")).first_selected_option.text
                user_dic[user_id]["enrollment"] = enrollment
                print(f"在籍確認:{enrollment}")

            elif count == 3 and user_id not in user_id_ls:
                # 確認済みの為、処理実行せず
                user_id_ls.append(user_id)

                # ①採用お祝い
                recruit_celebration = tr.find_element(By.TAG_NAME, "td").text

                user_dic[user_id]["recruit_celebration"] = recruit_celebration
                # ②管理者用メモ
                admin_memo = tr.find_element(By.CLASS_NAME, "job_adoptions__remark_dummy").get_attribute("value")
                user_dic[user_id]["admin_memo"] = admin_memo

                # ⑥チェック要素
                check_element = tr.find_element(By.CLASS_NAME, "job_adoptions__admin_check_flag")
                print(f"採用お祝い:{recruit_celebration}\n"
                      f"管理者用メモ:{admin_memo}")

                flg = False
                try:
                    check_date = datetime.strptime(user_dic[user_id]["first_work"], "%Y/%m/%d")
                except:
                    check_date = user_dic[user_id]["first_work"]
                if user_dic[user_id]["status"] == "採用" and user_dic[user_id]["recruit_celebration"] == "" and user_dic[user_id][
                    "admin_memo"] == "":
                    if user_dic[user_id]["first_work"] != "" and user_dic[user_id]["enrollment"] == "" and check_date == "未定":
                        # ③採用　①空白　②空白　④未定　⑤空白の場合
                        flg = True
                    elif user_dic[user_id]["first_work"] != "" and (check_date.year > current_date.year or (
                            check_date.year == current_date.year and check_date.month >= current_date.month)) and \
                            user_dic[user_id]["enrollment"] == "":
                        # ③採用　①空白　②空白　④当月以降の日付が入ってる　⑤空白の場合
                        flg = True
                    elif user_dic[user_id]["first_work"] != "" and (current_date - relativedelta(months=1) >= check_date) and \
                            user_dic[user_id]["enrollment"] == "◯":
                        # ③採用　①空白　②空白　④該当の日付から実行日まで1ヵ月経っている　⑤〇の場合
                        flg = True
                elif user_dic[user_id]["status"] in ["保留", "不合格", "連絡取れず", "辞退", "欠席"] and user_dic[user_id][
                    "recruit_celebration"] == "" and user_dic[user_id]["admin_memo"] == "":
                    # ③保留・不合格・連絡取れず・辞退・欠席のいずれか　①空白　②空白
                    flg = True

                if flg:
                    # クリック処理
                    check_flg = True
                    check_element.click()
                    print(f"{user_id}:クリック実行")
                    # ログ保存
                    log_list.append([last_row, f"{current_date.year}/{current_date.month}/{current_date.day}", user_id, user_dic[user_id]["status"]])
                    last_row += 1

            if count >= 3:
                count = 0
                user_id = ""

        # 変更があった場合　変更を行う
        if check_flg:
            # 変更ボタンクリック
            driver.find_elements(By.CSS_SELECTOR, ".box-button.large")[1].find_element(By.TAG_NAME, "input").click()
            wait.until(EC.presence_of_all_elements_located)
            time.sleep(1)
            # 実行ボタンクリック
            driver.find_elements(By.CSS_SELECTOR, ".box-button.large")[0].find_element(By.TAG_NAME, "input").click()
            wait.until(EC.presence_of_all_elements_located)
            time.sleep(2.5)


        # 次のページがあるか
        if len(driver.find_elements(By.CLASS_NAME, "next_page")) > 0 and "disabled" not in driver.find_element(By.CLASS_NAME, "next_page").get_attribute("class"):
            driver.find_element(By.CLASS_NAME, "next_page").click()
        else:
            break



    # スプレッドシートの最終行に2次元配列を追加
    try:
        if len(log_list) > 0:
            # 追加
            worksheet.append_rows(log_list)
            # slackに通知
            requests.post(webhook, data=json.dumps({
                'text': u'@',  # 通知内容
                'username': u'@channel 採用確認の自動チェックが完了しました！\n下記よりご確認下さい。\nhttps://docs.google.com/spreadsheets/d/1wrMxZDxJPIadXV-hBNlAoTzdfm0Rzc03asJhHOrIcYs/edit#gid=0',  # ユーザー名
                'link_names': 1,  # 名前をリンク化
            }))

    except Exception as e:
        messagebox.showwarning("お知らせ", "スプレッドシートへの追記に失敗しました。")
        print(e)
        print("スプレッドシートへの追記に失敗")
        time.sleep(10)
        try:
            worksheet.append_rows(log_list)
        except:
            print("再度試行したが失敗")


    # チェック済みuser_idの保存
    f = open(f'{os.path.abspath(".")}\\log.txt', 'w')
    d = "\n".join(user_id_ls)
    f.write(d)
    f.close()
    # driverの終了
    driver.quit()

    print("実行終了")
    time.sleep(60)

