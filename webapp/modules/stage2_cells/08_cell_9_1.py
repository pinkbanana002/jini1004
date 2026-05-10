# [ Cell 9-1 ] (Final_All_Details) 상품 등록 (상세 폴더 전체 + 추가이미지1,2 업로드 + 완벽 체크 이식)
import os, shutil, time, pandas as pd, glob, random
import requests
import gspread
from google.oauth2.service_account import Credentials
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==============================================================================
# 🎛️ [대표님 설정 구간]
# ==============================================================================
DAILY_LIMIT = 50        # 🛑 하루 목표
REST_EVERY  = 10        # ☕ 휴식 주기
LONG_REST_SEC = 180     # 🛌 휴식 시간

# 📂 [완료 폴더 경로 자동 설정]
CURRENT_WORK_DIR = os.getcwd()
COMPLETED_DIR = os.path.join(CURRENT_WORK_DIR, "완료된_상품")

if not os.path.exists(COMPLETED_DIR): 
    os.makedirs(COMPLETED_DIR)
    print(f"✨ [자동 생성] 완료 폴더: {COMPLETED_DIR}")
else:
    print(f"📂 [경로 확인] 완료 폴더: {COMPLETED_DIR}")
# ==============================================================================

print(f"▶️ [ Cell 9-1 ] 상품 등록 시작 (상세페이지 전체 업로드 Ver)...")

# ------------------------------------------------------------------
# 🌐 인터넷 및 시트 연결 도구
# ------------------------------------------------------------------
def wait_for_internet():
    while True:
        try:
            requests.get("https://www.google.com", timeout=3)
            return True 
        except:
            print("    🚨 [네트워크 오류] 인터넷 연결 대기 중...")
            time.sleep(10)

def ensure_sheet_connection():
    global doc, worksheet
    try:
        _ = doc.title 
    except:
        print("    🔌 [시트 재연결] 연결을 복구합니다...")
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file('key.json', scopes=scope)
            client = gspread.authorize(creds)
            doc = client.open_by_url(SHEET_URL)
            worksheet = doc.worksheet('상품등록목록')
            print("    ✅ 재연결 성공")
        except Exception as e:
            print(f"    ❌ 재연결 실패: {e}")
            time.sleep(10); ensure_sheet_connection()

def human_sleep(min_sec=1.5, max_sec=4.0):
    time.sleep(random.uniform(min_sec, max_sec))

# 🛠️ [기본 파일 찾기 함수]
def find_file(folder, keywords, ext_list):
    if not os.path.exists(folder): return None
    for f in os.listdir(folder):
        if not any(f.lower().endswith(ext) for ext in ext_list): continue
        if any(k in f for k in keywords): return os.path.join(folder, f)
    return None

