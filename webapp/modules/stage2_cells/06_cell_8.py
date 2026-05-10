# [ Cell 8 ] (Final_PDF_Exclude) 서플라이허브 다운로드 (PDF 제외 + ZIP 삭제 기능 추가)
import subprocess
import os
import time
import shutil
import zipfile
import glob
import pandas as pd
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

print("▶️ [ Cell 8 ] 통합 다운로드 로봇 (PDF 제외 모드) 가동!...")

# ==========================================
# ⚙️ [설정]
# ==========================================
target_sheet_name = globals().get('TARGET_SHEET_NAME', "상품등록목록")
supply_id = globals().get('SUPPLY_ID', "")
supply_pw = globals().get('SUPPLY_PW', "")

user_home = os.path.expanduser("~")
my_dl_dir = globals().get('MY_DOWNLOAD_DIR', os.path.join(user_home, "Downloads"))
path_prof = globals().get('PATH_PROFILE', r"C:\rocket-bot\chrome_profile")

my_dl_dir = os.path.normpath(my_dl_dir)
if not os.path.exists(path_prof): os.makedirs(path_prof)

# -----------------------------------------------------------
# 🛠️ [헬퍼 함수] Oops 에러 및 흰 화면 감지
# -----------------------------------------------------------
def check_browser_error(driver):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "Oops" in body_text or len(body_text) < 50:
            print("\n" + "="*60)
            print("🚨 [경고] 서플라이허브 화면 오류(Oops 또는 흰 화면)가 감지되었습니다!")
            print("👉 브라우저를 확인해서 '새로고침' 하거나 정상 화면으로 돌려주세요.")
            input("✅ 해결하셨다면 [Enter] 키를 눌러서 계속 진행하세요...")
            print("="*60 + "\n")
            return True
    except: pass
    return False

# ==========================================
# 🚀 [1단계] 기존 로봇 크롬 정리 및 실행
# ==========================================
def kill_existing_debug_chrome():
    print("    🧹 기존 로봇 크롬 정리 중...")
    try:
        cmd = 'wmic process where "name=\'chrome.exe\' and commandline like \'%remote-debugging-port=9222%\'" get processid'
        output = subprocess.check_output(
            cmd, shell=True, encoding='utf-8', errors='replace',
        )
        pids = [int(p) for p in output.split() if p.isdigit()]
        if pids:
            for pid in pids: os.system(f'taskkill /F /PID {pid} > nul 2>&1')
            time.sleep(2)
    except:
        os.system('taskkill /f /im chrome.exe /fi "remote-debugging-port=9222" > nul 2>&1')

def launch_robot_chrome():
    kill_existing_debug_chrome()
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.getenv('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe')
    ]
    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
    if not chrome_exe: print("    ❌ 크롬 없음"); return

    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={path_prof}",
        "--lang=ko", 
        "--disable-features=Translate",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized", 
        "--window-position=0,0",
        "https://supplier.coupang.com/login"
    ]
    subprocess.Popen(cmd)
    print("    🚀 크롬 실행 완료. 연결 대기...")
    time.sleep(5)

launch_robot_chrome()

# ==========================================
# 🔗 [2단계] 크롬 연결
# ==========================================
driver = None
for i in range(5):
    try:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.minimize_window()
            time.sleep(0.5)
            driver.maximize_window()
            driver.switch_to.window(driver.current_window_handle)
        except: pass
        
        params = {'behavior': 'allow', 'downloadPath': my_dl_dir}
        driver.execute_cdp_cmd('Page.setDownloadBehavior', params)
        print("✅ 연결 성공!")
        break
    except Exception as e:
        if i < 4: time.sleep(3)
        else: print(f"❌ 연결 실패: {e}"); raise

# ==========================================
# 🔑 [3단계] 로그인
# ==========================================
if driver and "login" in driver.current_url:
    print("\n🚨 [로그인 프로세스 시작]")
    try:
        wait = WebDriverWait(driver, 5)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
        time.sleep(1)
        
        inputs = driver.find_elements(By.TAG_NAME, "input")
        text_inputs = [i for i in inputs if i.get_attribute("type") in ["text", "email", "password"]]
        if len(text_inputs) >= 2:
            id_box, pw_box = text_inputs[0], text_inputs[1]
            for box, val in [(id_box, supply_id), (pw_box, supply_pw)]:
                box.click(); box.send_keys(Keys.CONTROL + "a"); box.send_keys(Keys.BACKSPACE); time.sleep(0.3); box.send_keys(val)
            
            try:
                login_btn = driver.find_element(By.XPATH, "//button[contains(., '로그인') or contains(., 'Login')]")
                driver.execute_script("arguments[0].click();", login_btn)
            except: pw_box.send_keys(Keys.ENTER)
    except: pass

    print("    ⏳ 로그인 확인 중...")
    time.sleep(3)
    
    if "login" in driver.current_url:
        print("\n" + "!"*60)
        print("⛔ [주의] 자동 로그인이 완료되지 않았습니다.")
        print("👉 브라우저에서 **수동으로 로그인**을 완료해주세요.")
        input("✅ 로그인이 완료되었다면 [Enter] 키를 눌러주세요...")
        print("!"*60 + "\n")
    else:
        print("    🎉 로그인 성공 확인!")

if "registration" not in driver.current_url:
    driver.get("https://supplier.coupang.com/qvt/registration")
    time.sleep(3)

