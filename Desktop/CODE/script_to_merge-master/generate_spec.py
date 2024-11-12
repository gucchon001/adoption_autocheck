import os
import logging
from typing import Optional
from openai import OpenAI
from utils import read_settings, read_file_safely, write_file_content

# ロガーの設定
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class SpecificationGenerator:
    """仕様書生成を管理するクラス"""

    def __init__(self):
        """設定を読み込んで初期化"""
        try:
            config = read_settings()
            # APIセクションから設定を読み込む
            self.api_key = config.get('openai_api_key', '')  # 設定キーを変更
            self.model = config.get('openai_model', 'gpt-4')  # 設定キーを変更
            self.temperature = 0.7  # デフォルト値として設定
            
            # ソースディレクトリの設定
            self.source_dir = config.get('source_directory', '.')
            self.document_dir = os.path.join(self.source_dir, 'document')

            # OpenAIクライアントを初期化
            self.client = OpenAI(api_key=self.api_key)

            logger.debug(f"SpecificationGenerator initialized with model: {self.model}")
        except KeyError as e:
            logger.error(f"設定ファイルに必要なキーがありません: {e}")
            raise
        except Exception as e:
            logger.error(f"SpecificationGeneratorの初期化に失敗しました: {e}")
            raise

    def generate(self) -> str:
        """仕様書を生成してファイルに保存"""
        try:
            code_content = self._read_merge_file()
            if not code_content:
                logger.error("コード内容が空です。")
                return ""

            prompt = self._generate_prompt(code_content)
            specification = self._get_ai_response(prompt)
            if not specification:
                return ""

            # 出力先をdocumentフォルダに設定
            output_path = os.path.join(self.document_dir, 'requirements_spec.txt')
            if write_file_content(output_path, specification):
                logger.info(f"仕様書が正常に出力されました: {output_path}")
                return output_path
            return ""
        except Exception as e:
            logger.error(f"仕様書生成中にエラーが発生しました: {e}")
            return ""

    def _read_merge_file(self) -> str:
        """merge.txt ファイルの内容を読み込む"""
        merge_path = os.path.join(self.document_dir, 'merge.txt')
        content = read_file_safely(merge_path)
        if content:
            logger.info("merge.txt の読み込みに成功しました。")
        else:
            logger.error("merge.txt の読み込みに失敗しました。")
        return content or ""

    def _generate_prompt(self, code_content: str) -> str:
        """AIに送信するプロンプトを生成"""
        return f"""以下のPythonコードを解析して、日本語で機能要件仕様書を作成してください。
# AIチャットアプリケーション機能要件仕様書
## 1. システム概要
## 2. 主要機能要件
## 3. 非機能要件
## 4. 技術要件

コード:
{code_content}"""

    def _get_ai_response(self, prompt: str) -> str:
        """OpenAI APIを使用して仕様書を生成"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "あなたは仕様書を作成するAIです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            logger.info("AI応答の取得に成功しました。")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI応答取得中にエラーが発生しました: {e}")
            return ""

def generate_specification() -> str:
    """generate_specification 関数"""
    generator = SpecificationGenerator()
    return generator.generate()

if __name__ == "__main__":
    generate_specification()