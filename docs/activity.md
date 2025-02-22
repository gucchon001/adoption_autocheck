```mermaid
graph TD
    Start([開始]) --> ReadConfig[設定ファイル読み込み<br>settings.ini]
    ReadConfig --> ReadLog[処理済IDログ読み込み<br>log.txt]
    ReadLog --> Auth[Basic認証]
    Auth --> Login[サービスログイン]
    
    Login --> WaitTime{実行時刻か?<br>exec_time1/2}
    WaitTime -- No --> WaitTime
    WaitTime -- Yes --> GetSheet[スプレッドシート<br>最終行取得]
    
    GetSheet --> SearchApplicants[応募者情報検索]
    
    SearchApplicants --> CheckLoop{チェック対象あり?}
    CheckLoop -- Yes --> CheckStatus[応募者ステータス確認]
    CheckStatus --> UpdateSheet[スプレッドシート更新]
    UpdateSheet --> LogUpdate[ログファイル更新]
    LogUpdate --> CheckLoop
    
    CheckLoop -- No --> NotifySlack[Slack通知]
    NotifySlack --> WaitTime
    
    subgraph "ステータス確認条件"
        CheckStatus --> IsAdopted{採用?}
        IsAdopted -- Yes --> CheckAdoptCond[採用条件確認<br>- 研修初日<br>- 在籍確認<br>- 採用お祝い]
        IsAdopted -- No --> CheckOtherStatus[他ステータス確認<br>保留/不合格/連絡取れず<br>辞退/欠席]
        
        CheckAdoptCond -- 条件合致 --> NeedCheck[要チェック]
        CheckOtherStatus -- 条件合致 --> NeedCheck
        CheckAdoptCond -- 条件不一致 --> NoCheck[チェック不要]
        CheckOtherStatus -- 条件不一致 --> NoCheck
    end 