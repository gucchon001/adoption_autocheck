from datetime import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')

class PathGenerator:
    def __init__(self, service_name: str, environment: str):
        self.service_name = service_name
        self.environment = environment
        
    def generate_gcs_path(self, table_name: str, chunk_num: int, load_type: str = "full_load") -> str:
        """
        GCSのファイルパスを生成
        
        Args:
            table_name: テーブル名
            chunk_num: チャンク番号
            load_type: ロードタイプ（"full_load" or "incremental"）
            
        Returns:
            str: GCS上のファイルパス
        """
        current_date = datetime.now(JST).strftime('%Y%m%d')
        timestamp = datetime.now(JST).strftime('%H%M%S')
        
        # パス構成
        path_components = {
            'root': 'mysql_exports',
            'service': self.service_name,
            'env': self.environment,
            'load_type': load_type,
            'table': table_name,
            'date': current_date,
            'filename': f"{table_name}_part_{chunk_num:03d}_{timestamp}.parquet"
        }
        
        return (
            f"{path_components['root']}/"
            f"{path_components['service']}/"
            f"{path_components['env']}/"
            f"{path_components['load_type']}/"
            f"{path_components['table']}/"
            f"{path_components['date']}/"
            f"{path_components['filename']}"
        ) 