# -*- coding: utf-8 -*-
"""
1단계 크롬이 '빈 프로필(chrome_profile_stage1)' 대신
평소 로그인된 개인 크롬 'Default' 프로필을 그대로 쓰게 바꿉니다.
- 이미 셀록홈즈에 구글 로그인된 프로필이라 로그인 화면이 안 뜹니다.
- 원본 크롤링 로직은 건드리지 않음. 실행 전 자동 백업.
- 여러 번 실행해도 안전.

주의: 크롤링 돌릴 때는 평소 크롬을 완전히 닫아야 합니다(같은 프로필 동시사용 불가).
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

USER_DATA_DIR = r"C:\Users\Jini\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Default"

NEW_LINES = [
    '        options.add_argument(r"--user-data-dir=' + USER_DATA_DIR + '")',
    '        options.add_argument("--profile-directory=' + PROFILE_NAME + '")',
]
MARKER = "profile-directory=" + PROFILE_NAME

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        lines = f.readlines()

    src = "".join(lines)
    if MARKER in src and "User Data" in src:
        print("[SKIP] 이미 Default 프로필을 쓰도록 되어 있습니다.")
        return 0

    # chrome_profile_stage1 을 쓰는 기존 user-data-dir 줄을 찾아 교체
    target_idx = None
    for i, ln in enumerate(lines):
        if "--user-data-dir" in ln and "chrome_profile_stage1" in ln:
            target_idx = i
            break

    if target_idx is None:
        print("[ERROR] 교체할 기존 프로필 줄(chrome_profile_stage1)을 못 찾았습니다.")
        print("        먼저 patch_stage1_profile.py 가 적용됐는지 확인하세요. 중단합니다.")
        return 1

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_default_profile_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    # 기존 한 줄을 두 줄로 교체
    lines[target_idx] = "\n".join(NEW_LINES) + "\n"

    with open(TARGET, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("[OK] 완료. 1단계 크롬이 개인 Default 프로필을 사용합니다.")
    print("     사용법: 크롤링 전 평소 크롬을 완전히 닫고 START.bat 실행.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
