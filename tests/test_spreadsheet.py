import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from src.modules.spreadsheet import SpreadSheet
from src.utils.environment import EnvironmentUtils as env

def test_spreadsheet_connection():
    """スプレッドシートへの接続テスト"""
    # テスト環境の環境変数をロード
    env.load_env(test_mode=True)
    
    # 設定の読み込み
    credentials_path = env.get_service_account_file()
    spreadsheet_key = env.get_env_var("SPREADSHEET_KEY")
    
    print(f"認証情報ファイル: {credentials_path}")
    print(f"スプレッドシートキー: {spreadsheet_key}")
    
    # SpreadSheetクラスのインスタンス化
    spreadsheet = SpreadSheet(credentials_path, spreadsheet_key)
    
    # 接続テスト
    assert spreadsheet.connect() is True, "スプレッドシートへの接続に失敗"
    
    # シートの存在確認
    assert spreadsheet.sheet is not None, "シートの取得に失敗"
    assert spreadsheet.sheet.title == "exe_logsheet", "シート名が一致しない"

def test_append_logs():
    """ログ追加機能のテスト"""
    # テスト環境の環境変数をロード
    env.load_env(test_mode=True)
    
    # SpreadSheetクラスの準備
    credentials_path = env.get_service_account_file()
    spreadsheet_key = env.get_env_var("SPREADSHEET_KEY")
    spreadsheet = SpreadSheet(credentials_path, spreadsheet_key)
    spreadsheet.connect()
    
    # テストデータ
    test_applicants = [
        {
            'id': 'TEST001',
            'status': 'テスト',
            'training_date': '2024/03/01',
            'attendance_check': '〇',
            'celebration_sent': '',
            'admin_memo': '',
            'check_result': 'テスト実行'
        }
    ]
    
    # 追加前の行数を取得
    initial_rows = spreadsheet.get_last_row()
    
    # ログの追加
    assert spreadsheet.append_logs(test_applicants) is True, "ログの追加に失敗"
    
    # 追加後の行数を確認
    final_rows = spreadsheet.get_last_row()
    assert final_rows == initial_rows + 1, "行数が正しく増加していない"

def test_empty_applicants():
    """空のデータ追加テスト"""
    # テスト環境の環境変数をロード
    env.load_env(test_mode=True)
    
    credentials_path = env.get_service_account_file()
    spreadsheet_key = env.get_env_var("SPREADSHEET_KEY")
    spreadsheet = SpreadSheet(credentials_path, spreadsheet_key)
    spreadsheet.connect()
    
    # 空のリストを追加
    assert spreadsheet.append_logs([]) is True, "空リストの追加でエラー"

if __name__ == "__main__":
    print("スプレッドシートの接続テストを開始します...")
    
    try:
        test_spreadsheet_connection()
        print("接続テスト: OK")
        
        test_append_logs()
        print("ログ追加テスト: OK")
        
        test_empty_applicants()
        print("空データテスト: OK")
        
        print("全てのテストが成功しました！")
        
    except Exception as e:
        print(f"テスト失敗: {str(e)}") 