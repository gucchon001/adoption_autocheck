from datetime import datetime
import time
from ..utils.environment import EnvironmentUtils as env

class Scheduler:
    def __init__(self, time1, time2):
        """
        Args:
            time1 (list): 1回目の実行時間 [時, 分]
            time2 (list): 2回目の実行時間 [時, 分]
        """
        self.time1 = time1
        self.time2 = time2
        self.enabled = env.get_config_value('SCHEDULE', 'enabled', True)

    def wait_for_execution_time(self):
        """実行時間まで待機"""
        if not self.enabled:
            print("スケジューラーは無効化されています")
            return

        print("待機中")
        while not self._check_execution_time():
            time.sleep(1)
        print("実行スタート")

    def _check_execution_time(self):
        """実行時間のチェック"""
        if not self.enabled:
            return True
            
        current = datetime.now()
        return (str(current.hour) == str(self.time1[0]) and str(current.minute) == str(self.time1[1])) or \
               (str(current.hour) == str(self.time2[0]) and str(current.minute) == str(self.time2[1]))

    def get_schedule_text(self) -> str:
        """スケジュール設定の文字列を取得"""
        if not self.enabled:
            return "無効"
        return f"{self.time1[0]:02d}:{self.time1[1]:02d}, {self.time2[0]:02d}:{self.time2[1]:02d}" 