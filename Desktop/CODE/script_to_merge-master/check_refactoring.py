import os
import logging
from typing import Optional, Dict, List
from openai import OpenAI
from utils import read_settings, read_file_safely, write_file_content

# モジュール固有のロガーを設定
logger = logging.getLogger(__name__)

class RefactoringChecker:
    """コードのリファクタリング提案を管理するクラス"""

    def __init__(self):
        """設定を読み込んで初期化"""
        try:
            self.settings = read_settings()
            self.model = self.settings['openai_model']        # キー名を変更
            self.temperature = float(0.7)  # 固定値として設定
            self.output_dir = os.path.join(self.settings['source_directory'], 'document')  # 出力ディレクトリのパスを修正
            
            # OpenAIクライアントを初期化
            self.client = OpenAI(api_key=self.settings['openai_api_key'])
            
            logger.info("RefactoringChecker initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RefactoringChecker: {e}")
            raise

    def _read_merge_file(self) -> Optional[str]:
        """マージされたファイルを読み込む"""
        try:
            merge_path = os.path.join(self.output_dir, 'merge.txt')
            content = read_file_safely(merge_path)
            if content is None:
                logger.error("Failed to read merge.txt")
                return None
            logger.info("Successfully read merge.txt")
            return content
        except Exception as e:
            logger.error(f"Error reading merge file: {e}")
            return None

    def _generate_prompt(self, code_content: str) -> str:
        """AIに送信するプロンプトを生成"""
        return f"""以下のPythonコードに対するリファクタリング提案を行ってください。
以下の観点から分析し、具体的な改善提案を日本語で作成してください：

1. 単一責任原則に基づいた責任の分離
2. 関数の重複
3. 未使用の関数
4. 外部ファイルからの読み込み該当の関数
5. 過度なエラーログの抑制

提案は以下の形式で出力してください：

リファクタリング提案:
以下に各観点に基づいたリファクタリング提案を示します。

### 1. 単一責任原則に基づいた責任の分離
[具体的な提案内容]

### 2. 関数の重複
[具体的な提案内容]

### 3. 未使用の関数
[具体的な提案内容]

### 4. 外部ファイルからの読み込み該当の関数
[具体的な提案内容]

### 5. 過度なエラーログの抑制
[具体的な提案内容]

コード：
{code_content}"""

    def _get_ai_response(self, prompt: str) -> Optional[str]:
        """OpenAI APIを使用してリファクタリング提案を生成"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "あなたは経験豊富なソフトウェアエンジニアです。"
                                 "コードの品質を分析し、具体的で実践的なリファクタリング提案を提供することができます。"
                                 "SOLID原則やクリーンコードの原則に基づいた改善提案を行います。"
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

    def generate_suggestions(self) -> Optional[str]:
        """リファクタリング提案を生成してファイルに保存"""
        try:
            # マージファイルを読み込み
            code_content = self._read_merge_file()
            if not code_content:
                return None

            # プロンプトを生成
            prompt = self._generate_prompt(code_content)
            
            # AI応答を取得
            suggestions = self._get_ai_response(prompt)
            if not suggestions:
                return None

            # リファクタリング提案を保存
            output_path = os.path.join(self.output_dir, 'check_refactoring.txt')
            if write_file_content(output_path, suggestions):
                logger.info(f"Successfully wrote refactoring suggestions to {output_path}")
                return output_path
            return None

        except Exception as e:
            logger.error(f"Error generating refactoring suggestions: {e}")
            return None

    def validate_suggestions(self, suggestions_path: str) -> bool:
        """生成されたリファクタリング提案の妥当性を検証"""
        try:
            content = read_file_safely(suggestions_path)
            if not content:
                logger.error("Generated refactoring suggestions are empty")
                return False

            # 必要なセクションの存在を確認
            required_sections = [
                "リファクタリング提案:",
                "### 1. 単一責任原則に基づいた責任の分離",
                "### 2. 関数の重複",
                "### 3. 未使用の関数",
                "### 4. 外部ファイルからの読み込み該当の関数",
                "### 5. 過度なエラーログの抑制"
            ]

            for section in required_sections:
                if section not in content:
                    logger.error(f"Missing required section: {section}")
                    return False

            logger.info("Refactoring suggestions validation successful")
            return True

        except Exception as e:
            logger.error(f"Error validating refactoring suggestions: {e}")
            return False

def generate_refactoring_suggestions() -> Optional[str]:
    """既存のコードとの互換性のための関数"""
    try:
        checker = RefactoringChecker()
        suggestions_path = checker.generate_suggestions()
        
        if suggestions_path and checker.validate_suggestions(suggestions_path):
            logger.info("Refactoring check completed successfully")
            return suggestions_path
        else:
            logger.error("Refactoring check failed or validation failed")
            return None
            
    except Exception as e:
        logger.error(f"Error in refactoring check: {e}")
        return None

def main():
    return generate_refactoring_suggestions() is not None

if __name__ == "__main__":
    main()