```mermaid
graph TD
    subgraph "外部システム"
        GS[Google Spreadsheet<br/>シート1]
        Slack[Slack]
        JOB[求人サービス]
    end

    subgraph "設定ファイル"
        SET[setting.txt]
        JSON[data.json]
        LOG[log.txt<br/>処理済ID]
    end

    subgraph "現在のプロセス"
        MAIN[main.py]
        AUTO[new_auto_saiyo_check.py]
    end

    %% 現在のデータの流れ
    SET -->|全設定情報| MAIN
    JSON -->|API認証| MAIN
    LOG -->|処理済ID読込| MAIN
    MAIN -->|処理済ID追記| LOG

    MAIN -->|認証・操作（selenium）| JOB
    MAIN -->|結果保存| GS
    GS -->|最終行取得| MAIN
    MAIN -->|完了通知| Slack
    JOB -->|応募者データ| MAIN