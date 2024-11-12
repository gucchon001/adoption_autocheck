#merge_files.py
from typing import Optional, List
import logging
import os
import fnmatch
import configparser
import utils

# モジュールレベルのロガー設定
logger = logging.getLogger(__name__)

class PythonFileMerger:
    def __init__(self, settings_path: str = 'settings.ini'):
        """INI設定を読み込んでマージャーを初期化"""
        try:
            self.settings = utils.read_settings(settings_path)
            self.project_dir = os.path.abspath(self.settings['source_directory'])
            
            # 出力ディレクトリを設定（documentフォルダ）
            self.output_dir = os.path.join(self.project_dir, 'document')
            self.output_filename = self.settings['output_file']
            
            # documentディレクトリが存在しない場合は作成
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            
            # 除外パターンをリストに変換
            self.exclude_patterns = [
                pattern.strip() for pattern in self.settings['exclusions'].split(',')
                if pattern.strip()
            ]
            
            # ログ出力
            logger.info(f"Initialized with project_dir: {self.project_dir}")
            logger.info(f"Output directory: {self.output_dir}")
            logger.info(f"Output file: {os.path.join(self.output_dir, self.output_filename)}")
            logger.info(f"Exclude patterns: {self.exclude_patterns}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PythonFileMerger: {str(e)}")
            raise

    def _should_exclude(self, path: str) -> bool:
        """パスが除外パターンに一致するかチェック"""
        try:
            name = os.path.basename(path)
            path_parts = path.split(os.sep)
            
            for pattern in self.exclude_patterns:
                pattern = pattern.strip()
                if any(fnmatch.fnmatch(part, pattern) for part in path_parts):
                    return True
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error in _should_exclude for path {path}: {str(e)}")
            return True

    def _get_directory_structure(self, startpath: str) -> str:
        """ディレクトリ構造を文字列として取得"""
        try:
            tree_str = "# Directory Structure\n\n"
            
            # ルートディレクトリ名を表示
            tree_str += f"{os.path.basename(startpath)}/\n"
            
            root_files = []
            sub_dirs = []
            
            # ルートディレクトリのファイルとサブディレクトリを収集
            for item in sorted(os.listdir(startpath)):
                item_path = os.path.join(startpath, item)
                if os.path.isfile(item_path):
                    root_files.append(item)
                elif os.path.isdir(item_path):
                    sub_dirs.append(item)
            
            # ルートディレクトリのファイルを表示（Pythonファイルを先に）
            python_files = sorted(f for f in root_files if f.endswith('.py'))
            other_files = sorted(f for f in root_files if not f.endswith('.py'))
            
            for f in python_files + other_files:
                tree_str += f"    {f}\n"
            
            # サブディレクトリを処理
            for dirname in sorted(sub_dirs):
                dirpath = os.path.join(startpath, dirname)
                tree_str += f"    {dirname}/\n"
                
                # 除外対象のディレクトリの場合
                if self._should_exclude(dirpath):
                    tree_str += "        (skipped directory contents)\n"
                    continue
                
                # 除外対象でない場合はPythonファイルを表示
                python_files = []
                for root, _, files in os.walk(dirpath):
                    if root == dirpath:  # 直接の子ファイルのみを処理
                        python_files.extend(
                            f for f in sorted(files)
                            if f.endswith('.py') and not self._should_exclude(os.path.join(root, f))
                        )
                
                for f in python_files:
                    tree_str += f"        {f}\n"
            
            return f"{tree_str}\n{'=' * 80}\n"
                
        except Exception as e:
            logger.error(f"Error in _get_directory_structure: {str(e)}")
            return "# Error generating directory structure\n\n"

    def _format_file_content(self, filename: str, content: str) -> str:
        """ファイル内容のフォーマット"""
        separator = "=" * 80
        return f"""
{separator}
File: {filename}
{separator}

{content}

"""

    def process(self) -> Optional[str]:
        """ファイルマージ処理を実行"""
        try:
            # Pythonファイルを収集（除外パターンを考慮）
            python_files = utils.get_python_files(self.project_dir, self.exclude_patterns)
            
            if not python_files:
                logger.warning(f"No Python files found in {self.project_dir}")
                return None

            logger.info(f"Found {len(python_files)} Python files to process")
            
            # ディレクトリ構造を追加
            merged_content = "# Merged Python Files\n\n"
            merged_content += self._get_directory_structure(self.project_dir)
            
            # ファイル内容を追加
            processed_count = 0
            total_files = len(python_files)
            
            for rel_path, filepath in sorted(python_files):
                content = utils.read_file_safely(filepath)
                if content is not None:
                    formatted_content = self._format_file_content(rel_path, content)
                    merged_content += formatted_content
                    processed_count += 1
                else:
                    logger.warning(f"Skipped file due to read error: {rel_path}")

            output_path = os.path.join(self.output_dir, self.output_filename)
            logger.info(f"Writing output to: {os.path.abspath(output_path)}")
            
            # UTF-8でファイルを書き込み
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(merged_content)
                logger.info(f"Successfully wrote merged content to {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Failed to write output file: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"Error during file merge operation: {str(e)}")
            return None

def merge_py_files() -> Optional[str]:
    """マージ処理のエントリーポイント"""
    try:
        logger.info("Starting Python files merge process")
        merger = PythonFileMerger()
        merged_file_path = merger.process()
        
        if merged_file_path:
            logger.info(f"File merge completed successfully. Output file: {os.path.abspath(merged_file_path)}")
            return merged_file_path
        else:
            logger.error("File merge failed")
            return None
            
    except Exception as e:
        logger.error(f"Error in merge operation: {str(e)}")
        return None