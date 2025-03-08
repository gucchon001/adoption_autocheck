```mermaid
graph TD
    Start([開始]) --> ReadConfig[設定ファイル読み込み<br>settings.ini]
    ReadConfig --> Auth[Basic認証]
    Auth --> Login[サービスログイン]
    
    Login --> WaitTime{実行時刻か?<br>exec_time1/2}
    WaitTime -- No --> WaitTime
    WaitTime -- Yes --> GetSheet[スプレッドシート<br>最終行取得]
    
    GetSheet --> SearchApplicants[応募者情報検索]
    
    SearchApplicants --> ProcessPage[現在ページの処理]
    
    ProcessPage --> CheckLoop{チェック対象あり?}
    CheckLoop -- Yes --> CheckStatus[応募者ステータス確認]
    CheckStatus --> ClickCheckbox[チェックボックスクリック]
    ClickCheckbox --> CheckLoop
    
    CheckLoop -- No --> UpdateButton[更新ボタンクリック]
    UpdateButton --> HasChanges{変更あり?}
    HasChanges -- Yes --> ConfirmUpdate[更新確定]
    ConfirmUpdate --> CloseModal[閉じるボタンクリック]
    HasChanges -- No --> NextPage
    CloseModal --> NextPage{次ページあり?}
    
    NextPage -- Yes --> ClickNextPage[次ページボタンクリック]
    ClickNextPage --> ProcessPage
    
    NextPage -- No --> UpdateSheet[スプレッドシート更新]
    UpdateSheet --> NotifySlack[Slack通知]
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