# utils\helpers.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import List
from .environment import EnvironmentUtils as env

def get_selected_tables_from_sheets() -> List[str]:
    """
    Googleスプレッドシートから「実行対象」がTRUEの物理テーブル名を取得します。

    Returns:
        List[str]: 実行対象の物理テーブル名リスト
    """
    try:
        # サービスアカウントのキーで認証
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        service_account_file = env.get_env_var("GCS_KEY_PATH")
        credentials = ServiceAccountCredentials.from_json_keyfile_name(service_account_file, scope)
        client = gspread.authorize(credentials)

        # スプレッドシートとシート名を取得
        spreadsheet_id = env.get_config_value("SPREADSHEET", "SSID")
        sheet_name = env.get_config_value("SPREADSHEET", "SHEETNAME")
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

        # シートのデータを取得
        data = sheet.get_all_records()
        
        # 「実行対象」が TRUE の物理テーブル名を抽出
        selected_tables = [row["物理テーブル名"] for row in data if str(row["実行対象"]).upper() == "TRUE"]
        
        return selected_tables

    except Exception as e:
        raise Exception(f"スプレッドシートからデータを取得中にエラーが発生しました: {e}")
