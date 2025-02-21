from datetime import datetime
import time

class Scheduler:
    def __init__(self, time1, time2):
        """
        Args:
            time1 (list): 1回目の実行時間 [時, 分]
            time2 (list): 2回目の実行時間 [時, 分]
        """
        self.time1 = time1
        self.time2 = time2

    def wait_for_execution_time(self):
        """実行時間まで待機"""
        print("待機中")
        while not self._check_execution_time():
            time.sleep(1)
        print("実行スタート")

    def _check_execution_time(self):
        """実行時間のチェック"""
        current = datetime.now()
        return (str(current.hour) == str(self.time1[0]) and str(current.minute) == str(self.time1[1])) or \
               (str(current.hour) == str(self.time2[0]) and str(current.minute) == str(self.time2[1])) 