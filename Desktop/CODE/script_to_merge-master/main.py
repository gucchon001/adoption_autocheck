import os
import sys
import traceback
from merge_files import merge_py_files
from generate_spec import generate_specification
from generate_detailed_spec import generate_detailed_specification
from check_refactoring import generate_refactoring_suggestions
from logging_config import setup_logging
import logging
import argparse

logger = logging.getLogger(__name__)

def main():
    try:
        # コマンドライン引数の解析
        parser = argparse.ArgumentParser(description='Python Files Processor')
        parser.add_argument('--debug', action='store_true', help='デバッグモードを有効化')
        args = parser.parse_args()

        # ロギング設定を初期化
        setup_logging(debug_mode=args.debug)
        logger.info("Application started")
        
        functions = {
            "1": lambda: (merge_py_files(), generate_specification(), 
                         generate_detailed_specification(), generate_refactoring_suggestions()),
            "2": merge_py_files,
            "3": generate_specification,
            "4": generate_detailed_specification,
            "5": generate_refactoring_suggestions
        }
        
        print("実行したい機能を選択してください:")
        print("1. 全てを順に実行")
        print("2. merge.txt の生成")
        print("3. 仕様書の作成")
        print("4. 詳細なプログラム仕様書の作成")
        print("5. リファクタリングチェック")
        
        choice = input("選択 (1, 2, 3, 4 または 5): ").strip()
        logger.debug(f"選択された機能: {choice}")
        
        if choice in functions:
            try:
                logger.info(f"機能{choice}の実行開始")
                result = functions[choice]()
                logger.info(f"機能{choice}の実行完了")
                print("\n処理が正常に完了しました。")
                if result:
                    print(f"処理結果: {result}")
            except Exception as e:
                error_info = traceback.format_exc()
                logger.error(f"Error during execution: {str(e)}\n{error_info}")
                print(f"エラーが発生しました: {e}")
        else:
            print("無効な選択です。")
            
    except Exception as e:
        error_info = traceback.format_exc()
        logger.error(f"Critical error: {str(e)}\n{error_info}")
        print(f"重大なエラーが発生しました: {e}")

if __name__ == "__main__":
    logger.debug(f"Pythonバージョン: {sys.version}")
    logger.debug(f"実行パス: {os.path.abspath(__file__)}")
    main()