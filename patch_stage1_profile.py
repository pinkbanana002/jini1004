# -*- coding: utf-8 -*-
"""
1단계 크롬이 로그인 세션을 유지하도록 stage1.py 에 프로필 경로 한 줄을 추가합니다.
- 원본 크롤링 로직은 건드리지 않고, 크롬 실행 옵션에 --user-data-dir 만 추가.
- 실행 전 자동 백업(webapp/_backups/).
- 여러 번 실행해도 안전(이미 패치돼 있으면 그냥 넘어감).
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
# 이 스크립트를 프로젝트 최상위(대량클로드_로켓배송_자동화)에 두고 실행한다고 가정
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

ANCHOR = '        options.add_argument("--no-sandbox")'
INSERT = '        options.add_argument("--user-data-dir=" + os.path.join(BASE_DRIVE, "chrome_profile_stage1"))'

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        print("        이 스크립트를 webapp 폴더가 있는 최상위 폴더에 두고 실행하세요.")
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    if "chrome_profile_stage1" in src or "user-data-dir" in src:
        print("[SKIP] 이미 패치되어 있습니다. 추가 작업 없음.")
        return 0

    count = src.count(ANCHOR)
    if count != 1:
        print(f"[ERROR] 기준 줄(--no-sandbox)을 정확히 1개 찾지 못했습니다 (발견: {count}개).")
        print("        파일이 예상과 달라 안전을 위해 중단합니다. 수동 수정이 필요합니다.")
        return 1

    # 백업
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_profile_patch_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    # 삽입 (기준 줄 바로 다음에 새 줄 추가)
    patched = src.replace(ANCHOR, ANCHOR + "\n" + INSERT, 1)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(patched)

    print("[OK] 패치 완료. 1단계 크롬이 chrome_profile_stage1 프로필을 사용합니다.")
    print("     이제 서버를 재시작(START.bat)하기 전에, 아래 로그인 준비 단계를 먼저 하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
