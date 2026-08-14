# [ Cell 7-2 ] (Final_Clean_Log) 초고속 상세페이지 제작 (로그 그룹화 적용)
from PIL import Image, ImageDraw, ImageFont
import os
import pandas as pd
import re
import textwrap
import glob
import requests
import json
import time
import random 
from io import BytesIO
import google.generativeai as genai

print("▶️ [ Cell 7-2 ] 초고속 상세페이지 제작 모드 (로그 요약형) 가동! 🚀...")

# ==============================================================
# 🚨 환경 설정
# ==============================================================
if 'PATH_TEMPLATES' not in globals() or 'PATH_FONTS' not in globals():
    BASE_DRIVE = os.getcwd()
    PATH_TEMPLATES = os.path.join(BASE_DRIVE, "templates")
    PATH_FONTS = os.path.join(BASE_DRIVE, "fonts")
    FONT_BOLD = "강원교육모두 Bold.ttf"
    FONT_REGULAR = "강원교육모두 Light.ttf"

if 'GEMINI_API_KEY' in globals() and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except: pass

# ==============================================================
# ⚡ 템플릿 로드
# ==============================================================
TARGET_WIDTH = 860

def load_and_resize_template(filename):
    path = os.path.join(PATH_TEMPLATES, filename)
    if os.path.exists(path):
        img = Image.open(path).convert("RGB")
        w_percent = (TARGET_WIDTH / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        return img.resize((TARGET_WIDTH, h_size), Image.Resampling.BICUBIC)
    return None

print("⏳ 템플릿 메모리 로딩 중...")
GLOBAL_LOGO = load_and_resize_template("상단로고.png")
GLOBAL_HEADER = load_and_resize_template("상단.jpg")
GLOBAL_FOOTER = load_and_resize_template("하단.jpg")
print("✅ 템플릿 로딩 완료.")

# ==============================================================
# 💰 유틸 및 캐시
# ==============================================================
if 'ai_planning_cache' not in globals():
    ai_planning_cache = {} 
total_api_calls = 0 

def get_font(name, size):
    font_path = os.path.join(PATH_FONTS, name)
    try: return ImageFont.truetype(font_path, size)
    except: return ImageFont.load_default()

def create_text_banner(text, width=860):
    lines = textwrap.wrap(text, width=22)
    line_h = 50
    h = 180 + (len(lines) * line_h)
    banner = Image.new("RGB", (width, h), (248, 249, 250))
    draw = ImageDraw.Draw(banner)
    f = get_font(FONT_BOLD, 34)
    draw.text((width//2, h//2), "\n".join(lines), font=f, fill="#222222", anchor="mm", align="center")
    return banner

def ask_ai_md_planning(img_url, prod_name, prod_link):
    global total_api_calls
    default_copies = ["품격 있는 디자인", "철저한 품질 관리", "빠른 안심 배송"]

    if 'model' not in globals() or not model or not img_url: 
        return default_copies

    if prod_link in ai_planning_cache:
        return ai_planning_cache[prod_link]

    try:
        res = requests.get(img_url, timeout=5)
        if res.status_code != 200: return default_copies
        
        img = Image.open(BytesIO(res.content))
        
        prompt = f"""
        상품명: {prod_name}
        이미지를 보고 고객의 마음을 사로잡을 셀링 포인트 3개를 기획하세요.
        - 전문 MD의 말투로 짧고 강렬하게 작성할 것.
        - 특수문자 금지.
        - '|' 기호로 구분하여 3개만 출력.
        """
        try:
            ai_res = model.generate_content([prompt, img])
        except:
            fallback_model = genai.GenerativeModel('gemini-flash-latest')
            ai_res = fallback_model.generate_content([prompt, img])

        result_copies = [c.strip() for c in ai_res.text.strip().split('|') if c.strip()][:3]
        if len(result_copies) < 3: result_copies = default_copies

        ai_planning_cache[prod_link] = result_copies
        total_api_calls += 1
        return result_copies
    except Exception as e:
        return default_copies

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()

def resize_width_fast(img, target_w):
    w_percent = (target_w / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    return img.resize((target_w, h_size), Image.Resampling.BICUBIC)

def make_final_detail_fast(row, detail_dir, save_path):
    try:
        p_name = str(row.get('변환상품명', '')).strip()
        opt_kor = str(row.get('한글 옵션명', '')).strip()
        full_sku = str(row.get('전체옵션명', '')).strip()
        img_url = str(row.get('대표이미지링크', '')).strip()
        prod_link = str(row.get('상품링크', '')).strip()
        material = str(row.get('재질', '상세페이지 참조')).strip() or "상세페이지 참조"
        
        rep_dir = str(row.get('대표이미지경로', '')).strip()
        if not rep_dir or not os.path.exists(rep_dir):
            print(f'    [7-2 FAIL] 대표이미지경로 없음/미존재: {rep_dir!r}'); return False

        if str(row.get('옵션2', '')).strip(): 
            rep_dir = os.path.join(rep_dir, "copy")
            
        exact_img = os.path.join(rep_dir, f"{sanitize_filename(full_sku)}.jpg")
        
        if not os.path.exists(exact_img):
            opt1_val = str(row.get('옵션1', '')).strip()
            search = glob.glob(os.path.join(rep_dir, f"*{sanitize_filename(opt1_val)}*.jpg"))
            if not search: 
                search = glob.glob(os.path.join(rep_dir, f"*{sanitize_filename(opt1_val)}*.png"))
                if not search:
                    print(f'    [7-2 FAIL] 옵션이미지 못찾음 dir={rep_dir!r} sku={full_sku!r} opt1={opt1_val!r}'); return False
            exact_img = search[0]

        logo = GLOBAL_LOGO.copy() if GLOBAL_LOGO else None
        header = GLOBAL_HEADER.copy() if GLOBAL_HEADER else Image.new("RGB", (TARGET_WIDTH, 500), "white")
        footer = GLOBAL_FOOTER.copy() if GLOBAL_FOOTER else Image.new("RGB", (TARGET_WIDTH, 500), "white")

        sku_img_800 = Image.open(exact_img).convert("RGB")
        sku_img_800 = resize_width_fast(sku_img_800, 800)

        ai_copies = ask_ai_md_planning(img_url, p_name, prod_link)
        
        draw_h = ImageDraw.Draw(header)
        h_cx = header.width // 2
        
        draw_h.text((h_cx, 110), textwrap.fill(p_name, width=20), font=get_font(FONT_BOLD, 45), fill="black", anchor="mm", align="center")
        draw_h.text((h_cx, 230), opt_kor, font=get_font(FONT_BOLD, 35), fill="#555555", anchor="mm")
        
        header.paste(sku_img_800, ((header.width-800)//2, 340))

        mid_files = sorted([os.path.join(detail_dir, f) for f in os.listdir(detail_dir) if f.lower().endswith(('.jpg', '.png')) and "상세_" not in f])
        body_parts = []
        if len(mid_files) > 20: mid_files = mid_files[:20]

        for i, f in enumerate(mid_files):
            try:
                img_obj = Image.open(f).convert("RGB")
                img_obj = resize_width_fast(img_obj, TARGET_WIDTH)
                body_parts.append(img_obj)
                if i < len(ai_copies):
                    body_parts.append(create_text_banner(ai_copies[i], width=TARGET_WIDTH))
            except: pass

        draw_f = ImageDraw.Draw(footer)
        footer.paste(sku_img_800, ((footer.width-800)//2, 50))
        
        brand_val = MY_BRAND_NAME if 'MY_BRAND_NAME' in globals() else "상세페이지 참조"
        info_lines = [f"상품명 : {p_name}", f"옵션명 : {opt_kor}", "제조국 : Made in China (중국)", f"수입사 : {brand_val}", f"재질 : {material}"]
        
        TARGET_X, START_Y = 430, 1000
        for i, line in enumerate(info_lines):
            draw_f.text((TARGET_X, START_Y + (i * 60)), line, font=get_font(FONT_REGULAR, 26), fill="black", anchor="mm")

        all_imgs = ([logo] if logo else []) + [header] + body_parts + [footer]
        
        total_h = sum(img.height for img in all_imgs)
        canvas = Image.new("RGB", (TARGET_WIDTH, total_h), "white")
        curr_y = 0
        for img in all_imgs:
            canvas.paste(img, (0, curr_y))
            curr_y += img.height
        
        canvas.save(save_path, "JPEG", quality=85, optimize=False)
        return True
    except Exception as e:
        print(f'    [7-2 FAIL] 예외: {e}'); return False

# --- 메인 실행 ---
try:
    worksheet = doc.worksheet('상품등록목록')
    all_data = worksheet.get_all_records()
    df_final = pd.DataFrame(all_data)
    aa_data = []

    print(f"📦 총 {len(df_final)}개 옵션 처리 시작...\n")

    # [로그 그룹화를 위한 변수]
    prev_prod_name = None
    curr_success_cnt = 0
    curr_fail_cnt = 0
    start_row_num = 2  # 엑셀의 시작 행 번호

    for idx, row in df_final.iterrows():
        curr_prod_name = str(row.get('변환상품명', '이름없음')).strip()
        
        # 1. 상품명이 바뀌었을 때 -> 이전 상품 결과 출력
        if prev_prod_name is not None and curr_prod_name != prev_prod_name:
            print(f"[{start_row_num}] {prev_prod_name[:15]}... ✅ {curr_success_cnt}개 옵션 완성 (실패 {curr_fail_cnt}개)")
            # 카운터 초기화
            curr_success_cnt = 0
            curr_fail_cnt = 0
            start_row_num = idx + 2 # 현재 행 번호로 갱신

        prev_prod_name = curr_prod_name

        # 2. 로직 실행 (상세페이지 제작)
        rep_path = str(row.get('대표이미지경로', '')).strip()
        full_opt_name = str(row.get('전체옵션명', '')).strip()
        
        # 데이터 유효성 검사
        if not rep_path or not os.path.exists(rep_path): 
            aa_data.append([""])
            curr_fail_cnt += 1
            continue

        p_root = os.path.dirname(rep_path)
        det_dir = os.path.join(p_root, "상세페이지")
        copy_dir = os.path.join(det_dir, "상세copy이미지")
        os.makedirs(copy_dir, exist_ok=True)
        
        fname = f"상세_{sanitize_filename(full_opt_name)}.jpg"
        spath = os.path.join(copy_dir, fname)
        
        # 제작 수행
        if make_final_detail_fast(row, det_dir, spath):
            aa_data.append([fname]) 
            curr_success_cnt += 1
        else:
            aa_data.append([""])
            curr_fail_cnt += 1

    # 3. 마지막 상품 결과 출력 (반복문 끝나고 한 번 더)
    if prev_prod_name:
        print(f"[{start_row_num}] {prev_prod_name[:15]}... ✅ {curr_success_cnt}개 옵션 완성 (실패 {curr_fail_cnt}개)")

    # 4. 시트 업데이트
    if aa_data:
        worksheet.update(range_name=f"AA2:AA{len(aa_data)+1}", values=aa_data)
        
    print("\n" + "="*50)
    print(f"🎉 전체 작업 완료!")
    print(f"💸 AI API 호출 횟수: {total_api_calls}회")
    print("="*50)

except Exception as e:
    print(f"❌ 실행 중 오류: {e}")