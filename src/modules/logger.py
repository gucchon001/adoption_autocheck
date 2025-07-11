from datetime import datetime
from typing import List, Dict
from src.utils.environment import EnvironmentUtils as env
import traceback
from src.utils.logging_config import get_logger
import gspread
from google.oauth2 import service_account

class Logger:
    def __init__(self, spreadsheet):
        """
        ログ記録機能を管理するクラス
        
        Args:
            spreadsheet: SpreadSheetクラスのインスタンス
        """
        self.spreadsheet = spreadsheet
        self.logger = get_logger(__name__)
        
    def log_applicants(self, applicants_data: List[Dict]) -> bool:
        """
        応募者データをスプレッドシートに記録（一括処理用）
        
        Args:
            applicants_data: 記録する応募者データのリスト
            
        Returns:
            bool: 記録成功時True、失敗時False
        """
        try:
            self.logger.info("\n=== ログ記録処理開始 ===")
            if not applicants_data:
                self.logger.info("記録対象のデータがありません")
                return True

            # スプレッドシートの接続確認
            if not self.spreadsheet or not self.spreadsheet.sheet:
                self.logger.error("❌ スプレッドシートが初期化されていません")
                return False

            # パターン99の制御設定を読み込み
            include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)
            
            # パターン99のフィルタリング（文字列比較）
            filtered_data = [
                data for data in applicants_data
                if data.get('pattern') != '99' or include_pattern_99
            ]

            if not filtered_data:
                self.logger.info("記録対象のデータがありません（パターン99フィルター後）")
                return True

            # 現在の日時を取得
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 現在の行数を取得
            last_row = len(self.spreadsheet.sheet.col_values(1))
            
            # ログデータの作成
            log_data = [
                [
                    last_row + i + 1,      # No
                    current_date,           # 実行日
                    applicant['id'],        # 応募ID
                    applicant['status'],    # 採用ステータス
                    applicant.get('pattern', ''),   # パターン
                    applicant.get('pattern_reason', ''),    # パターン判定理由
                    applicant.get('oiwai', ''),     # お祝いフラグ
                    applicant.get('memo', ''),      # 備考
                    applicant['training_start_date'],  # 研修初日
                    applicant['zaiseki'],   # 在籍確認
                    applicant.get('confirm_checkbox', ''),     # 確認完了チェックボックス
                    applicant.get('confirm_onoff', '')        # 更新反映状態
                ]
                for i, applicant in enumerate(filtered_data)
            ]
            
            # デバッグ情報
            for i, applicant in enumerate(filtered_data):
                self.logger.info(f"DEBUG: logger.py:log_applicants - 応募ID: {applicant['id']} のデータ:")
                self.logger.info(f"  - パターン: {applicant.get('pattern', '未設定')}")
                self.logger.info(f"  - パターン判定理由: {applicant.get('pattern_reason', '未設定')}")
                self.logger.info(f"  - お祝いフラグ: {applicant.get('oiwai', '未設定')}")
                self.logger.info(f"  - ステータス: {applicant.get('status', '未設定')}")
            
            # スプレッドシートに追加
            try:
                self.spreadsheet.sheet.append_rows(log_data)
                self.logger.info(f"✅ {len(filtered_data)}件のデータを記録しました")
                return True
            except Exception as e:
                self.logger.error(f"データの追加に失敗: {str(e)}")
                # 1回だけリトライ
                try:
                    self.spreadsheet.sheet.append_rows(log_data)
                    self.logger.info("✅ リトライ成功")
                    return True
                except Exception as e:
                    self.logger.error(f"❌ リトライも失敗: {str(e)}")
                    return False

        except Exception as e:
            self.logger.error(f"❌ ログ記録処理でエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return False
            
    def log_single_applicant(self, applicant_data: Dict) -> bool:
        """
        単一の応募者データをスプレッドシートに記録（応募IDごとの処理用）
        
        Args:
            applicant_data: 記録する応募者データ
            
        Returns:
            bool: 記録成功時True、失敗時False
        """
        try:
            app_id = applicant_data.get('id', '不明')
            pattern = applicant_data.get('pattern', '未設定')
            
            # 必ず出力されるデバッグ情報
            self.logger.info(f"\n=== 応募ID: {app_id} のログ記録処理開始 ===")
            self.logger.info(f"STEP1: 受信データ確認 - パターン: {pattern} (型: {type(pattern)})")
            
            # スプレッドシートの接続確認
            if not self.spreadsheet or not hasattr(self.spreadsheet, 'sheet') or self.spreadsheet.sheet is None:
                self.logger.error("❌ スプレッドシートが初期化されていません")
                return False
            
            # パターン99の制御設定を読み込み
            include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)
            self.logger.info(f"STEP2: 設定確認 - include_pattern_99: {include_pattern_99} (型: {type(include_pattern_99)})")
            
            # デバッグ: パターン99の設定値と判定を出力
            if applicant_data.get('pattern') == '99':
                self.logger.info(f"STEP3: パターン99検出 - 応募ID: {applicant_data['id']}")
                self.logger.info(f"  - include_pattern_99設定値: {include_pattern_99} (型: {type(include_pattern_99)})")
                self.logger.info(f"  - パターン値: {applicant_data.get('pattern')} (型: {type(applicant_data.get('pattern'))})")
            
            # パターン99の場合はスキップ（文字列比較）
            if applicant_data.get('pattern') == '99' and not include_pattern_99:
                self.logger.info("STEP4: パターン99のため記録をスキップします")
                return True
            elif applicant_data.get('pattern') == '99' and include_pattern_99:
                self.logger.info("STEP4: パターン99ですが、include_pattern_99=Trueのため記録を続行します")
            else:
                self.logger.info(f"STEP4: パターン{pattern}のため記録を続行します")
                
            # 現在の日時を取得
            now = datetime.now()
            current_date = now.strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                # 現在の行数を取得
                last_row = len(self.spreadsheet.sheet.col_values(1))
            except Exception as e:
                self.logger.error(f"行数の取得に失敗: {str(e)}")
                last_row = 1  # エラー時はデフォルト値を使用
            
            # ログデータの作成
            log_data = [
                [
                    last_row + 1,      # No
                    current_date,      # 実行日
                    applicant_data['id'],        # 応募ID
                    applicant_data['status'],    # 採用ステータス
                    applicant_data.get('pattern', ''),   # パターン
                    applicant_data.get('pattern_reason', ''),    # パターン判定理由
                    applicant_data.get('oiwai', ''),     # お祝いフラグ
                    applicant_data.get('memo', ''),      # 備考
                    applicant_data['training_start_date'],  # 研修初日
                    applicant_data['zaiseki'],   # 在籍確認
                    applicant_data.get('confirm_checkbox', ''),     # 確認完了チェックボックス
                    applicant_data.get('confirm_onoff', '')        # 更新反映状態
                ]
            ]
            
            # デバッグ情報
            self.logger.info(f"DEBUG: logger.py:log_single_applicant - 応募ID: {applicant_data['id']} のデータ:")
            self.logger.info(f"  - パターン: {applicant_data.get('pattern', '未設定')}")
            self.logger.info(f"  - パターン判定理由: {applicant_data.get('pattern_reason', '未設定')}")
            self.logger.info(f"  - お祝いフラグ: {applicant_data.get('oiwai', '未設定')}")
            self.logger.info(f"  - ステータス: {applicant_data.get('status', '未設定')}")
            
            # スプレッドシートに追加
            try:
                self.spreadsheet.sheet.append_rows(log_data)
                self.logger.info(f"✅ 応募ID: {applicant_data.get('id', '不明')} のデータを記録しました")
                return True
            except Exception as e:
                self.logger.error(f"データの追加に失敗: {str(e)}")
                # 1回だけリトライ
                try:
                    self.spreadsheet.sheet.append_rows(log_data)
                    self.logger.info("✅ リトライ成功")
                    return True
                except Exception as e:
                    self.logger.error(f"❌ リトライも失敗: {str(e)}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ 単一応募者データのログ記録処理でエラー: {str(e)}")
            traceback.print_exc()  # スタックトレースを出力
            return False

    def connect(self) -> bool:
        """
        スプレッドシートに接続します。
        
        Returns:
            bool: 接続成功時True、失敗時False
        """
        try:
            # 既に接続済みの場合は成功を返す
            if hasattr(self, 'sheet') and self.sheet is not None:
                return True
            
            # 認証情報の読み込み
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # クライアントの初期化
            client = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            spreadsheet = client.open_by_key(self.spreadsheet_key)
            
            # 最初のシートを選択
            self.sheet = spreadsheet.get_worksheet(0)
            
            return True
        except Exception as e:
            print(f"スプレッドシートへの接続に失敗: {str(e)}")
            return False 