# [ Cell 6-2 ] (Final_Upgraded) 파일명 변경 + 400px 자동 확대 + [추가이미지 생성]
import os
import pandas as pd
import re
import shutil
import gspread
import time # 👈 API 대기용 추가
from PIL import Image # 이미지 처리를 위해 필수

# 🗑️ [필수] 좀비 데이터 방지
if 'crawled_buffer' in globals():
    del crawled_buffer
    print("🧹 과거 수집 메모리 삭제 완료.")

if 'BASE_DRIVE' not in globals(): BASE_DRIVE = os.getcwd()

print("▶️ [ Cell 6-2 ] 파일명 변경, 400px 확대, 그리고 [추가이미지 JPG 생성] 작업을 시작합니다...")

# [수정] 쉼표(,)는 제거하지만 마침표(.)는 유지하는 버전
def sanitize_filename(name):
    # 1. 쉼표만 제거 (replace 사용)
    clean_name = str(name).replace(",", "")
    # 2. 나머지 금지 문자(\ / : * ? " < > |) 제거 (마침표 . 는 제외)
    return re.sub(r'[\\/*?:"<>|]', "", clean_name).strip()

try:
    if 'doc' not in globals():
        raise NameError("구글 시트 연결(doc)이 없습니다. Cell 2를 실행해주세요.")

    worksheet = doc.worksheet('상품등록목록')
    all_values = worksheet.get_all_values()
    
    if len(all_values) < 2: 
        print("⚠️ 데이터가 없습니다.")
    else:
        data_rows = all_values[1:] 
        headers = all_values[0]
        
        # -------------------------------------------------------
        # 인덱스 찾기
        # -------------------------------------------------------
        path_idx = 8  # I열 (대표이미지경로)
        temp_idx = 25 # Z열 (임시파일명)
        
        opt1_idx = -1
        for i, h in enumerate(headers):
            if h == "옵션1": opt1_idx = i; break
        
        # [추가] 옵션2 인덱스도 찾기 (시트 수정을 위해)
        opt2_idx = -1
        for i, h in enumerate(headers):
            if h == "옵션2": opt2_idx = i; break
            
        full_idx = 10 # K열
        for i, h in enumerate(headers):
            if "한글" in h and "옵션" in h: full_idx = i; break

        try:
            g_idx = headers.index('변환상품명') 
            h_idx = headers.index('메인키워드') 
        except:
            g_idx, h_idx = -1, -1

        success_count = 0
        fill_count = 0 
        resize_count = 0
        add_img_count = 0 # 추가이미지 생성 개수
        
        print("\n📝 [작업 내역]") 
        
        for r_idx, row in enumerate(data_rows):
            current_row_num = r_idx + 2 

            # =======================================================
            # 0️⃣ [추가됨] 옵션명 쉼표(,) 제거 및 시트 동기화 (마침표 유지)
            # =======================================================
            # 옵션1 쉼표 제거
            if opt1_idx != -1 and len(row) > opt1_idx:
                orig_o1 = str(row[opt1_idx])
                if "," in orig_o1:
                    clean_o1 = orig_o1.replace(",", "")
                    try:
                        worksheet.update_cell(current_row_num, opt1_idx + 1, clean_o1)
                        row[opt1_idx] = clean_o1 # 메모리 상의 row 데이터도 갱신 (중요!)
                        print(f"    🔄 [시트수정] 옵션1 쉼표제거: {orig_o1} -> {clean_o1}")
                        time.sleep(0.5) # API 제한 방지
                    except: pass
            
            # 옵션2 쉼표 제거
            if opt2_idx != -1 and len(row) > opt2_idx:
                orig_o2 = str(row[opt2_idx])
                if "," in orig_o2:
                    clean_o2 = orig_o2.replace(",", "")
                    try:
                        worksheet.update_cell(current_row_num, opt2_idx + 1, clean_o2)
                        row[opt2_idx] = clean_o2 # 메모리 갱신
                        print(f"    🔄 [시트수정] 옵션2 쉼표제거: {orig_o2} -> {clean_o2}")
                        time.sleep(0.5)
                    except: pass

            # =======================================================
            # 1️⃣ 메인키워드(H열) 자동 채우기
            # =======================================================
            if g_idx != -1 and h_idx != -1 and len(row) > max(g_idx, h_idx):
                g_val = str(row[g_idx]).strip() 
                h_val = str(row[h_idx]).strip() 
                
                if not h_val and g_val:
                    try:
                        worksheet.update_cell(current_row_num, h_idx + 1, g_val)
                        fill_count += 1
                        row[h_idx] = g_val 
                    except Exception as e:
                        pass

            # =======================================================
            # 2️⃣ 파일명 변경 + [400px 자동 확대]
            # =======================================================
            if len(row) <= path_idx or len(row) <= temp_idx: continue

            sheet_path = str(row[path_idx]).strip()
            temp_name = str(row[temp_idx]).strip()
            
            if not sheet_path or not temp_name: continue
            
            if opt1_idx != -1 and len(row) > opt1_idx and row[opt1_idx]:
                target_base = row[opt1_idx]
            else:
                val = str(row[full_idx]) if len(row) > full_idx else ""
                target_base = val.split()[0]
                
            target_base = sanitize_filename(target_base)
            
            # --- [파일명 변경 및 확대 로직 시작] ---
            if os.path.exists(sheet_path):
                # A. 대표이미지 처리
                candidates = [temp_name]
                if not temp_name.lower().endswith(('.jpg', '.png', '.jpeg')):
                      candidates.append(temp_name + ".jpg")

                for cand in candidates:
                    old_file = os.path.join(sheet_path, cand)
                    
                    if os.path.exists(old_file):
                        ext = os.path.splitext(old_file)[1]
                        if not ext: ext = ".jpg"
                        
                        new_file_name = target_base + ext
                        new_file = os.path.join(sheet_path, new_file_name)
                        
                        processed = False
                        try:
                            with Image.open(old_file) as img:
                                w, h = img.size
                                # 400px 미만 확대 로직
                                if w < 400 or h < 400:
                                    ratio = 400 / min(w, h)
                                    new_w = int(w * ratio)
                                    new_h = int(h * ratio)
                                    
                                    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS).convert("RGB")
                                    img_resized.save(new_file, quality=95)
                                    
                                    if old_file != new_file:
                                        os.remove(old_file)
                                    
                                    print(f"    📏 [확대] {cand} -> {new_file_name}")
                                    processed = True
                                    resize_count += 1
                                    success_count += 1
                        except Exception as e:
                            print(f"    ⚠️ 이미지 처리 오류: {e}")

                        # 확대 안 했으면 단순 이름 변경
                        if not processed and old_file != new_file:
                            try:
                                if os.path.exists(new_file): os.remove(new_file)
                                os.rename(old_file, new_file)
                                success_count += 1
                                print(f"    ✅ [변경] {cand} -> {new_file_name}")
                            except: pass
                        break 
                
                # =======================================================
                # 3️⃣ [NEW] 추가이미지 생성 (추가1.jpg, 추가2.jpg)
                # =======================================================
                try:
                    # sheet_path = .../상품명/대표이미지
                    # 한 단계 위로 올라가서 '상세페이지' 폴더를 찾음
                    product_root = os.path.dirname(sheet_path) 
                    detail_dir = os.path.join(product_root, "상세페이지")
                    target_add_dir = os.path.join(detail_dir, "추가이미지")
                    
                    if os.path.exists(detail_dir):
                        # detail_ 로 시작하는 파일만 찾아서 정렬
                        detail_files = sorted([f for f in os.listdir(detail_dir) if f.startswith('detail_')])
                        
                        if detail_files:
                            os.makedirs(target_add_dir, exist_ok=True)
                            
                            # 최대 2개까지만 만듦 (추가1, 추가2)
                            for i in range(min(2, len(detail_files))):
                                src_img_path = os.path.join(detail_dir, detail_files[i])
                                target_img_name = f"추가{i+1}.jpg"
                                target_img_path = os.path.join(target_add_dir, target_img_name)
                                
                                # 이미 있으면 건너뛰기 (시간 절약)
                                if not os.path.exists(target_img_path):
                                    with Image.open(src_img_path) as img:
                                        # ✨ 핵심: 무조건 JPG로 변환 (RGB 모드)
                                        img.convert("RGB").save(target_img_path, "JPEG", quality=95)
                                        add_img_count += 1
                                        # print(f"      ➕ 생성: {target_img_name}")
                except Exception as e:
                    print(f"    ⚠️ 추가이미지 생성 실패: {e}")
                # =======================================================

        print("\n" + "="*50)
        print(f"🎉 [ Cell 6-2 ] 모든 이미지 작업 완료!")
        print(f"📂 대표이미지 이름 변경: {success_count}개")
        print(f"📏 대표이미지 확대: {resize_count}개")
        print(f"📸 추가이미지(JPG) 생성: {add_img_count}개")
        print(f"✨ 키워드 채움: {fill_count}개")
        print("="*50)

except Exception as e:
    print(f"❌ 오류 발생: {e}")