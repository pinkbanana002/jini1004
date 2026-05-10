# [ Cell 7 ] (Final_Auto_Close) 폴더명 변경 및 파일 정리 (열린 폴더 자동 닫기)
import pandas as pd
import gspread
import shutil
import os
import re
import time
import subprocess # 명령어 실행용

print("▶️ [ Cell 7 ] 최종 정리 작업을 시작합니다 (폴더 자동 닫기 모드)...")

# 🗑️ [필수] 좀비 데이터 방지
if 'crawled_buffer' in globals():
    del crawled_buffer
    print("    🧹 과거 수집 메모리 삭제 완료.")

# ------------------------------------------------------------------
# 🚪 [신규 기능] 열려있는 모든 폴더(탐색기) 자동 닫기 함수
# ------------------------------------------------------------------
def close_all_explorer_windows():
    print("    🚪 충돌 방지를 위해 열려있는 모든 폴더 창을 닫습니다...")
    try:
        # [SAFE-FILTER] 원래 코드는 Shell.Application.Windows() 의 결과를
        # 전부 Quit() 했지만, 이 컬렉션은 Windows 11 에서 IE/Chrome 등
        # 셸 통합 창까지 포함하여 사용자 크롬 창이 같이 닫히는 사고가 발생.
        # 따라서 FullName 이 explorer.exe 로 끝나는 창(=실제 파일 탐색기)만
        # 정확히 골라서 닫는다.
        ps_command = (
            'powershell -NoProfile -Command "'
            '(New-Object -ComObject Shell.Application).Windows() |'
            ' Where-Object { $_.FullName -like \'*\\explorer.exe\' } |'
            ' ForEach-Object { $_.Quit() }"'
        )
        subprocess.run(ps_command, shell=True)
        time.sleep(2) # 닫히는 시간 대기
        print("    ✨ 모든 폴더 창 닫기 완료!")
    except Exception as e:
        print(f"    ⚠️ 폴더 닫기 실패 (수동으로 닫아주세요): {e}")
# 파일명 특수문자 제거
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

try:
    if 'doc' not in globals():
        raise NameError("구글 시트 연결(doc)이 없습니다. Cell 2를 실행해주세요.")

    # 0. 작업 시작 전 폴더 창 싹 닫기 (에러 원천 차단)
    close_all_explorer_windows()

    # 1. 구글 시트 데이터 가져오기
    worksheet = doc.worksheet('상품등록목록')
    all_data = worksheet.get_all_records()
    df_processed = pd.DataFrame(all_data)
    
    processed_count = 0
    copy_count = 0
    folders_to_rename = {} # 나중에 바꿀 폴더 목록

    # 2. 파일명 변경 작업
    for index, row in df_processed.iterrows():
        try:
            sheet_path = str(row.get('대표이미지경로', '')).strip()
            new_prod_name = str(row.get('변환상품명', '')).strip()
            full_opt_name = str(row.get('전체옵션명', '')).strip()
            
            opt1_val = str(row.get('옵션1', '')).strip()
            if not opt1_val: opt1_val = full_opt_name.split()[0] 
            
            opt2_val = str(row.get('옵션2', '')).strip()

            if not sheet_path or not os.path.exists(sheet_path): continue

            # 폴더명 변경 예약
            prod_root = os.path.dirname(sheet_path)
            if new_prod_name:
                folders_to_rename[prod_root] = sanitize_filename(new_prod_name)

            # 원본 파일 찾기
            src_name = f"{sanitize_filename(opt1_val)}.jpg"
            src_path = os.path.join(sheet_path, src_name)
            
            if not os.path.exists(src_path):
                src_path_png = os.path.join(sheet_path, f"{sanitize_filename(opt1_val)}.png")
                if os.path.exists(src_path_png): src_path = src_path_png

            if not os.path.exists(src_path): continue

            # [A] 옵션2 있음 -> COPY 폴더로 복사
            if opt2_val and opt2_val != "단일 옵션":
                copy_dir = os.path.join(sheet_path, "copy")
                if not os.path.exists(copy_dir): os.makedirs(copy_dir)
                
                dst_name = f"{sanitize_filename(full_opt_name)}.jpg"
                dst_path = os.path.join(copy_dir, dst_name)

                try:
                    shutil.copy2(src_path, dst_path)
                    copy_count += 1
                except Exception as e:
                    print(f"    ⚠️ 복사 실패 ({src_name}): {e}")

            # [B] 옵션2 없음 -> 원본 이름 변경
            else:
                dst_name = f"{sanitize_filename(full_opt_name)}.jpg"
                dst_path = os.path.join(sheet_path, dst_name)
                
                if src_path != dst_path:
                    if os.path.exists(dst_path):
                        try: os.remove(dst_path)
                        except: pass
                    
                    try:
                        os.rename(src_path, dst_path)
                        processed_count += 1
                    except Exception as e:
                        print(f"    ⚠️ 이름변경 실패 ({src_name}): {e}")

        except Exception as e: pass

    # 3. 폴더명 일괄 변경 (가장 에러 많이 나는 구간)
    print(f"\n🔄 폴더명 변경 시작 (대상: {len(folders_to_rename)}개)")
    
    for old_path, new_name in folders_to_rename.items():
        try:
            if not os.path.exists(old_path): continue
            
            parent_dir = os.path.dirname(old_path)
            new_path = os.path.join(parent_dir, new_name)
            
            if os.path.basename(old_path) == new_name: continue
            if os.path.exists(new_path):
                # print(f"    ⚠️ 이미 존재하는 폴더명: {new_name}")
                continue

            # ⏳ [강력한 변경 시도]
            rename_success = False
            for retry in range(5): 
                try:
                    os.rename(old_path, new_path)
                    print(f"    ✅ 폴더명 변경: {new_name}")
                    rename_success = True
                    break
                except PermissionError:
                    # 윈도우가 파일을 잡고 있을 때
                    print(f"    ⏳ [{retry+1}/5] 폴더가 아직 사용 중입니다... (3초 대기)")
                    time.sleep(3)
                    # 혹시 모르니 다시 한번 닫기 시도
                    if retry == 2: close_all_explorer_windows()
                except Exception as e:
                    print(f"    ❌ 오류: {e}")
                    break
            
            if not rename_success:
                print(f"    ⛔ [실패] '{os.path.basename(old_path)}' 폴더를 수동으로 닫아주세요!")

        except Exception as e:
            print(f"    ❌ 예외 발생: {e}")

    print("-" * 40)
    print(f"🎉 [ Cell 7 ] 작업 완료! (파일처리: {processed_count+copy_count}개)")

except Exception as e:
    print(f"❌ 치명적 오류: {e}")