# ==========================================
# ⬇️ [4단계] 다운로드 루프
# ==========================================
print("\n🚀 견적서 다운로드 시작")
try:
    if 'doc' not in globals():
        from google.oauth2.service_account import Credentials
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file('key.json', scopes=scope)
        client = gspread.authorize(creds)
        doc = client.open_by_url(SHEET_URL)
    worksheet = doc.worksheet(target_sheet_name)
    df = pd.DataFrame(worksheet.get_all_records()).drop_duplicates(subset=['변환상품명'], keep='first')
    print(f"📋 총 {len(df)}개 상품 처리 예정")
except: df = pd.DataFrame()

wait = WebDriverWait(driver, 15)

for idx, row in df.iterrows():
    try:
        keyword_main = str(row.get('메인키워드', '')).strip()
        prod_name = str(row.get('변환상품명', '')).strip()
        full_search_text = keyword_main if keyword_main else prod_name
        
        img_path = str(row.get('대표이미지경로', '')).strip()
        if not full_search_text or not img_path: continue
        
        target_dir = os.path.dirname(img_path)
        print(f"\n🔹 [{idx+1}] 검색 대상: {full_search_text[:20]}...")

        if glob.glob(os.path.join(target_dir, "*견적서*.xlsx")):
            print("    ⏭️ 이미 있음. 패스")
            continue

        if "registration" not in driver.current_url:
            driver.get("https://supplier.coupang.com/qvt/registration")
            time.sleep(2)
            check_browser_error(driver)

        # 다운로드 모달 열기
        try:
            dl_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Download latest excel file')]")))
            driver.execute_script("arguments[0].click();", dl_btn)
            time.sleep(1.5)
        except:
            check_browser_error(driver)
            driver.refresh(); time.sleep(3); continue

        # 검색 로직
        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "div.modal-body input[type='text']")))
        
        words = full_search_text.split()
        candidates = []
        candidates.append(full_search_text) 
        if len(words) >= 3: candidates.append(" ".join(words[:3])) 
        if len(words) >= 2: candidates.append(" ".join(words[:2])) 

        final_success = False

        for keyword in candidates:
            try:
                search_input.click()
                search_input.send_keys(Keys.CONTROL + "a")
                search_input.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                search_input.send_keys(keyword)
                time.sleep(0.5)
                search_input.send_keys(Keys.ENTER)
                
                print(f"    ⏳ '{keyword}' 검색 중...")
                time.sleep(4)

                cat_link = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="controlled-tab-example-pane-name"]/div[1]/div[1]/div/div/div/ul/li[1]/a')))
                driver.execute_script("arguments[0].click();", cat_link)
                
                print(f"    ✅ 카테고리 선택 성공!")
                final_success = True
                break 
            except:
                print(f"    ⚠️ '{keyword}' 검색 결과 없음. 재시도...")
                time.sleep(1)

        if not final_success:
            print("    ❌ 검색 실패.")
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            continue
        
        # 다운로드 버튼 클릭
        try:
            search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Search')]")))
            driver.execute_script("arguments[0].click();", search_btn)
            time.sleep(3)
            
            dn_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='modal-footer']//button[contains(., 'Download')]")))
            driver.execute_script("arguments[0].click();", dn_btn)
            print("    ⬇️ 다운로드 요청")
            time.sleep(5) 
            
            latest_check = glob.glob(os.path.join(my_dl_dir, "*.zip"))
            if not latest_check: 
                 print("    ⚠️ 파일 미감지. 버튼 재클릭...")
                 driver.execute_script("arguments[0].click();", dn_btn)
                 time.sleep(5)

        except Exception as e:
            print(f"    ⚠️ 버튼 오류: {e}")
            continue

        # 파일 이동 및 PDF 제외 로직
        file_found = False
        for _ in range(30):
            time.sleep(1)
            zips = glob.glob(os.path.join(my_dl_dir, "*.zip"))
            if not zips: continue
            latest = max(zips, key=os.path.getmtime)
            if time.time() - os.path.getmtime(latest) < 40:
                try:
                    # ‼️ [수정됨] PDF 제외하고 압축 풀기
                    with zipfile.ZipFile(latest, 'r') as z:
                        for file_info in z.infolist():
                            # 파일명 끝이 .pdf 면 건너뛰기 (대소문자 무시)
                            if file_info.filename.lower().endswith('.pdf'):
                                continue
                            z.extract(file_info, target_dir)

                    print(f"    📦 완료 (PDF 제외됨) -> {os.path.basename(target_dir)}")
                    
                    # ‼️ [수정됨] ZIP 파일 삭제 (휴지통 기능 대신 영구 삭제로 깔끔하게 처리)
                    file_found = True
                    os.remove(latest) 
                    print("    🗑️ 다운로드 받은 ZIP 파일 삭제 완료")
                    break
                except Exception as e: 
                    print(f"    ⚠️ 압축 해제 중 오류: {e}")
                    pass
        
        if not file_found: 
            print(f"    ❌ 다운로드 실패 (타임아웃)")
        
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)

    except Exception as e:
        print(f"    ⚠️ 오류: {e}")
        check_browser_error(driver) 
        try: driver.refresh(); time.sleep(3)
        except: pass

print("\n🎉 [ Cell 8 ] 다운로드 완료!")