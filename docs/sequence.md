```mermaid
sequenceDiagram
    participant User
    participant Main as メインプロセス
    participant Config as 設定ファイル
    participant Log as ログファイル
    participant Browser as ブラウザ
    participant Job as 求人サービス
    participant Sheet as スプレッドシート
    participant Slack as Slack

    User->>Main: システム起動
    Main->>Config: 設定読み込み
    Main->>Log: 処理済ID読み込み
    
    loop 実行時刻待機
        Main->>Main: 現在時刻チェック
    end

    Main->>Browser: ChromeDriver起動
    Main->>Job: Basic認証
    Main->>Job: サービスログイン
    
    loop 応募者チェック
        Main->>Job: 応募者情報取得
        Job-->>Main: 応募者データ
        Main->>Sheet: 最終行取得
        Sheet-->>Main: 行数
        
        alt ステータス条件合致
            Main->>Sheet: 結果記録
            Main->>Log: 処理済ID追記
        end
    end
    
    Main->>Slack: 完了通知
    Slack-->>Main: 通知完了
    
    alt エラー発生
        Main->>Main: リトライ処理
    end 