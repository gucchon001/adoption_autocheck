# src/utils/notifications.py

import logging
import requests
from typing import Optional, Dict
from datetime import datetime
import json

from .environment import EnvironmentUtils as env

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url (str): SlackのWebhook URL
        """
        self.webhook_url = webhook_url

    def send_slack_notification(
        self, 
        status: str,
        stats: Optional[Dict] = None,
        error_message: Optional[str] = None,
        spreadsheet_key: Optional[str] = None,
        test_mode: bool = False
    ) -> bool:
        """
        Slackに通知を送信します。

        Args:
            status (str): 処理のステータス ("success" or "error")
            stats (Optional[Dict]): 処理の統計情報
            error_message (Optional[str]): エラーメッセージ
            spreadsheet_key (Optional[str]): スプレッドシートのキー
            test_mode (bool): テストモードかどうか

        Returns:
            bool: 送信が成功したかどうか
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_text = "[テストモード]" if test_mode else "[本番モード]"
        
        if status == "success":
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{mode_text} ✅ 処理が完了しました",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*処理時刻:*\n{now}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*実行モード:*\n{'テスト' if test_mode else '本番'}"
                        }
                    ]
                }
            ]

            if stats:
                # 全体の処理件数
                total_block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*処理件数:* {stats.get('total', 0)}件"
                    }
                }
                blocks.append(total_block)

                # パターンごとの件数
                if 'patterns' in stats:
                    pattern_descriptions = {
                        1: {
                            "保留": "選考結果が保留中",
                            "不合格": "不合格が確定",
                            "連絡取れず": "連絡が取れない状態",
                            "辞退": "応募者から辞退の連絡",
                            "欠席": "面接・説明会に欠席"
                        },
                        2: "採用：研修日未定・在籍確認未実施",
                        3: "採用：研修日が実行月以降・在籍確認未実施",
                        4: "採用：研修日から1ヶ月以上経過・在籍確認済み"
                    }
                    
                    pattern_text = "*パターン別件数:*\n"
                    for pattern, count in stats['patterns'].items():
                        if pattern == 1:
                            # パターン1は複数の状態があるため、合計を表示
                            pattern_text += f"• パターン1（要対応）: {count}件\n"
                            pattern_text += "  - 保留/不合格/連絡取れず/辞退/欠席のいずれか\n"
                        else:
                            description = pattern_descriptions.get(pattern, "不明なパターン")
                            pattern_text += f"• パターン{pattern}: {count}件\n"
                            pattern_text += f"  - {description}\n"
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": pattern_text
                        }
                    })

        else:  # エラーの場合
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{mode_text} ❌ エラーが発生しました",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*発生時刻:*\n{now}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*実行モード:*\n{'テスト' if test_mode else '本番'}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*エラー内容:*\n```{error_message}```"
                    }
                }
            ]

        # スプレッドシートのリンクを追加
        if spreadsheet_key:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*スプレッドシート:*\nhttps://docs.google.com/spreadsheets/d/{spreadsheet_key}"
                }
            })

        payload = {
            "blocks": blocks,
            "username": "採用確認Bot",
            "icon_emoji": ":robot_face:"
        }

        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Slack通知を送信しました。")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack通知の送信に失敗しました: {e}")
            return False
