import os
import logging
from typing import Optional, Dict, List, Tuple
from openai import OpenAI
from utils import read_settings, read_file_safely, write_file_content

# モジュール固有のロガーを設定
logger = logging.getLogger(__name__)

class DetailedSpecificationGenerator:
    """詳細仕様書生成を管理するクラス"""

    def __init__(self):
        """設定を読み込んで初期化"""
        try:
            self.settings = read_settings()
            self.model = self.settings['openai_model']
            self.temperature = float(0.7)  # 固定値として設定
            self.source_dir = self.settings['source_directory']
            self.output_dir = os.path.join(self.source_dir, 'document')
            
            # OpenAIクライアントを初期化
            self.client = OpenAI(api_key=self.settings['openai_api_key'])
            
            logger.info("DetailedSpecificationGenerator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DetailedSpecificationGenerator: {e}")
            raise

    def _read_input_files(self) -> Optional[Tuple[str, str]]:
        """必要な入力ファイルを読み込む"""
        try:
            # merge.txtの読み込み
            merge_path = os.path.join(self.output_dir, 'merge.txt')
            merge_content = read_file_safely(merge_path)
            if merge_content is None:
                logger.error("Failed to read merge.txt")
                return None

            # requirements_spec.txtの読み込み
            spec_path = os.path.join(self.output_dir, 'requirements_spec.txt')
            spec_content = read_file_safely(spec_path)
            if spec_content is None:
                logger.error("Failed to read requirements_spec.txt")
                return None

            logger.info("Successfully read both input files")
            return merge_content, spec_content

        except Exception as e:
            logger.error(f"Error reading input files: {e}")
            return None

    def _generate_prompt(self, merge_content: str, spec_content: str) -> str:
        """AIに送信するプロンプトを生成"""
        return f"""以下の機能要件仕様書とソースコードを基に、より詳細なプログラム仕様書を作成してください。
出力は以下の形式に従い、具体的な実装詳細、データフロー、各モジュールの相互作用を含めてください：

# プログラム仕様書

## 1. システム概要
[システムの詳細な説明と全体アーキテクチャ]

## 2. ファイルごとの役割と詳細説明
[各ファイルの具体的な役割、機能、依存関係]

## 3. 関数ごとの役割と詳細説明
[各関数の入出力、処理内容、エラーハンドリング]

## 4. 非機能要件
[具体的な性能要件、セキュリティ要件、その他の技術要件]

## 5. 技術要件
[必要なライブラリのバージョン、環境設定、依存関係]

## 6. 使用手順と注意事項
[セットアップ手順、使用方法、既知の制限事項]

機能要件仕様書：
{spec_content}

ソースコード：
{merge_content}"""

    def _get_ai_response(self, prompt: str) -> Optional[str]:
        """OpenAI APIを使用して詳細仕様書を生成"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "あなたは優秀なソフトウェアアーキテクトです。コードと仕様書を解析して、"
                                 "実装の詳細まで踏み込んだ包括的なプログラム仕様書を作成することができます。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            logger.info("Successfully received AI response")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return None

    def generate(self) -> Optional[str]:
        """詳細仕様書を生成してファイルに保存"""
        try:
            # 入力ファイルを読み込み
            input_contents = self._read_input_files()
            if not input_contents:
                return None
                
            merge_content, spec_content = input_contents

            # プロンプトを生成
            prompt = self._generate_prompt(merge_content, spec_content)
            
            # AI応答を取得
            specification = self._get_ai_response(prompt)
            if not specification:
                return None

            # 詳細仕様書を保存
            output_path = os.path.join(self.output_dir, 'detailed_program_spec.txt')
            if write_file_content(output_path, specification):
                logger.info(f"Successfully wrote detailed specification to {output_path}")
                return output_path
            return None

        except Exception as e:
            logger.error(f"Error generating detailed specification: {e}")
            return None

    def validate_specification(self, spec_path: str) -> bool:
        """生成された詳細仕様書の妥当性を検証"""
        try:
            content = read_file_safely(spec_path)
            if not content:
                logger.error("Generated detailed specification is empty")
                return False

            # 必要なセクションの存在を確認
            required_sections = [
                "# プログラム仕様書",
                "## 1. システム概要",
                "## 2. ファイルごとの役割と詳細説明",
                "## 3. 関数ごとの役割と詳細説明",
                "## 4. 非機能要件",
                "## 5. 技術要件",
                "## 6. 使用手順と注意事項"
            ]

            for section in required_sections:
                if section not in content:
                    logger.error(f"Missing required section: {section}")
                    return False

            logger.info("Detailed specification validation successful")
            return True

        except Exception as e:
            logger.error(f"Error validating detailed specification: {e}")
            return False

def generate_detailed_specification() -> Optional[str]:
    """既存のコードとの互換性のための関数"""
    try:
        generator = DetailedSpecificationGenerator()
        spec_path = generator.generate()
        
        if spec_path and generator.validate_specification(spec_path):
            logger.info("Detailed specification generation completed successfully")
            return spec_path
        else:
            logger.error("Detailed specification generation failed or validation failed")
            return None
            
    except Exception as e:
        logger.error(f"Error in detailed specification generation: {e}")
        return None

def main():
    return generate_detailed_specification() is not None

if __name__ == "__main__":
    main()