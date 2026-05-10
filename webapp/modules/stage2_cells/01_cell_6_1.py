# [ Cell 6-1 ] (Final_Fix_Duplicates) 이미지 링크 중복 허용 + 순차 복구 모드
# 핵심: 이미지 주소가 같아도(화이트/블랙), 순서대로 하나씩 꺼내서 정확히 매칭합니다.

import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1

print("▶️ [ Cell 6-1 ] 백업 데이터 복구 (중복 링크 순차 매칭)...")

# 1. 🗑️ 과거 수집 메모리 초기화
if 'crawled_buffer' in globals():
    del crawled_buffer
    print("    🧹 과거 수집 메모리 삭제 완료.")

try:
    # 2. 시트 연결
    worksheet_main = doc.worksheet('상품등록목록')
    try:
        worksheet_backup = doc.worksheet('[백업]링크데이터')
    except:
        raise ValueError("❌ '[백업]링크데이터' 시트가 없습니다. Cell 6을 먼저 실행하세요.")

    # 3. 데이터 읽기
    main_data = worksheet_main.get_all_values()
    if len(main_data) < 2: raise ValueError("메인 데이터가 없습니다.")
    main_rows = main_data[1:]
    
    backup_data = worksheet_backup.get_all_values()
    backup_rows = backup_data[1:]
    
    if len(backup_rows) < 1: raise ValueError("❌ 백업할 데이터가 없습니다.")

    # 4. 🔑 백업 데이터 매핑 (리스트 형태)
    # ‼️ [수정된 부분] 딕셔너리가 아닌 '리스트'에 담아서 덮어쓰기 방지
    backup_map = {}
    
    for row in backup_rows:
        link_key = str(row[0]).strip() 
        
        path_data = {
            'I': row[1] if len(row) > 1 else "", # 대표이미지경로
            'N': row[2] if len(row) > 2 else "", # COPY경로
            'Z': row[4] if len(row) > 4 else ""  # 임시파일명 (TEMP_...)
        }
        
        if link_key:
            if link_key not in backup_map:
                backup_map[link_key] = [] # 방을 리스트로 만듦
            backup_map[link_key].append(path_data) # 데이터를 줄 세움

    print(f"    📚 백업 데이터 로드 완료 (중복 링크 포함)")

    # 5. 🎯 메인 시트 순회하며 매칭 (꺼내 쓰기)
    header = main_data[0]
    try: q_idx = header.index('대표이미지링크')
    except: q_idx = 16 
        
    update_i, update_n, update_z, update_r = [], [], [], []
    match_count = 0
    
    for i, row in enumerate(main_rows):
        current_img_link = str(row[q_idx]).strip() if len(row) > q_idx else ""
        
        found_data = None
        
        # ‼️ [수정된 부분] 줄 서있는 데이터에서 맨 앞의 것을 하나 꺼냄 (pop)
        if current_img_link in backup_map and len(backup_map[current_img_link]) > 0:
            found_data = backup_map[current_img_link].pop(0) 
        
        if found_data:
            update_i.append([found_data['I']])
            update_n.append([found_data['N']])
            update_z.append([found_data['Z']])
            match_count += 1
        else:
            # 매칭 안 되면 빈칸 (삭제된 옵션 등)
            update_i.append([""]) 
            update_n.append([""])
            update_z.append([""])

        # 수식 복구 (기존 유지)
        row_num = i + 2
        update_r.append([f'=TRIM(G{row_num} & " " & L{row_num})'])

    # 6. 일괄 업데이트
    end_row = len(main_rows) + 1
    
    print("    ☁️ 데이터 복구 중...", end="")
    worksheet_main.update(range_name=f"I2:I{end_row}", values=update_i)
    worksheet_main.update(range_name=f"N2:N{end_row}", values=update_n)
    worksheet_main.update(range_name=f"Z2:Z{end_row}", values=update_z)
    worksheet_main.update(range_name=f"R2:R{end_row}", values=update_r, value_input_option='USER_ENTERED')
    print(" 완료!")

    print("-" * 40)
    print(f"🎉 [ Cell 6-1 ] 정밀 매칭 복구 완료! ({match_count}개)")
    print("    ✅ 이제 같은 이미지 링크(화이트/블랙)도 정확하게 복구됩니다.")

except Exception as e:
    print(f"❌ 복구 실패: {e}")