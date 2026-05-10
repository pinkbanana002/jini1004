# [ Cell 7-1 ] 경로 최신화 및 '품질 표시 라벨' 자동 생성 (폰트 안전 모드)
# 설명: 1. Cell 4-2에서 적용한 엑셀 수식을 깨트리지 않기 위해, '경로' 열만 부분 업데이트합니다.
#       2. Cell 0의 브랜드 정보를 사용하여 라벨을 생성합니다.

import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont 
import textwrap 
import gspread
from gspread.utils import rowcol_to_a1
import re

print("▶️ [ Cell 7-1 ] 경로 동기화(수식 보호) 및 라벨 생성을 시작합니다...")

# ==============================================================
# 🚨 [안전장치 1] 필수 변수 및 폰트 체크
# ==============================================================
if 'MY_BRAND_NAME' not in globals():
    print("⚠️ [경고] Cell 0이 실행되지 않았습니다. 기본값으로 진행합니다.")
    MY_BRAND_NAME = "브랜드명"
    MY_COMPANY_NAME = "업체명"
    MY_PHONE_NUMBER = "010-0000-0000"
    PATH_FONTS = os.path.join(os.getcwd(), "fonts")
    FONT_BOLD = "malgun.ttf" # 윈도우 기본

# 폰트 경로 설정 (Cell 0에서 설정한 폰트 우선 사용)
font_path = os.path.join(PATH_FONTS, FONT_BOLD)
if not os.path.exists(font_path):
    # 폰트 파일이 없으면 윈도우 기본 폰트 시도, 맥이면 AppleGothic 시도
    font_path = "malgun.ttf" 
    if not os.path.exists("C:/Windows/Fonts/malgun.ttf"): # 윈도우가 아니면
        font_path = "/System/Library/Fonts/AppleGothic.ttf" # 맥

# --- [설정] 라벨 디자인 ---
LABEL_WIDTH = 600             
LABEL_HEIGHT = 600            
BG_COLOR = "white"
TEXT_COLOR = "black"

def load_font(path, size):
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default() # 최후의 수단: 기본 폰트

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

