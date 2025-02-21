# src/utils/notifications.py

import logging
import requests
from typing import Optional

from .environment import EnvironmentUtils as env

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url (str): SlackのWebhook URL
        """
        self.webhook_url = webhook_url

    def send_slack_notification(self, message: str, spreadsheet_key: Optional[str] = None) -> bool:
        """
        Slackに通知を送信します。

        Args:
            message (str): 送信するメッセージ
            spreadsheet_key (Optional[str]): スプレッドシートのキー（URLに追加する場合）

        Returns:
            bool: 送信が成功したかどうか
        """
        if spreadsheet_key:
            message += f'\nhttps://docs.google.com/spreadsheets/d/{spreadsheet_key}'

        payload = {
            'text': message,
            'username': '採用確認Bot',
            'link_names': 1,
        }

        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Slack通知を送信しました。")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack通知の送信に失敗しました: {e}")
            return False