# --- 메인 로직 ---
if 'driver' in globals() and driver is not None:
    ensure_sheet_connection() 
    try:
        raw_df = pd.DataFrame(worksheet.get_all_records())
        df = raw_df.drop_duplicates(subset=['변환상품명'], keep='first')
        print(f"📋 총 {len(df)}개의 상품 데이터가 로드되었습니다.\n")
    except: print("❌ 구글 시트 읽기 실패"); df = pd.DataFrame()

    success_count = 0
    wait = WebDriverWait(driver, 15)

    def reset_registration_page(driver):
        wait_for_internet() 
        try:
            target_url = "https://supplier.coupang.com/qvt/registration"
            if target_url not in driver.current_url:
                driver.get(target_url)
            else:
                driver.refresh()
            print("    🔄 페이지 초기화 (5초 대기)...")
            time.sleep(5)
        except: pass

    for idx, row in df.iterrows():
        wait_for_internet()
        ensure_sheet_connection()

        if success_count >= DAILY_LIMIT:
            print(f"\n🛑 일일 목표({DAILY_LIMIT}개) 달성! 작업을 종료합니다."); break

        if success_count > 0 and success_count % REST_EVERY == 0:
            print(f"\n☕ {success_count}개 완료. {LONG_REST_SEC}초 휴식...")
            time.sleep(LONG_REST_SEC)
            reset_registration_page(driver)

        prod_name = str(row.get('변환상품명', '')).strip()
        base_folder = str(row.get('대표이미지경로', '')).strip()
        
        if not base_folder or not os.path.exists(base_folder): continue
        product_root_folder = os.path.dirname(base_folder)

        print(f"\n🔹 [{idx+1}] '{prod_name}' 등록 시작")
        
        # ---------------------------------------------------------
        # 📂 [Step 1] 파일 경로 확보
        # ---------------------------------------------------------
        excel_path = find_file(product_root_folder, ["견적서", "카테고리"], [".xlsx"])
        size_chart_path = find_file(product_root_folder, ["사이즈", "사이즈표", "size"], [".jpg", ".png"])
        barcode_path = find_file(product_root_folder, ["barcode", "바코드"], [".png", ".jpg"])

        # ‼️ [수정됨] 상세copy이미지 폴더 내 '모든' 이미지 수집
        detail_img_paths = [] # 리스트로 변경
        
        detail_search_paths = [
            os.path.join(product_root_folder, "상세페이지", "상세copy이미지"), 
            os.path.join(product_root_folder, "상세페이지", "COPY"),
            os.path.join(product_root_folder, "상세페이지", "copy"),
            os.path.join(product_root_folder, "상세페이지")
        ]
        
        for d_path in detail_search_paths:
            if os.path.exists(d_path):
                # 해당 폴더의 모든 JPG 찾기
                all_jpgs = [f for f in os.listdir(d_path) if f.lower().endswith('.jpg')]
                
                if all_jpgs:
                    # 정렬 (이름순)
                    all_jpgs.sort()
                    
                    # 전체 경로 리스트 생성
                    detail_img_paths = [os.path.join(d_path, f) for f in all_jpgs]
                    
                    print(f"    🔍 상세페이지 폴더 발견: .../{os.path.basename(d_path)} (총 {len(detail_img_paths)}장)")
                    break 
        
        if not detail_img_paths:
            print("    ⚠️ [경고] 상세페이지 이미지를 찾을 수 없습니다!")

        # 🟢 [기존 유지] 추가이미지(추가1, 추가2) 찾기 로직
        additional_imgs = []
        add_img_folder = os.path.join(product_root_folder, "상세페이지", "추가이미지")
        
        if os.path.exists(add_img_folder):
            for fname in ["추가1.jpg", "추가2.jpg"]:
                fpath = os.path.join(add_img_folder, fname)
                if os.path.exists(fpath):
                    additional_imgs.append(fpath)
                    print(f"    📸 추가이미지 발견: {fname}")

        # 1. 대표 이미지 폴더 찾기
        target_image_folder = base_folder
        copy_candidates = [
            os.path.join(product_root_folder, "COPY"),
            os.path.join(product_root_folder, "copy"),
            os.path.join(base_folder, "COPY"),
            os.path.join(base_folder, "copy")
        ]
        
        for candidate in copy_candidates:
            if os.path.exists(candidate) and os.path.isdir(candidate):
                if any(f.lower().endswith('.jpg') for f in os.listdir(candidate)):
                    target_image_folder = candidate
                    break
        
        # 2. 대표 이미지 리스트
        representative_images = [
            os.path.join(target_image_folder, f) 
            for f in os.listdir(target_image_folder) 
            if f.lower().endswith('.jpg') and 'processed_final' not in f
        ]
        
        # 3. 최종 리스트 조합 (대표 -> [상세전체] -> [추가] -> 사이즈표)
        files_to_upload = []
        files_to_upload.extend(representative_images)
        
        # ‼️ [수정됨] 상세이미지 리스트 전체 추가 (extend 사용)
        if detail_img_paths: 
            files_to_upload.extend(detail_img_paths)
            
        # 🟢 추가이미지 리스트에 합치기
        if additional_imgs:
            files_to_upload.extend(additional_imgs)

        if size_chart_path:
            files_to_upload.append(size_chart_path)
            print(f"    📏 사이즈표 포함됨")
        
        if not excel_path: print("    ⚠️ 견적서 없음 (Pass)"); continue
        
        print(f"    ✅ 파일 준비 완료 ({len(files_to_upload)}장 / 상세전체+추가 포함)")

        # ---------------------------------------------------------
        # 📤 [Step 2] 업로드 시작
        # ---------------------------------------------------------
        try:
            wait_for_internet() 
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            human_sleep(1, 2)
            
            # [1] 견적서 업로드
            excel_upload_success = False
            for attempt in range(3):
                try:
                    file_inputs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='file']")))
                    if len(file_inputs) > 0:
                        file_inputs[0].send_keys(excel_path)
                        print(f"    📤 [1/3] 견적서 업로드 성공")
                        excel_upload_success = True
                        human_sleep(5, 7)
                        break
                    else: raise Exception("파일 입력창 없음")
                except: time.sleep(2)
            
            if not excel_upload_success:
                print("    ❌ 견적서 업로드 실패 -> 건너뜀")
                reset_registration_page(driver)
                continue

            # [2] 이미지 통합 업로드
            if files_to_upload:
                try:
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    print(f"    📤 [2/3] 이미지 일괄 업로드 ({len(files_to_upload)}장)...")
                    file_inputs[1].send_keys("\n".join(files_to_upload))
                    
                    print("    ⏳ 이미지 서버 전송 및 썸네일 생성 대기 (20초)...")
                    time.sleep(20) 
                except Exception as e:
                    print(f"    ❌ 이미지 업로드 오류: {e}")

            # [3] 바코드
            if barcode_path:
                try:
                    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                    print("    📤 [3/3] 바코드 업로드...")
                    file_inputs[2].send_keys(barcode_path)
                    human_sleep(4, 6)
                except: pass

            # =================================================================
            # 🟢 [하단 로직] 필수 항목 체크 + 안전 인증 + 등록 (완벽 이식 버전)
            # =================================================================
            print("\n    🖱️ 하단 필수 항목 체크 시작...")
            
            # 1. 무적의 Yes 클릭 (이 과정에서 로켓 설치가 눈치 없이 Yes로 눌릴 수 있습니다)
            try:
                print("      👉 [1/4] 모든 'Yes(예)' 버튼 일괄 클릭 (안전인증 동의)...")
                all_yes_labels = driver.find_elements(By.XPATH, "//label[normalize-space()='Yes' or normalize-space()='예']")
                for yes_label in all_yes_labels:
                    try:
                        driver.execute_script("arguments[0].click();", yes_label)
                        time.sleep(0.3)
                    except: pass
            except: pass

            # 2. 팝업 창 처리 (Agree 닫기)
            try:
                print("      👉 [2/4] 안전인증 팝업창 처리...")
                agree_btns = driver.find_elements(By.XPATH, "//button[normalize-space()='Agree' or normalize-space()='동의']")
                for btn in agree_btns:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print("      ✅ 'Agree' 팝업 닫기 완료!")
                        time.sleep(1)
            except: pass
            
            # (추가 안전인증 약관 텍스트 체크)
            try:
                content_agrees = driver.find_elements(By.XPATH, "//label[contains(., 'contents stated above') or contains(., '위 내용에 동의합니다')]")
                for ca in content_agrees:
                    driver.execute_script("arguments[0].click();", ca)
                    time.sleep(0.3)
            except: pass

            # 3. 법적 서류 N/A 클릭 (페이지에 있는 모든 N/A 라벨 자동 클릭)
            try:
                print("      👉 [3/4] 법적 서류 N/A 항목 체크...")

                # 페이지 끝까지 스크롤해서 모든 N/A가 DOM에 로드되도록
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.8)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.3)

                # 페이지의 모든 N/A 라벨 찾기 (대소문자/공백 변형 포함)
                all_na = driver.find_elements(By.XPATH, "//label[contains(., 'N/A') or contains(., 'n/a')]")
                print(f"      📋 N/A 라벨 {len(all_na)}개 발견")

                clicked_count = 0
                for idx, na_label in enumerate(all_na):
                    try:
                        # 클릭하기 전에 라벨 위치로 스크롤 (가려진 요소도 클릭 가능하게)
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", na_label)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", na_label)
                        clicked_count += 1
                        time.sleep(0.3)
                    except Exception as ne:
                        print(f"      ⚠️ N/A {idx+1}번째 클릭 실패: {type(ne).__name__}")

                print(f"      ✅ N/A 총 {clicked_count}/{len(all_na)}개 클릭 완료")

                # 클릭 후 페이지 맨 위로 복귀 (다음 단계 진행 위해)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
            except Exception as e:
                print(f"      ⚠️ N/A 처리 단계 오류: {e}")

            # 🚀 4. 로켓 설치 'No' 정밀 타격 클릭
            try:
                print("      👉 [4/4] 로켓 설치 여부 'No(아니오)'로 덮어씌우기...")
                rocket_no_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'rocket installation') or contains(text(), '로켓 설치') or contains(text(), '로켓설치')]//following::label[normalize-space()='No' or normalize-space()='아니오'][1]"
                
                rocket_no_label = wait.until(EC.presence_of_element_located((By.XPATH, rocket_no_xpath)))
                driver.execute_script("arguments[0].click();", rocket_no_label)
                print("      ✅ 로켓 설치 'No' 완벽 복구 완료!")
                time.sleep(0.5)
            except Exception as e: 
                print("      ⚠️ 로켓 설치 정밀 타격 실패, 기존 방식으로 재시도합니다.")
                try:
                    all_no_labels = driver.find_elements(By.XPATH, "//label[normalize-space()='No' or normalize-space()='아니오']")
                    if all_no_labels:
                        driver.execute_script("arguments[0].click();", all_no_labels[-1])
                except: pass

            # 5. 권장 소비자 가격 관련 특정 약관 동의
            try:
                retail_agree_xpath = "//input[@type='checkbox' and following-sibling::*[contains(., 'I hereby agree on Coupang')]] | //label[contains(., 'I hereby agree on Coupang')]"
                retail_element = wait.until(EC.presence_of_element_located((By.XPATH, retail_agree_xpath)))
                driver.execute_script("""
                    var el = arguments[0];
                    el.click();
                    var chk = (el.tagName === 'INPUT') ? el : el.querySelector('input[type="checkbox"]');
                    if (chk) {
                        chk.checked = true;
                        chk.dispatchEvent(new Event('change', { bubbles: true }));
                        chk.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                """, retail_element)
                print("      👉 권장 소비자 가격 약관 동의 체크 완료")
                time.sleep(2) 
            except Exception as e: pass

            # -----------------------------------------------------
            # [Step 3] 등록 버튼 클릭 및 팝업 처리 (스마트 대기 이식)
            # -----------------------------------------------------
            is_validate_clicked = False
            try:
                validate_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Validate')]")))
                driver.execute_script("arguments[0].click();", validate_btn)
                print("      👉 [Validate] 버튼 클릭 완료!")
                
                print("    ⏳ [스마트 대기] 결과 팝업을 기다리는 중입니다... (완료 시 즉시 진행)")
                try:
                    WebDriverWait(driver, 180).until(
                        EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Quotation has been submitted')]"))
                    )
                    print("      🚀 결과 팝업 감지 완료! 대기를 종료하고 다음 단계로 진행합니다.")
                    time.sleep(1)
                except:
                    print("      ⚠️ 180초 초과: 팝업을 감지하지 못했습니다. (오류 가능성 있음)")

                try:
                    close_btn = driver.find_element(By.XPATH, "//button[contains(., '닫기') or contains(., '확인') or contains(., 'Close')]")
                    driver.execute_script("arguments[0].click();", close_btn)
                    print("      👉 [6] 결과 팝업 '닫기' 버튼 클릭 완료")
                    time.sleep(5)
                    is_validate_clicked = True
                except:
                    print("      ⚠️ 팝업 '닫기' 버튼을 찾지 못했습니다.")

            except Exception as e:
                print(f"      ❌ 등록 버튼 처리 오류: {e}")

            # -----------------------------------------------------
            # [Step 4] 폴더 이동 (성공 시에만)
            # -----------------------------------------------------
            if is_validate_clicked:
                print("    🔄 페이지를 초기화합니다...")
                reset_registration_page(driver) 
                
                dest_path = os.path.join(COMPLETED_DIR, os.path.basename(product_root_folder))
                move_success = False
                for attempt in range(3):
                    try:
                        if os.path.exists(dest_path): shutil.rmtree(dest_path)
                        shutil.move(product_root_folder, dest_path)
                        move_success = True
                        break 
                    except PermissionError:
                        print("      ⏳ 파일 이동 대기 (3초)...")
                        time.sleep(3)
                    except Exception as e:
                        print(f"      ❌ 폴더 이동 오류: {e}"); break
                
                if move_success:
                    print(f"    📦 폴더 이동 완료: {os.path.basename(product_root_folder)}")
                    success_count += 1
                else:
                    print("    ❌ 폴더 이동 실패 (파일이 열려있을 수 있음)")
            else:
                 print("    ⛔ [이동 안함] 등록이 완료되지 않았습니다.")

        except Exception as e:
            print(f"    ❌ 치명적 오류: {e}")
            wait_for_internet()
            reset_registration_page(driver)

    print("\n" + "="*50)
    print(f"🎉 [ Cell 9-1 ] 작업 종료! (성공: {success_count}개)")
    print(f"👉 [확인] 완료된 상품은 '{COMPLETED_DIR}' 폴더에 있습니다.")
    print("="*50)