# -*- coding: utf-8 -*-
"""
1단계 크롬이 '개인 프로필 직접 사용' 대신
프로젝트 안에 복사해둔 사본 프로필(chrome_auto_profile)을 쓰게 바꿉니다.
- 로그인(쿠키)이 복사돼 있어 로그인 화면이 안 뜨고,
- 개인 크롬을 안 닫아도 프로필 충돌(DevToolsActivePort)이 안 납니다.
- 원본 크롤링 로직은 건드리지 않음. 실행 전 자동 백업.
- 여러 번 실행해도 안전.
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

AUTO_PROFILE_DIR = os.path.join("BASE_DRIVE_PLACEHOLDER", "chrome_auto_profile")
NEW_LINE = '        options.add_argument("--user-data-dir=" + os.path.join(BASE_DRIVE, "chrome_auto_profile"))'
MARKER = "chrome_auto_profile"

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        lines = f.readlines()
    src = "".join(lines)

    if MARKER in src:
        print("[SKIP] 이미 chrome_auto_profile(사본 프로필)을 쓰도록 되어 있습니다.")
        return 0

    # 기존 user-data-dir 줄(Default 프로필 직접사용 또는 chrome_profile_stage1)을 찾아 교체
    target_idx = None
    for i, ln in enumerate(lines):
        if "--user-data-dir" in ln:
            target_idx = i
            break

    if target_idx is None:
        print("[ERROR] 교체할 기존 --user-data-dir 줄을 못 찾았습니다. 중단합니다.")
        return 1

    # profile-directory=... 줄이 바로 다음에 있으면 그 줄도 제거(사본은 Default 하위구조라 불필요)
    remove_next = False
    if target_idx + 1 < len(lines) and "profile-directory" in lines[target_idx + 1]:
        remove_next = True

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_auto_profile_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    lines[target_idx] = NEW_LINE + "\n"
    if remove_next:
        del lines[target_idx + 1]

    with open(TARGET, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("[OK] 완료. 1단계 크롬이 사본 프로필(chrome_auto_profile)을 사용합니다.")
    print("     이제 개인 크롬을 열어둔 채로도 START.bat 실행이 가능합니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
