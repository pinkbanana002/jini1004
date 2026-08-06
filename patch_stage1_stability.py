# -*- coding: utf-8 -*-
"""
1단계 크롬이 사용자 프로필과 함께 안정적으로 뜨도록 옵션을 보강합니다.
- DevToolsActivePort / crashed 에러 대응용 표준 안정화 플래그 추가.
- 원본 크롤링 로직은 건드리지 않음. 실행 전 자동 백업(webapp/_backups/).
- 여러 번 실행해도 안전(이미 적용돼 있으면 스킵).
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

# 이 줄(--no-sandbox) 바로 다음에 안정화 플래그들을 추가한다.
ANCHOR = '        options.add_argument("--no-sandbox")'
INSERT_LINES = [
    '        options.add_argument("--remote-debugging-port=0")',
    '        options.add_argument("--no-first-run")',
    '        options.add_argument("--no-default-browser-check")',
    '        options.add_argument("--disable-dev-shm-usage")',
    '        options.add_argument("--disable-features=OptimizationGuideModelDownloading")',
]
MARKER = "--remote-debugging-port=0"

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    if MARKER in src:
        print("[SKIP] 안정화 옵션이 이미 적용돼 있습니다.")
        return 0

    if src.count(ANCHOR) != 1:
        print(f"[ERROR] 기준 줄(--no-sandbox)을 정확히 1개 찾지 못했습니다 (발견: {src.count(ANCHOR)}개). 중단합니다.")
        return 1

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_stability_patch_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    replacement = ANCHOR + "\n" + "\n".join(INSERT_LINES)
    patched = src.replace(ANCHOR, replacement, 1)

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(patched)

    print("[OK] 안정화 옵션 추가 완료. 이제 START.bat 를 다시 실행하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
