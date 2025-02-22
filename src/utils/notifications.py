# src/utils/notifications.py

import logging
import requests
from typing import Optional, Dict
from datetime import datetime
import json

from .environment import EnvironmentUtils as env
from ..utils.logging_config import get_logger
from ..modules.scheduler import Scheduler

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url (str): SlackのWebhook URL
        """
        self.webhook_url = webhook_url
        self.logger = get_logger(__name__)

    def send_slack_notification(
        self, 
        status: str,
        stats: Optional[Dict] = None,
        error_message: Optional[str] = None,
        spreadsheet_key: Optional[str] = None,
        test_mode: bool = False,
        scheduler: Optional[object] = None
    ) -> bool:
        """
        Slackに通知を送信します。

        Args:
            status (str): 処理のステータス ("success" or "error")
            stats (Optional[Dict]): 処理の統計情報
            error_message (Optional[str]): エラーメッセージ
            spreadsheet_key (Optional[str]): スプレッドシートのキー
            test_mode (bool): テストモードかどうか
            scheduler (Optional[object]): スケジューラーオブジェクト

        Returns:
            bool: 送信が成功したかどうか
        """
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            blocks = []

            # include_pattern_99の設定を取得
            include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)

            # ヘッダー（テストモードの場合のみ表示）
            header_text = "✅ 採用確認自動プログラム" if status == "success" else "❌ エラーが発生しました"
            if test_mode:
                header_text = "[テストモード] " + header_text

            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header_text,
                    "emoji": True
                }
            })

            # 基本情報（2カラムレイアウト）
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"🕒 *処理時刻*\n{now}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"🔄 *実行モード*\n{'テスト' if test_mode else '本番'}"
                    }
                ]
            })

            # 成功時の統計情報
            if status == "success" and stats:
                total_count = stats.get('total', 0)
                filtered_patterns = {k: v for k, v in stats['patterns'].items() if k != '99' or include_pattern_99}
                check_count = sum(v for k, v in filtered_patterns.items() if k != '99')

                blocks.append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"📊 *処理件数*\n{total_count}件"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"✔️ *更新件数*\n{check_count}件"
                        }
                    ]
                })

                # 内訳セクション
                blocks.extend([
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "内訳）チェック更新処理",
                            "emoji": True
                        }
                    }
                ])

                # パターン別の詳細を1つのセクションにまとめる
                pattern_texts = []
                
                # パターン1
                if '1' in filtered_patterns:
                    pattern_texts.append(f"• パターン1: {filtered_patterns['1']}件\n" +
                                      "_保留/不合格/連絡取れず/辞退/欠席_")

                # パターン2-4
                for pattern in ['2', '3', '4']:
                    if pattern in filtered_patterns:
                        description = {
                            '2': "採用：研修日未定・在籍確認未実施",
                            '3': "採用：研修日が実行月以降・在籍確認未実施",
                            '4': "採用：研修日から1ヶ月以上経過・在籍確認済み"
                        }[pattern]
                        pattern_texts.append(f"• パターン{pattern}: {filtered_patterns[pattern]}件\n" +
                                          f"_{description}_")

                # パターン99
                if '99' in filtered_patterns and include_pattern_99:
                    pattern_texts.append(f"• パターン99: {filtered_patterns['99']}件\n" +
                                      "_判定対象外_")

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n\n".join(pattern_texts)
                    }
                })

            # スプレッドシートリンク
            if spreadsheet_key:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📑 *ログシート*\n<https://docs.google.com/spreadsheets/d/{spreadsheet_key}|クリックして開く>"
                    }
                })

            # 区切り線
            blocks.append({
                "type": "divider"
            })

            # フッター（小さく、グレーで表示）
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"_設定情報: ヘッドレス={env.get_config_value('BROWSER', 'headless')} • "
                            f"自動更新={env.get_config_value('BROWSER', 'auto_update')} • "
                            f"0件繰返={env.get_config_value('BROWSER', 'repeat_until_empty')} • "
                            f"P99含={env.get_config_value('LOGGING', 'include_pattern_99')} • "
                            f"提出={self._get_submit_status_text()} • "
                            f"期限={self._get_submit_deadline_text()} • "
                            f"実行時刻={scheduler.get_schedule_text() if scheduler else 'なし'}_"
                        )
                    }
                ]
            })

            payload = {
                "blocks": blocks,
                "username": "採用確認Bot",
                "icon_emoji": ":robot_face:"
            }

            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return True

        except Exception as e:
            self.logger.error(f"Slack通知の送信に失敗: {str(e)}")
            return False

    def _get_submit_status_text(self) -> str:
        """提出ステータスのテキストを取得"""
        status_map = {
            "0": "指定なし",
            "1": "未提出",
            "2": "提出中",
            "3": "提出済"
        }
        status = env.get_config_value('SEARCH', 'submit_status', '')
        return status_map.get(str(status), str(status))

    def _get_submit_deadline_text(self) -> str:
        """提出期限のテキストを取得"""
        deadline_map = {
            "": "なし",
            "1": "今月末",
            "2": "期限超過"
        }
        deadline = env.get_config_value('SEARCH', 'submit_deadline', '')
        return deadline_map.get(str(deadline), str(deadline))

    def _create_pattern_blocks(self, patterns: Dict[str, int]) -> list:
        """パターン別の詳細情報を作成"""
        pattern_blocks = []
        
        # パターン99の制御設定を取得
        include_pattern_99 = env.get_config_value('LOGGING', 'include_pattern_99', False)

        # 要対応（パターン1）
        if '1' in patterns:
            pattern_blocks.extend([
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "要対応",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• パターン1: {patterns['1']}件\n" +
                               "_保留/不合格/連絡取れず/辞退/欠席_"
                    }
                }
            ])

        # 採用確定（パターン2-4）
        adoption_patterns = {k: v for k, v in patterns.items() if k in ['2', '3', '4']}
        if adoption_patterns:
            pattern_blocks.extend([
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "採用確定",
                        "emoji": True
                    }
                }
            ])
            for pattern in ['2', '3', '4']:
                if pattern in adoption_patterns:
                    description = {
                        '2': "採用：研修日未定・在籍確認未実施",
                        '3': "採用：研修日が実行月以降・在籍確認未実施",
                        '4': "採用：研修日から1ヶ月以上経過・在籍確認済み"
                    }[pattern]
                    pattern_blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"• パターン{pattern}: {adoption_patterns[pattern]}件\n" +
                                   f"_{description}_"
                        }
                    })

        # その他（パターン99）
        if '99' in patterns and include_pattern_99:
            pattern_blocks.extend([
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "その他",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• パターン99: {patterns['99']}件\n" +
                               "_判定対象外_"
                    }
                }
            ])

        return pattern_blocks
