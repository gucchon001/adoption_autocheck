from pathlib import Path
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import List, Dict, Optional
from ..utils.environment import EnvironmentUtils as env

class SpreadSheet:
    def __init__(self, credentials_path: Path, spreadsheet_key: str):
        """
        Args:
            credentials_path (Path): サービスアカウントの認証情報JSONファイルのパス
            spreadsheet_key (str): スプレッドシートのキー
        """
        self.credentials_path = credentials_path
        self.spreadsheet_key = spreadsheet_key
        self.client = None
        self.sheet = None

    def connect(self) -> bool:
        """
        スプレッドシートに接続します。シートが存在しない場合は作成します。

        Returns:
            bool: 接続成功したかどうか
        """
        try:
            # APIスコープの設定
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # 認証情報の設定
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                str(self.credentials_path), scope
            )
            
            # クライアントの初期化
            self.client = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            workbook = self.client.open_by_key(self.spreadsheet_key)
            
            # 設定ファイルからシート名を取得
            sheet_name = env.get_config_value('SPREADSHEET', 'sheet_name', 'exe_logsheet')
            
            try:
                # 既存のシートを開く
                self.sheet = workbook.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                # シートが存在しない場合は新規作成
                print(f"{sheet_name}が存在しないため、新規作成します")
                
                # 設定ファイルから新規シート作成時の設定を取得
                new_sheet_name = env.get_config_value('SPREADSHEET', 'new_sheet_name', sheet_name)
                new_sheet_rows = env.get_config_value('SPREADSHEET', 'new_sheet_rows', 1000)
                new_sheet_cols = env.get_config_value('SPREADSHEET', 'new_sheet_cols', 10)
                
                self.sheet = workbook.add_worksheet(new_sheet_name, new_sheet_rows, new_sheet_cols)
                
                # ヘッダーの設定
                headers = [
                    "No",
                    "実行日",
                    "応募ID",
                    "採用ステータス",
                    "パターン",
                    "パターン判定理由",
                    "お祝いフラグ",
                    "備考",
                    "研修初日",
                    "在籍確認",
                    "確認完了チェックボックス",
                    "更新反映"
                ]
                self.sheet.append_row(headers)
            
            return True
            
        except Exception as e:
            print(f"スプレッドシートへの接続に失敗: {str(e)}")
            return False

    def get_last_row(self) -> Optional[int]:
        """
        スプレッドシートの最終行を取得します。

        Returns:
            Optional[int]: 最終行の番号。エラー時はNone
        """
        try:
            return len(self.sheet.col_values(1))
        except Exception as e:
            print(f"最終行の取得に失敗: {str(e)}")
            return None 