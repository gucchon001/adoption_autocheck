```mermaid
graph TD
    %% 外部システム
    subgraph "外部システム"
        GS[Google Spreadsheet<br>(ログシート)]
        Slack[Slack]
        JOB[求人サービス]
    end

    %% 設定ファイル
    subgraph "設定ファイル"
        SET[settings.ini]
        JSON[data.json]
        LOG[log.txt<br>(処理済ID)]
    end

    %% 内部プロセス
    subgraph "内部プロセス"
        MAIN[main.py]
        SCHED[Scheduler]
        BROW[Browser<br>(ChromeDriver &amp; Selenium)]
        CHK[ApplicantChecker]
        LOGGER[Logger]
        NOTIF[Notifier]
    end

    %% 設定ファイルからの入力
    SET -->|全設定情報| MAIN
    JSON -->|API認証情報| MAIN
    LOG -->|処理済ID読み込み| MAIN

    %% スケジューリング処理
    MAIN -->|スケジュール確認要求| SCHED
    SCHED -->|実行時刻到達通知| MAIN

    %% ブラウザ起動と求人サービス連携
    MAIN -->|ChromeDriver起動| BROW
    MAIN -->|基本認証・ログイン指示| JOB
    JOB -->|応募者データ提供| MAIN

    %% 採用確認処理
    MAIN -->|応募者検索・処理実行| BROW
    BROW -->|抽出応募者データ| MAIN

    %% 応募者チェック
    MAIN -->|応募者情報評価| CHK
    CHK --|合致データ返却| MAIN

    %% ログ記録処理
    MAIN -->|ログ記録依頼| LOGGER
    LOGGER -->|応募者データ記録| GS
    LOGGER -->|処理済ID追記| LOG

    %% 通知処理
    MAIN -->|通知依頼| NOTIF
    NOTIF -->|Slack通知送信| Slack
```