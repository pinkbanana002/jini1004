# -*- coding: utf-8 -*-
"""
Cell 6-2 의 'list index out of range' 크래시를 고칩니다.
- 원인: 옵션1도 한글옵션도 빈 상품에서 val.split()[0] 이 빈 리스트 접근으로 죽음.
- 이 크래시로 Cell 6-2 가 중단 → 추가이미지 생성 단계에 도달 못 함(추가이미지 누락).
- 수정: val 이 비어도 안전하게 처리(빈 값이면 temp_name 을 대체 사용).
- 원본 로직 변경 최소화(방어 코드만). 실행 전 자동 백업. 여러 번 실행해도 안전.
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage2_cells", "02_cell_6_2.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

OLD = '''                val = str(row[full_idx]) if len(row) > full_idx else ""
                target_base = val.split()[0]'''

NEW = '''                val = str(row[full_idx]) if len(row) > full_idx else ""
                _parts = val.split()
                if _parts:
                    target_base = _parts[0]
                else:
                    # 옵션/한글옵션이 모두 비어 파일명 만들 재료가 없을 때:
                    # 임시파일명(temp_name)에서 확장자를 떼어 대체 사용 (크래시 방지)
                    target_base = os.path.splitext(temp_name)[0] if temp_name else "product"'''

MARKER = "_parts = val.split()"

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] 02_cell_6_2.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    if MARKER in src:
        print("[SKIP] 이미 수정돼 있습니다.")
        return 0

    if OLD not in src:
        print("[ERROR] 수정할 원본 코드 패턴을 찾지 못했습니다. 파일이 예상과 달라 중단합니다.")
        return 1

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"cell_6_2_before_indexfix_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    src = src.replace(OLD, NEW, 1)
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(src)

    print("[OK] 수정 완료. Cell 6-2 가 빈 옵션 상품에서도 안 죽고 추가이미지까지 생성합니다.")
    print("     서버(START.bat) 재시작 후 2단계를 다시 실행하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
