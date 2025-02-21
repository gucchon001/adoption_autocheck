# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 20:13:26 2020

@author: tmnk015
"""

from selenium import webdriver
import chromedriver_binary #これを書いとくとdriverのパスが通せるらしい。アラートでるが大丈夫。

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd
import time
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

"""パラメータの読み込み"""

para_path = r"\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\採用確認自動チェック\パラメータ.csv"
para_df = pd.read_csv(para_path,encoding='cp932')


#各データのセット
url = para_df["値"][0]
sp_id = para_df["値"][1]
slack_webhock = para_df["値"][2]
BasicId = para_df["値"][3]
BasicPw = para_df["値"][4]
LoginId = para_df["値"][5]
LoginPw = para_df["値"][6]
yobi1 = para_df["値"][7]










#謎エラーを無視するオプションを入れておく
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument('--headless')
driver = webdriver.Chrome(chrome_options=options)

driver.command_executor._commands["send_command"] = (
  'POST',
  '/session/$sessionId/chromium/send_command'
)
driver.execute(
  "send_command",
  params={
    'cmd': 'Page.setDownloadBehavior',
    'params': { 'behavior': 'allow', 'downloadPath': r'C:\Users\tmnk015\Downloads' }
  }
)

url = 'https://tomonokai:hCR1xZrkycs0XOVa@www.juku.st/admin/login'
driver.get(url)

#指定した要素が表示されるまで、明示的に30秒待機する
loginID = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.NAME, 'login'))
)
loginID.send_keys('kataoka')

password =  driver.find_element_by_xpath('//*[@id="password"]')
password.send_keys('hjbsrfhr')

loginbtn =driver.find_element_by_xpath('//*[@id="login"]/form/p[4]/input')
loginbtn.click()

#契約更新管理ページに移動
contract_dir = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="sub"]/div/ul[2]/li[3]/a'))
)
contract_dir.click()

#全件ダウンロード
contract_company = WebDriverWait(driver, 30).until(
	EC.visibility_of_element_located((By.XPATH, '//*[@id="main"]/form/div/input[2]'))
)
contract_company.click()


time.sleep(40)

driver.quit()


#ダウンロードしたファイルの移動


dl_path = r"C:\Users\tmnk015\Downloads"
moveto = r"\\nas\public\事務業務資料\300_講師求人部門\81講師求人DB\BPR用\元データ\03.塾向けメルマガ\元データ\契約データ"


dl_files = os.listdir(dl_path)
dl_files_file = [f for f in dl_files if os.path.isfile(os.path.join(dl_path, f))]


today = datetime.today()
passdate = datetime.strftime(today, '%Y%m%d')
passdate2 = datetime.strftime(today, '%Y-%m-%d')

contracts_csv = [s for s in dl_files_file if 'contracts' in s]
contracts_csv = [k for k in contracts_csv if passdate in k]

pathbar = '\\'
contracts_csv_path = dl_path + pathbar + contracts_csv[len(contracts_csv)-1]
new_contracts_csv_path = moveto + pathbar + 'contracts_' + passdate2 + '.csv'

import shutil

new_path = shutil.move(contracts_csv_path, new_contracts_csv_path)



contracts_df = pd.read_csv(new_contracts_csv_path,encoding='cp932')


print(contracts_df)


"""ここからスプレッドシートを操作しシートに張り付ける"""

 

#2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

#認証情報設定
#ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
json_file = r"\\nas\public\事務業務資料\100000管理部門\101000システム\事業部プログラム\講師求人部門\塾向けメルマガ\dataapp-282609-b2b0ec9574b8.json"
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)

#OAuth2の資格情報を使用してGoogle APIにログインします。
gc = gspread.authorize(credentials)

workbook = gc.open_by_key('1B9Y7aC6MczxuxG4u33FJ2ObHcbu9-Hvt71a_R-cBAo4')
worksheet = workbook.worksheet('シート1')

#既存データの数を取得
col_list = worksheet.col_values(1)
data_count = len(col_list)


#セット範囲を作成する
base_data_length= len(contracts_df)
data_range = 'A2' + ':I' + str(base_data_length+1)


#後は既存のデータ数と、格納データ数を使って、A1:B10形式でデータのセット範囲を取得、
#その範囲にデータを指定（先頭列を削除）、で完了

cell_list = worksheet.range(data_range)

#int型があると貼り付けできないので変更
contracts_df['企業ID'] = contracts_df['企業ID'].astype(str)
contracts_df['契約金額'] = contracts_df['契約金額'].astype(str)

contracts_df = contracts_df.fillna('データなし')

for cell in cell_list:
    val = contracts_df.iloc[cell.row - (data_count+1)][cell.col - 1]
    cell.value = val

worksheet.update_cells(cell_list,value_input_option='USER_ENTERED')

print("データの貼り付けが完了しました。")






