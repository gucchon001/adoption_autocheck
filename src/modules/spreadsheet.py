from pathlib import Path
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from typing import List, Dict, Optional

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
            
            try:
                # 既存のシートを開く
                self.sheet = workbook.worksheet('exe_logsheet')
            except gspread.exceptions.WorksheetNotFound:
                # シートが存在しない場合は新規作成
                print("exe_logsheetが存在しないため、新規作成します")
                self.sheet = workbook.add_worksheet('exe_logsheet', 1000, 10)  # 1000行、10列
                
                # ヘッダーの設定
                headers = [
                    "No",
                    "実行日",
                    "応募ID",
                    "採用ステータス",
                    "パターン",
                    "お祝いフラグ",
                    "備考",
                    "研修初日",
                    "在籍確認",
                    "確認完了チェックボックス",
                    "更新反映"  # 新しい列を追加
                ]
                self.sheet.append_row(headers)
            
            return True
            
        except Exception as e:
            print(f"スプレッドシートへの接続に失敗: {str(e)}")
            return False

    def append_logs(self, applicants: List[Dict]) -> bool:
        """
        応募者情報のログをスプレッドシートに追加します。

        Args:
            applicants (List[Dict]): 応募者情報のリスト
                {
                    'id': str,          # 応募者ID
                    'status': str,      # ステータス
                    'pattern': str,     # パターン
                    'oiwai': str,       # お祝いフラグ
                    'remark': str,      # 備考
                    'training_start_date': str,  # 研修初日
                    'zaiseki': str,      # 在籍確認
                    'confirm_checkbox': str       # 確認完了チェックボックス
                }

        Returns:
            bool: 追加成功したかどうか
        """
        try:
            if not applicants:
                return True

            # 現在の行数を取得
            last_row = len(self.sheet.col_values(1))
            
            # 現在の日時
            now = datetime.now()
            current_date = f"{now.year}/{now.month}/{now.day}"
            
            # ログデータの作成
            log_data = [
                [
                    last_row + i + 1,      # No
                    current_date,           # 実行日
                    applicant['id'],        # 応募ID
                    applicant['status'],    # 採用ステータス
                    applicant['pattern'],   # パターン
                    applicant['oiwai'],     # お祝いフラグ
                    applicant['remark'],    # 備考
                    applicant['training_start_date'],  # 研修初日
                    applicant['zaiseki'],   # 在籍確認
                    applicant['confirm_checkbox'],     # 確認完了チェックボックス
                    applicant['confirm_onoff']         # 更新反映状態を追加
                ]
                for i, applicant in enumerate(applicants)
            ]

            # スプレッドシートに追加
            self.sheet.append_rows(log_data)
            return True

        except Exception as e:
            print(f"ログの追加に失敗: {str(e)}")
            # 1回だけリトライ
            try:
                self.sheet.append_rows(log_data)
                return True
            except:
                print("再試行も失敗しました")
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