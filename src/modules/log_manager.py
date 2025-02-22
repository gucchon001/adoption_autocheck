from pathlib import Path

class LogManager:
    def __init__(self, log_path: Path):
        """
        Args:
            log_path (Path): ログファイルのパス
        """
        self.log_path = log_path
        self.processed_ids = []
        
        # ログファイルのディレクトリが存在しない場合は作成
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ログファイルが存在しない場合は空のファイルを作成
        if not self.log_path.exists():
            self.log_path.touch()
        else:
            self._load_processed_ids()

    def _load_processed_ids(self):
        """処理済みIDの読み込み"""
        with open(self.log_path, encoding='utf-8', errors='ignore') as f:
            self.processed_ids = [line.strip() for line in f if line.strip()]

    def save_processed_ids(self, new_ids):
        """処理済みIDの保存"""
        self.processed_ids.extend(new_ids)
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.processed_ids))

    def get_processed_ids(self):
        """処理済みIDのリストを取得"""
        return self.processed_ids 