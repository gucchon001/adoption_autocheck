```mermaid
graph TD
    %% 外部システム
    subgraph "外部システム"
        GS[Google Spreadsheet<br/>ログシート]
        Slack[Slack]
        JOB[求人サービス]
    end

    %% 設定ファイル
    subgraph "設定ファイル"
        SET[settings.ini]
        JSON[data.json<br/>Google API認証]
        SEL[selectors.csv<br/>要素セレクタ]
        JUD[judge_list.csv<br/>判定条件]
        LOG[log.txt<br/>処理済ID]
    end

    %% 内部プロセス
    subgraph "内部プロセス"
        MAIN[main.py]
        ENV[EnvironmentUtils]
        SCHED[Scheduler<br/>実行時刻制御]
        BROW[Browser<br/>ChromeDriver & Selenium]
        LOGIN[Login<br/>認証処理]
        SEARCH[Search<br/>応募者検索]
        CHK[ApplicantChecker<br/>パターン判定]
        LOGGER[Logger<br/>ログ記録]
        NOTIF[Notifier<br/>Slack通知]
    end

    %% 設定読み込み
    SET -->|設定情報| ENV
    ENV -->|環境設定| MAIN
    JSON -->|API認証| ENV
    SEL -->|セレクタ定義| CHK
    JUD -->|判定条件| CHK

    %% メインフロー制御
    MAIN -->|スケジュール確認| SCHED
    SCHED -->|実行時刻通知| MAIN

    %% ブラウザ操作
    MAIN -->|ブラウザ起動| BROW
    MAIN -->|ログイン指示| LOGIN
    LOGIN -->|認証実行| JOB
    MAIN -->|検索実行| SEARCH
    SEARCH -->|検索実行| JOB
    JOB -->|応募者データ| MAIN

    %% データ処理
    MAIN -->|応募者情報評価| CHK
    CHK -->|判定結果| MAIN
    LOG -->|処理済ID| MAIN

    %% 結果記録・通知
    MAIN -->|ログ記録| LOGGER
    LOGGER -->|データ記録| GS
    LOGGER -->|処理ID記録| LOG
    MAIN -->|結果通知| NOTIF
    NOTIF -->|通知送信| Slack