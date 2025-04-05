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
        LOG[log.txt<br/>処理ログファイル]
    end

    %% 内部プロセス
    subgraph "内部プロセス"
        MAIN[main.py]
        ENV[EnvironmentUtils]
        SCHED[Scheduler<br/>実行時刻制御]
        BROW[Browser<br/>ChromeDriver & Selenium]
        ADOPT[Adoption<br/>応募者処理]
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
    BROW -->|ログイン指示| LOGIN
    LOGIN -->|認証実行| JOB
    JOB -->|ログイン結果| LOGIN
    LOGIN -->|ログイン結果| BROW
    BROW -->|検索指示| SEARCH
    SEARCH -->|検索実行| JOB
    JOB -->|検索結果| SEARCH
    SEARCH -->|検索結果| BROW

    %% データ処理
    BROW -->|応募者処理開始| ADOPT
    ADOPT -->|応募者データ取得| JOB
    JOB -->|応募者データ| ADOPT
    ADOPT -->|パターン判定| CHK
    CHK -->|判定結果| ADOPT
    ADOPT -->|結果とデータ| BROW
    BROW -->|処理結果リスト| MAIN

    %% 結果記録・通知
    BROW -->|ログ記録指示| LOGGER
    LOGGER -->|データ記録| GS
    MAIN -->|Slack通知指示| NOTIF
    NOTIF -->|通知送信| Slack