try:
    # 1. 시트 연결 및 데이터 읽기
    try: worksheet = doc.worksheet('상품등록목록')
    except: print("❌ '상품등록목록' 시트를 찾을 수 없습니다."); raise

    all_values = worksheet.get_all_values()
    if len(all_values) < 2: raise ValueError("❌ 데이터가 없습니다.")
    
    headers = all_values[0]
    df = pd.DataFrame(all_values[1:], columns=headers)
    
    current_dir = os.getcwd()
    
    # 2. 🔍 [핵심 수정] 컬럼 위치 유연하게 찾기
    def get_col_idx(names):
        for i, h in enumerate(headers):
            for n in names:
                if n in h.replace(" ",""): return i + 1 # 엑셀은 1부터 시작
        return -1

    col_idx_img = get_col_idx(['대표이미지경로', '이미지경로'])
    col_idx_copy = get_col_idx(['COPY폴더경로', 'COPY'])
    
    if col_idx_img == -1:
        raise ValueError("❌ 필수 열('대표이미지경로')을 찾을 수 없습니다.")

    print(f"    🔎 업데이트 대상 열: {col_idx_img}열(대표), {col_idx_copy}열(COPY)")
    print("    🔄 [동기화] 변경된 폴더명을 계산하고 라벨을 생성합니다...")
    
    updated_count = 0
    label_count = 0
    processed_folders = set()
    
    new_img_paths = []
    new_copy_paths = []

    for idx, row in df.iterrows():
        # 기존 값 (안전하게 가져오기)
        # col_idx는 1부터 시작하므로 pandas iloc(0부터 시작) 쓸 때는 -1 해줘야 함
        curr_img_path = str(row.iloc[col_idx_img-1]) if col_idx_img-1 < len(row) else ""
        curr_copy_path = str(row.iloc[col_idx_copy-1]) if col_idx_copy > 0 and col_idx_copy-1 < len(row) else ""
        
        final_img_path = curr_img_path
        final_copy_path = curr_copy_path

        try:
            # 2. 바뀐 상품명(폴더명) 추적
            prod_name = str(row.get('변환상품명', '')).strip()
            
            if prod_name:
                clean_prod_name = sanitize_filename(prod_name)
                
                # 새 폴더 주소 구성
                new_product_folder = os.path.join(current_dir, clean_prod_name)
                new_rep_folder = os.path.join(new_product_folder, "대표이미지")
                new_copy_folder = os.path.join(new_rep_folder, "copy")
                
                # 3. [검증] 폴더 존재 여부 확인
                if os.path.exists(new_rep_folder):
                    final_img_path = new_rep_folder
                    
                    if str(row.get('옵션2', '')).strip():
                        final_copy_path = new_copy_folder
                    else:
                        final_copy_path = ""
                    
                    if final_img_path != curr_img_path: updated_count += 1
                    
                    # -----------------------------------------------------
                    # 4. 🎨 품질 표시 라벨 생성 (상품당 1번만)
                    # -----------------------------------------------------
                    if new_product_folder not in processed_folders:
                        processed_folders.add(new_product_folder)
                        
                        material = str(row.get('재질', '')).strip()
                        if not material: material = "상세페이지 참조"

                        canvas = Image.new('RGB', (LABEL_WIDTH, LABEL_HEIGHT), BG_COLOR)
                        draw = ImageDraw.Draw(canvas)
                        
                        # 폰트 로드 (Cell 0 폰트 사용)
                        font_header = load_font(font_path, 40)
                        font_bold = load_font(font_path, 22)
                        font_val = load_font(font_path, 20)

                        current_y = 50
                        center_x = LABEL_WIDTH // 2
                        left_margin = 40
                        value_margin = 210
                        
                        # 헤더
                        draw.text((center_x, current_y), MY_BRAND_NAME, font=font_header, fill=TEXT_COLOR, anchor="mm")
                        current_y += 60
                        draw.line([(40, current_y), (LABEL_WIDTH-40, current_y)], fill="black", width=2)
                        current_y += 30

                        # 내용
                        info_list = [
                            ("제품명", prod_name),
                            ("재질", material),
                            ("제조국명", "중국(Made in China)"),
                            ("수입/판매자", MY_COMPANY_NAME),
                            ("소비자상담", MY_PHONE_NUMBER),
                            ("취급 주의", "화기에 주의하세요/충격주의"),
                            ("사용 연령", "14세 이상 사용가능")
                        ]
                        
                        for key, value in info_list:
                            draw.text((left_margin, current_y), f"{key} :", font=font_bold, fill=TEXT_COLOR, anchor="lm")
                            wrapper = textwrap.TextWrapper(width=18)
                            word_list = wrapper.wrap(text=str(value))
                            for line in word_list:
                                draw.text((value_margin, current_y), line, font=font_val, fill=TEXT_COLOR, anchor="lm")
                                current_y += 28
                            current_y += 12 

                        current_y += 30
                        box_w, box_h = 400, 100
                        box_x1 = (LABEL_WIDTH - box_w) // 2
                        box_y1 = current_y
                        box_x2 = box_x1 + box_w
                        box_y2 = box_y1 + box_h
                        
                        draw.rectangle([box_x1, box_y1, box_x2, box_y2], outline="black", width=2)
                        draw.text(((box_x1+box_x2)//2, (box_y1+box_y2)//2), "[ 바코드 부착 위치 ]", font=font_bold, fill="gray", anchor="mm")

                        save_name = "barcode.png"
                        canvas.save(os.path.join(new_product_folder, save_name))
                        label_count += 1

        except Exception as e:
            # print(f"    ⚠️ 오류 (행 {idx+2}): {e}")
            pass
        
        # 리스트에 추가
        new_img_paths.append([final_img_path])
        new_copy_paths.append([final_copy_path])

    # 5. 부분 업데이트 (수식 보호)
    if new_img_paths:
        print("    💾 시트 경로 열만 부분 업데이트 중...")
        end_row = 1 + len(new_img_paths)
        
        # 대표이미지경로 열 업데이트
        worksheet.update(
            range_name=f"{rowcol_to_a1(2, col_idx_img)}:{rowcol_to_a1(end_row, col_idx_img)}", 
            values=new_img_paths
        )
        # COPY폴더 경로 열 업데이트 (존재 시)
        if col_idx_copy > 0:
            worksheet.update(
                range_name=f"{rowcol_to_a1(2, col_idx_copy)}:{rowcol_to_a1(end_row, col_idx_copy)}", 
                values=new_copy_paths
            )

    print("-" * 40)
    print(f"🎉 [ Cell 7-1 ] 완료! (엑셀 수식은 안전하게 보호되었습니다)")
    print(f"    ✅ 경로 동기화: {updated_count}건")
    print(f"    🏷️ 라벨 생성: {label_count}개 상품")

except Exception as e:
    print(f"❌ 실행 중 오류 발생: {e}")