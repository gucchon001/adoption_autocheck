# 求人応募者ステータス確認自動化システム

## 概要
求人サービスの応募者ステータスを定期的にチェックし、結果をGoogle Spreadsheetへ出力およびSlackへ通知する自動化システムです。

## 主な機能
- 指定時刻での自動実行（スケジューラー機能）
- ヘッドレスブラウザによる自動チェック
- 応募者情報の自動判定
- Google Spreadsheetへの結果記録
- Slack通知による結果報告

## システム要件
- Python 3.8以上
- Google Spreadsheet API認証情報
- Slack Webhook URL
- Chrome/Chromium ブラウザ

## セットアップと実行方法

### 1. 設定ファイルの準備

#### 基本設定 (config/settings.ini)
```ini
[SERVICE]
domain = サービスドメイン
service_account_file = config/data.json

[SCHEDULE]
enabled = true  # スケジューラーの有効/無効
exec_time1 = 12:00  # 1回目の実行時刻
exec_time2 = 18:00  # 2回目の実行時刻

[BROWSER]
headless = true  # ブラウザ非表示モード（本番環境ではtrue推奨）
auto_update = true  # 更新ボタンの自動クリック
repeat_until_empty = true  # 検索結果0件まで繰り返し実行

[SEARCH]
submit_status = 2  # 提出ステータス（0:指定なし、1:未提出、2:提出中、3:提出済）
submit_deadline = 1  # 提出期限（"":指定なし、1:今月末、2:期限超過）
```

#### 環境設定ファイル
- **開発環境用**: `config/secrets_test.env`
  - テスト環境用の認証情報
  - テスト用APIキー
  - ステージング環境のURL設定

- **本番環境用**: `config/secrets.env`
  - 本番環境の認証情報
  - 本番用APIキー
  - 本番環境のURL設定

#### 判定条件設定 (config/judge_list.csv)
応募者の状態に応じた判定パターンを定義：
- パターン2-4: 採用確定者の研修日・在籍状況による判定
- パターン1: 保留/不合格/連絡取れず/辞退/欠席の判定
- 各パターンごとの確認項目（研修初日、在籍確認、採用お祝い）

#### 要素セレクタ設定 (config/selectors.csv)
Webページの要素を特定するためのセレクタ定義：
- ログイン関連の入力項目
- 応募者情報の各項目（ID、教室名、氏名など）
- ステータス選択や更新ボタンなど
- 検索条件の入力項目

### 2. 詳細仕様書
システムの詳細な仕様については、`docs/`ディレクトリ内の以下のドキュメントを参照してください：

#### 機能仕様
- `spec.md`: システム仕様書（詳細な機能仕様）

#### システム設計図
- `system.md`: システム構成図
- `data_flow.md`: データフロー図
- `class_diagram.md`: クラス構成図
- `sequence.md`: シーケンス図
- `state.md`: 状態遷移図
- `activity.md`: アクティビティ図（処理フロー）

これらの設計図はMermaid記法で記述されており、GitHubやVSCodeで直接プレビューできます。

### 2. 実行方法

#### 開発時の実行
```bash
run_dev.bat
```
- 実行環境を選択できます（development/production）
- developmentモード：テストモードで実行、詳細ログ出力
- productionモード：本番環境用の設定で実行

#### 本番環境での実行
```bash
run.bat
```
- 本番環境用の設定で直接実行
- Windowsタスクスケジューラーでの定期実行に使用

### 3. 設定項目の説明

#### 基本設定 (settings.ini)
- `[SERVICE]`: サービス接続設定
- `[SCHEDULE]`: 実行スケジュール設定
- `[BROWSER]`: ブラウザ動作設定
- `[LOGGING]`: ログ出力設定
- `[SEARCH]`: 検索条件設定

#### 環境別設定
- 開発環境（development）
  - デバッグログ有効
  - テストモード使用可能
- 本番環境（production）
  - 最小限のログ出力
  - ヘッドレスモード推奨

## 注意事項
- システム実行中はブラウザを操作しないでください
- 設定ファイルの形式を維持してください
- ネットワーク接続が安定している環境で実行してください
- PCのスリープ設定を無効にすることを推奨します

## トラブルシューティング
- ログファイルは `logs/` ディレクトリに保存されます
- エラー発生時はSlackに通知されます
- 実行時のエラーはコンソールに表示されます