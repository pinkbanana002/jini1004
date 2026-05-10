# [ Cell 10 ] (Final_Move) 최종 이관 및 시트 정리 (백업 헤더 자동 추가)
import os
import shutil
import pandas as pd
import gspread
import time
import gc # 메모리 청소용

print("▶️ [ Cell 10 ] 최종 이관 작업을 준비합니다 (엑셀 프로세스 강제 정리 포함)...")

# ==============================================================================
# 🛠️ [기능 1] 방해꾼(엑셀) 강제 종료 함수
# ==============================================================================
def kill_excel_process():
    try:
        # 실행 중인 엑셀이 있다면 강제로 끕니다.
        os.system("taskkill /f /im excel.exe >nul 2>&1")
        time.sleep(1) 
        gc.collect() 
    except: pass

# ==============================================================================
# 📂 [기능 2] 끈질긴 폴더 이동 함수
# ==============================================================================
def force_move_folder(src, dst, max_retries=3):
    # 목적지에 이미 폴더가 있으면 삭제 (덮어쓰기 위해)
    if os.path.exists(dst):
        try: shutil.rmtree(dst)
        except: pass

    for i in range(max_retries):
        try:
            shutil.move(src, dst)
            return True
        except PermissionError: 
            # 윈도우가 파일을 잡고 있을 때
            print(f"    ⚠️ 이동 실패 ({i+1}/{max_retries})... 엑셀이 파일을 잡고 있습니다. 2초 대기")
            kill_excel_process() # 엑셀 한번 더 죽이기
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠️ 이동 오류: {e}")
            time.sleep(1)
    return False

# ==============================================================================
# 🚀 메인 로직 실행
# ==============================================================================
try:
    # 1. 엑셀 강제 종료 (파일 잠금 해제)
    kill_excel_process()

    # 2. 시트 데이터 읽기
    if 'doc' not in globals(): raise NameError("구글 시트 연결 끊김")
    worksheet = doc.worksheet('상품등록목록')
    raw_data = worksheet.get_all_records()
    df = pd.DataFrame(raw_data)
    
    # 작업 대상 (변환상품명이 있고, 아직 폴더가 남아있는 것들)
    target_df = df[df['변환상품명'] != ""].drop_duplicates(subset=['변환상품명'])
    
    print("\n" + "="*50)
    print(f"🧐 [최종 검수 단계] 총 {len(target_df)}개의 상품이 정리 대상입니다.")
    print("    - 이 작업은 PC의 '작업폴더'를 '완료된_상품' 폴더로 이동시키고")
    print("    - 구글 시트의 데이터를 '완료' 시트로 백업 후 초기화합니다.")
    print("="*50)

    user_input = input("🚀 정리 작업을 시작하려면 [Enter]를 누르세요 (취소: n): ")
    
    if user_input.strip().lower() == 'n':
        print("⛔ 작업이 취소되었습니다.")
    else:
        print(f"    📦 데이터 및 폴더 이관을 시작합니다...")
        
        # [A] '완료' 시트로 백업
        try:
            done_sheet = doc.worksheet('완료')
        except:
            print("    🆕 '완료' 시트가 없어서 새로 만듭니다.")
            done_sheet = doc.add_worksheet('완료', rows=1000, cols=30)
            
        # ‼️ [보강] 백업 시트가 비어있다면 헤더(제목줄)부터 넣어주기
        if len(done_sheet.get_all_values()) == 0:
            done_sheet.append_row(df.columns.tolist())

        # 데이터 추가 (append)
        done_sheet.append_rows(df.values.tolist()) 
        print("    ✅ '완료' 시트로 데이터 복사 완료.")

        # [B] 폴더 이동
        # 완료 폴더 경로 설정
        if 'PATH_COMPLETED' in globals(): COMPLETED_DIR = PATH_COMPLETED
        else: COMPLETED_DIR = os.path.join(os.getcwd(), "완료된_상품")
        if not os.path.exists(COMPLETED_DIR): os.makedirs(COMPLETED_DIR)

        moved_count = 0
        for idx, row in target_df.iterrows():
            src_path_raw = str(row.get('대표이미지경로', '')).strip()
            if not src_path_raw: continue
            
            # 대표이미지 폴더의 상위 폴더(상품 전체 폴더)를 옮겨야 함
            product_folder = os.path.dirname(src_path_raw)
            if not os.path.exists(product_folder): continue # 폴더가 없으면 패스

            folder_name = os.path.basename(product_folder)
            dest_path = os.path.join(COMPLETED_DIR, folder_name)
            
            if force_move_folder(product_folder, dest_path):
                moved_count += 1
            else:
                print(f"    ❌ 이동 실패: {folder_name} (수동 이동 필요)")

        print(f"    📂 PC 폴더 이동 완료: 총 {moved_count}개 -> {COMPLETED_DIR}")

        # [C] '상품등록목록' 시트 초기화
        # 2행부터 내용 지우기
        worksheet.resize(rows=2) # 안전하게 줄였다가
        worksheet.resize(rows=1000) # 다시 늘림
        
        range_to_clear = f"A2:AZ1000"
        worksheet.batch_clear([range_to_clear])
        
        print("    ✅ '상품등록목록' 시트 초기화 완료.")
        print("\n🎉🎉 [ Cell 10 ] 모든 작업이 성공적으로 마무리되었습니다!")

except Exception as e:
    print(f"❌ [ Cell 10 ] 오류 발생: {e}")