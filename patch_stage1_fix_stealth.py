# -*- coding: utf-8 -*-
"""
스텔스 옵션 중 사본 프로필과 충돌하는 두 줄(experimental options)만 제거합니다.
- excludeSwitches / useAutomationExtension 제거
  → 'unable to discover open pages' 크래시 해소.
- --disable-blink-features=AutomationControlled 와 CDP 위장(navigator.webdriver)은 유지.
- 실행 전 자동 백업. 여러 번 실행해도 안전.
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

REMOVE_SUBSTRINGS = [
    'excludeSwitches',
    'useAutomationExtension',
]

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        lines = f.readlines()

    to_remove = [i for i, ln in enumerate(lines)
                 if any(s in ln for s in REMOVE_SUBSTRINGS)]

    if not to_remove:
        print("[SKIP] 제거할 experimental 옵션 줄이 없습니다. (이미 정리됨)")
        return 0

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_fixstealth_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    kept = [ln for i, ln in enumerate(lines) if i not in to_remove]
    with open(TARGET, "w", encoding="utf-8") as f:
        f.writelines(kept)

    print(f"[OK] {len(to_remove)}개 줄 제거 완료. 크롬이 정상적으로 뜰 것입니다.")
    print("     서버(START.bat) 재시작 후 1단계 실행하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
