from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional
from pathlib import Path
import csv
import logging

class ApplicantChecker:
    def __init__(self, selectors_file: Path, judge_list_file: Path):
        """
        Args:
            selectors_file (Path): セレクターファイルのパス
            judge_list_file (Path): 判定パターンファイルのパス
        """
        self.selectors = self._load_selectors(selectors_file)
        self.patterns = self._load_judge_patterns(judge_list_file)
        self.logger = logging.getLogger(__name__)

    def _load_selectors(self, file_path: Path) -> Dict[str, str]:
        """
        セレクターファイルを読み込む
        
        Args:
            file_path (Path): セレクターファイルのパス
            
        Returns:
            Dict[str, str]: セレクター情報
        """
        selectors = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['page'] == 'adoption':
                    selectors[row['element']] = {
                        'description': row['description'],
                        'action_type': row['action_type'],
                        'selector_type': row['selector_type'],
                        'selector_value': row['selector_value']
                    }
        return selectors

    def _load_judge_patterns(self, file_path: Path) -> List[Dict]:
        """
        判定パターンファイルを読み込む
        
        Args:
            file_path (Path): 判定パターンファイルのパス
            
        Returns:
            List[Dict]: 判定パターンのリスト
        """
        # 注: 判定パターンファイルのカラム名と内部変数名の対応
        # 'remark'(CSV) -> 'admin_memo'(コード内変数)
        # この変換により、コード内で管理者メモは一貫して'admin_memo'として扱う
        patterns = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                patterns.append({
                    'pattern': int(row['pattern']),
                    'oiwai': row['oiwai'],
                    'admin_memo': row['remark'],  # CSVファイルのカラム名は'remark'だが、内部的には'admin_memo'として扱う
                    'status': row['status'],
                    'training_start_date': row['training_start_date'],
                    'zaiseki': row['zaiseki']
                })
        return patterns

    def get_selectors(self) -> Dict[str, Dict[str, str]]:
        """
        セレクター情報を取得
        
        Returns:
            Dict[str, Dict[str, str]]: セレクター情報の辞書
        """
        return self.selectors

    def _check_training_date_condition(self, condition: str, actual_date: str) -> bool:
        """
        研修日の条件チェック
        
        Args:
            condition (str): 判定条件 (例: {実行月以降}, {1ヶ月以上経過})
            actual_date (str): 実際の日付 (例: 2024/04/01)
            
        Returns:
            bool: 条件を満たすかどうか
        """
        if actual_date == "未定":
            return False
        
        try:
            # 日付文字列をdatetimeオブジェクトに変換
            training_date = datetime.strptime(actual_date, "%Y/%m/%d")
            current_date = datetime.now()
            
            if condition == "{実行月以降}":
                # 実行月以降の判定
                return (training_date.year > current_date.year) or (
                    training_date.year == current_date.year and 
                    training_date.month >= current_date.month
                )
                
            elif condition == "{1ヶ月以上経過}":
                # 1ヶ月以上経過の判定
                one_month_ago = current_date - relativedelta(months=1)
                return one_month_ago >= training_date
                
        except ValueError:
            return False
        
        return False

    def should_check_applicant(self, applicant: Dict) -> Optional[str]:
        """
        応募者が確認対象かどうかを判定します。

        Args:
            applicant (Dict): 応募者情報
                {
                    'status': str,          # ステータス
                    'celebration_sent': str, # 採用お祝い送信状況
                    'admin_memo': str,      # 管理者メモ
                    'training_date': str,   # 研修初日
                    'attendance_check': str  # 在籍確認状況
                }

        Returns:
            Optional[str]: チェック結果の理由。対象外の場合はNone
        """
        # 共通条件チェック
        if applicant['celebration_sent'] or applicant['admin_memo']:
            return None

        # 各パターンのチェック
        values = {
            'oiwai': applicant['celebration_sent'],
            'admin_memo': applicant['admin_memo'],
            'status': applicant['status'],
            'training_start_date': applicant['training_date'],
            'zaiseki': applicant['attendance_check']
        }

        # パターン2: 採用_未定
        if self._matches_pattern("2", values):
            return "研修日未定・在籍確認未実施"

        # パターン3: 採用_実行月以降
        if self._matches_pattern("3", values):
            return "研修日当月以降・在籍確認未実施"

        # パターン4: 採用_1ヶ月以上経過_◯
        if self._matches_pattern("4", values):
            return "研修日1ヶ月経過・在籍確認済み"

        # パターン1: 不採用等確定
        if self._matches_pattern("1", values):
            return "不採用等確定"

        return None

    def _matches_pattern(self, pattern_id: str, values: Dict[str, str]) -> bool:
        """
        与えられた値が指定されたパターンに一致するか確認

        Args:
            pattern_id (str): パターンID
            values (Dict[str, str]): チェックする値

        Returns:
            bool: パターンに一致するかどうか
        """
        patterns = self.patterns.get(pattern_id, [])
        for pattern in patterns:
            matches = True
            for key, expected in pattern.items():
                if not expected:  # 空の条件はスキップ
                    continue

                actual = values.get(key, '')
                
                # 研修日の特殊条件チェック
                if key == 'training_start_date' and expected.startswith('{'):
                    if not self._check_training_date_condition(expected, actual):
                        matches = False
                        break
                # 通常の値チェック
                elif actual != expected:
                    matches = False
                    break

            if matches:
                return True
        return False

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """日付文字列をdatetimeオブジェクトに変換"""
        if date_str == "未定":
            return None
        
        formats = ['%Y/%m/%d', '%Y-%m-%d']  # 対応する日付フォーマット
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def check_pattern(self, applicant_data: Dict) -> tuple[int, str]:
        """応募者データのパターンを判定する"""
        now = datetime.now()
        self.logger.info(f"パターン判定開始: {applicant_data}")
        
        # パターン1の判定（保留/不合格/連絡取れず/辞退/欠席）
        if applicant_data['status'] in ['保留', '不合格', '連絡取れず', '辞退', '欠席']:
            reason = f"ステータス: {applicant_data['status']}"
            self.logger.info(f"パターン1と判定: {reason}")
            self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {1}, 理由: {reason}")
            return 1, reason
            
        # 採用の場合のパターン判定
        if applicant_data['status'] == '採用':
            # パターン2: 研修日未定
            if applicant_data['training_start_date'] == '未定':
                self.logger.info("パターン2と判定: 研修日未定")
                reason = "研修日未定・在籍確認未実施"
                self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {2}, 理由: {reason}")
                return 2, reason
                
            training_date = self._parse_date(applicant_data['training_start_date'])
            if not training_date:
                self.logger.info("パターン99と判定: 研修日のパース失敗")
                reason = "研修日の形式が不正"
                self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {99}, 理由: {reason}")
                return 99, reason
                
            # パターン3: 実行月以降
            if training_date >= now:
                self.logger.info("パターン3と判定: 研修日が実行月以降")
                reason = "研修日が実行月以降・在籍確認未実施"
                self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {3}, 理由: {reason}")
                return 3, reason
                
            # パターン4: 1ヶ月以上経過
            one_month_ago = now - relativedelta(months=1)
            if training_date <= one_month_ago and applicant_data['zaiseki'] == '〇':
                self.logger.info("パターン4と判定: 1ヶ月以上経過・在籍確認済み")
                reason = "研修日から1ヶ月以上経過・在籍確認済み"
                self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {4}, 理由: {reason}")
                return 4, reason
        
        self.logger.info("パターン99と判定: 該当するパターンなし")
        self.logger.info(f"DEBUG: checker.py - パターン判定結果 -> パターン: {99}, 理由: {'該当するパターンなし'}")
        return 99, "該当するパターンなし"

    @staticmethod
    def format_check_result(reason: str) -> str:
        """
        チェック結果を整形します。

        Args:
            reason (str): チェックの理由

        Returns:
            str: 整形されたチェック結果
        """
        return f"要確認（{reason}）"

    def _build_pattern_reason(self, pattern_id: int, applicant_data: Dict) -> str:
        """
        パターンに応じた判定理由を構築します。

        Args:
            pattern_id (int): パターンID
            applicant_data (Dict): 応募者データ

        Returns:
            str: 判定理由
        """
        pattern_reasons = {
            1: "不採用等確定",
            2: "研修日未定・在籍確認未実施",
            3: "研修日当月以降・在籍確認未実施",
            4: "研修日1ヶ月経過・在籍確認済み",
            99: "該当するパターンなし"
        }

        # パターンに応じた基本の理由を取得
        reason = pattern_reasons.get(pattern_id, "不明なパターン")

        # 研修日情報を追加（必要な場合）
        if pattern_id in [2, 3, 4]:
            training_date = applicant_data.get('training_start_date', '未定')
            reason = f"{reason}（研修日: {training_date}）"

        return reason 