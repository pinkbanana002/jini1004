# -*- coding: utf-8 -*-
"""
1단계 크롬에 봇 감지 회피(스텔스) 옵션을 추가합니다.
- 셀록홈즈가 '자동화 브라우저'로 감지해 상품 상세를 로그인으로 튕기는 문제 대응.
- 2단계(쿠팡)에 이미 쓰이는 것과 동일한 기법: navigator.webdriver 위장 등.
- 원본 크롤링 로직은 건드리지 않음. 실행 전 자동 백업. 여러 번 실행해도 안전.
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

OPT_ANCHOR = '        options.add_argument("--no-sandbox")'
OPT_INSERT = [
    '        options.add_argument("--disable-blink-features=AutomationControlled")',
    '        options.add_experimental_option("excludeSwitches", ["enable-automation"])',
    '        options.add_experimental_option("useAutomationExtension", False)',
]

DRIVER_ANCHOR = '        driver = webdriver.Chrome(service=service, options=options)'
CDP_INSERT = [
    '        try:',
    '            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {',
    '                "source": (',
    '                    "Object.defineProperty(navigator, \'webdriver\', {get: () => undefined});"',
    '                    "window.chrome = window.chrome || { runtime: {} };"',
    '                    "Object.defineProperty(navigator, \'plugins\', {get: () => [1,2,3,4,5]});"',
    '                    "Object.defineProperty(navigator, \'languages\', {get: () => [\'ko-KR\',\'ko\',\'en-US\',\'en\']});"',
    '                )',
    '            })',
    '        except Exception as _stealth_e:',
    '            print("    \u26a0\ufe0f \ubd07 \uc704\uc7a5 \uc8fc\uc785 \uc2e4\ud328:", _stealth_e)',
]

MARKER = "AutomationControlled"

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        lines = f.readlines()
    src = "".join(lines)

    if MARKER in src:
        print("[SKIP] 이미 스텔스 옵션이 적용돼 있습니다.")
        return 0

    if src.count(OPT_ANCHOR) != 1:
        print(f"[ERROR] 옵션 기준 줄(--no-sandbox)을 1개 찾지 못함 (발견 {src.count(OPT_ANCHOR)}). 중단.")
        return 1
    if src.count(DRIVER_ANCHOR) != 1:
        print(f"[ERROR] 드라이버 생성 줄을 1개 찾지 못함 (발견 {src.count(DRIVER_ANCHOR)}). 중단.")
        return 1

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_stealth_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    out = []
    for ln in lines:
        out.append(ln)
        if ln.rstrip("\n") == OPT_ANCHOR:
            for x in OPT_INSERT:
                out.append(x + "\n")
        elif ln.rstrip("\n") == DRIVER_ANCHOR:
            for x in CDP_INSERT:
                out.append(x + "\n")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.writelines(out)

    print("[OK] 스텔스 옵션 추가 완료. 서버(START.bat) 재시작 후 1단계 실행하세요.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
