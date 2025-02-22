from telnetlib import EC
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from datetime import datetime
from dateutil.relativedelta import relativedelta

class Adoption:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def get_applicants_data(self):
        """応募者情報の取得"""
        applicants = {}
        try:
            # 応募者一覧テーブルの取得
            table = self.driver.find_elements(By.CLASS_NAME, "w_900")[1]
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            current_applicant_id = None
            row_count = 0
            
            for row in rows:
                # ヘッダー行をスキップ
                if len(row.find_elements(By.TAG_NAME, "th")) != 0:
                    continue
                
                row_count += 1
                
                if row_count == 1:
                    # 1行目: 基本情報
                    current_applicant_id = row.find_element(By.CLASS_NAME, "no").text.strip()
                    status = Select(row.find_element(By.CLASS_NAME, "job_adoptions__adoption_status_id")).first_selected_option.text
                    first_work = row.find_element(By.CLASS_NAME, "job_adoptions__training_first_on").get_attribute("value")
                    
                    applicants[current_applicant_id] = {
                        "status": status,
                        "first_work": first_work,
                        "enrollment": "",
                        "recruit_celebration": "",
                        "admin_memo": "",
                        "check_element": None
                    }
                    
                elif row_count == 2:
                    # 2行目: 在籍確認
                    enrollment = ""
                    enrollment_elements = row.find_elements(By.CLASS_NAME, "job_adoptions__belong_1month_enum")
                    if enrollment_elements:
                        enrollment = Select(enrollment_elements[0]).first_selected_option.text
                    applicants[current_applicant_id]["enrollment"] = enrollment
                    
                elif row_count == 3:
                    # 3行目: お祝い、メモ、チェック要素
                    applicants[current_applicant_id].update({
                        "recruit_celebration": row.find_element(By.TAG_NAME, "td").text,
                        "admin_memo": row.find_element(By.CLASS_NAME, "job_adoptions__remark_dummy").get_attribute("value"),
                        "check_element": row.find_element(By.CLASS_NAME, "job_adoptions__admin_check_flag")
                    })
                    row_count = 0
                    current_applicant_id = None
            
            return applicants
            
        except Exception as e:
            print(f"応募者情報の取得でエラー: {str(e)}")
            return {}

    def should_check_applicant(self, applicant_data, processed_ids):
        """応募者のチェック要否を判定"""
        if applicant_data["id"] in processed_ids:
            return False
            
        current_date = datetime.now()
        try:
            check_date = datetime.strptime(applicant_data["first_work"], "%Y/%m/%d")
        except:
            check_date = applicant_data["first_work"]

        # 採用かつ祝い・メモが空の場合
        if applicant_data["status"] == "採用" and not applicant_data["recruit_celebration"] and not applicant_data["admin_memo"]:
            # 研修日未定かつ在籍確認なし
            if applicant_data["first_work"] and not applicant_data["enrollment"] and check_date == "未定":
                return True
                
            # 当月以降の研修日かつ在籍確認なし
            if applicant_data["first_work"] and (check_date.year > current_date.year or 
                (check_date.year == current_date.year and check_date.month >= current_date.month)) and not applicant_data["enrollment"]:
                return True
                
            # 研修から1ヶ月経過かつ在籍確認済
            if applicant_data["first_work"] and (current_date - relativedelta(months=1) >= check_date) and applicant_data["enrollment"] == "◯":
                return True

        # 不採用系ステータスかつ祝い・メモが空の場合
        elif applicant_data["status"] in ["保留", "不合格", "連絡取れず", "辞退", "欠席"] and not applicant_data["recruit_celebration"] and not applicant_data["admin_memo"]:
            return True

        return False

    def apply_checks(self, applicants_data, processed_ids):
        """チェック処理の実行"""
        checked_applicants = []
        check_performed = False
        
        for applicant_id, data in applicants_data.items():
            if self.should_check_applicant(data, processed_ids):
                data["check_element"].click()
                checked_applicants.append({
                    "id": applicant_id,
                    "status": data["status"]
                })
                check_performed = True
                
        if check_performed:
            # 変更ボタンクリック
            self.driver.find_elements(By.CSS_SELECTOR, ".box-button.large")[1].find_element(By.TAG_NAME, "input").click()
            self.wait.until(EC.presence_of_all_elements_located)
            time.sleep(1)
            
            # 実行ボタンクリック
            self.driver.find_elements(By.CSS_SELECTOR, ".box-button.large")[0].find_element(By.TAG_NAME, "input").click()
            self.wait.until(EC.presence_of_all_elements_located)
            time.sleep(2.5)
            
        return checked_applicants 