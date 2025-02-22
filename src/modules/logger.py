from datetime import datetime
from typing import List, Dict
from ..utils.environment import EnvironmentUtils as env

class Logger:
    def __init__(self, spreadsheet):
        """
        ログ記録機能を管理するクラス
        
        Args:
            spreadsheet: SpreadSheetクラスのインスタンス
        """
        self.spreadsheet = spreadsheet
        
    def log_applicants(self, applicants_data: List[Dict]) -> bool:
        """
        応募者データをスプレッドシートに記録
        
        Args:
            applicants_data: 記録する応募者データのリスト
            
        Returns:
            bool: 記録成功時True、失敗時False
        """
        try:
            print("\n=== ログ記録処理開始 ===")
            if not applicants_data:
                print("記録対象のデータがありません")
                return True

            # パターン99の制御設定を読み込み
            include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)
            
            # パターン99のフィルタリング
            filtered_data = [
                data for data in applicants_data
                if data.get('pattern') != '99' or include_pattern_99
            ]

            if not filtered_data:
                print("記録対象のデータがありません（パターン99フィルター後）")
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
                    applicant.get('oiwai', ''),     # お祝いフラグ
                    applicant.get('remark', ''),    # 備考
                    applicant['training_start_date'],  # 研修初日
                    applicant['zaiseki'],   # 在籍確認
                    applicant.get('confirm_checkbox', ''),     # 確認完了チェックボックス
                    applicant.get('confirm_onoff', '')        # 更新反映状態
                ]
                for i, applicant in enumerate(filtered_data)
            ]

            # スプレッドシートに追加
            try:
                self.spreadsheet.sheet.append_rows(log_data)
                print(f"✅ {len(filtered_data)}件のデータを記録しました")
                return True
            except Exception as e:
                print(f"データの追加に失敗: {str(e)}")
                # 1回だけリトライ
                try:
                    self.spreadsheet.sheet.append_rows(log_data)
                    print("✅ リトライ成功")
                    return True
                except Exception as e:
                    print(f"❌ リトライも失敗: {str(e)}")
                    return False

        except Exception as e:
            print(f"❌ ログ記録処理でエラー: {str(e)}")
            return False 