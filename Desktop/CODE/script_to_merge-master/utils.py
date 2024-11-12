import os
import logging
import fnmatch
import configparser
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

def normalize_path(path: str) -> str:
    """パスを正規化"""
    return os.path.normpath(path).replace('\\', '/')

def read_settings(settings_path: str = 'settings.ini') -> dict:
    """設定ファイルを読み込む"""
    try:
        config = configparser.ConfigParser()
        
        # デフォルト設定
        default_settings = {
            'source_directory': '.',
            'output_file': 'merge.txt',
            'exclusions': 'myenv,*__pycache__*,sample_file,*.log',
            'openai_api_key': '',
            'openai_model': 'gpt-4'
        }
        
        if os.path.exists(settings_path):
            config.read(settings_path, encoding='utf-8')
            settings = {
                'source_directory': config['DEFAULT'].get('SourceDirectory', default_settings['source_directory']),
                'output_file': config['DEFAULT'].get('OutputFile', default_settings['output_file']),
                'exclusions': config['DEFAULT'].get('Exclusions', default_settings['exclusions']).replace(' ', '')
            }
            
            # APIセクションの設定を読み込む
            if 'API' in config:
                settings['openai_api_key'] = config['API'].get('openai_api_key', default_settings['openai_api_key'])
                settings['openai_model'] = config['API'].get('openai_model', default_settings['openai_model'])
            else:
                logger.warning("API section not found in settings.ini")
                settings.update({
                    'openai_api_key': default_settings['openai_api_key'],
                    'openai_model': default_settings['openai_model']
                })
        else:
            logger.warning(f"Settings file not found at {settings_path}, using default settings")
            settings = default_settings
        
        # APIキーの存在確認
        if not settings['openai_api_key']:
            logger.error("OpenAI API key is not set in settings.ini")
        
        return settings
    except Exception as e:
        logger.error(f"Error reading settings file {settings_path}: {str(e)}")
        return default_settings

def write_file_content(filepath: str, content: str) -> bool:
    """ファイルに内容を書き込む"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Error writing to file {filepath}: {str(e)}")
        return False

def read_file_safely(filepath: str) -> Optional[str]:
    """ファイルを安全に読み込む"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='cp932') as f:
                content = f.read()
                return content
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {str(e)}")
        return None

def get_python_files(directory: str, exclude_patterns: List[str]) -> List[Tuple[str, str]]:
    """指定ディレクトリ配下のPythonファイルを取得"""
    python_files = []
    
    try:
        for root, dirs, files in os.walk(directory):
            # ディレクトリ名を基にした除外チェック
            dir_name = os.path.basename(root)
            should_skip = any(
                fnmatch.fnmatch(dir_name, pattern.strip())
                for pattern in exclude_patterns
            )
            
            if should_skip:
                dirs.clear()  # サブディレクトリの走査をスキップ
                continue
            
            # 除外パターンに一致するディレクトリを削除
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, pattern.strip())
                for pattern in exclude_patterns
            )]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                # ファイル名を基にした除外チェック
                if any(fnmatch.fnmatch(file, pattern.strip()) for pattern in exclude_patterns):
                    continue
                
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, directory)
                python_files.append((rel_path, filepath))
        
        return sorted(python_files)
        
    except Exception as e:
        logger.error(f"Error getting Python files from {directory}: {str(e)}")
        return []