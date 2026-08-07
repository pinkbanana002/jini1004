# -*- coding: utf-8 -*-
"""
1단계 크롬을 '직접 생성' 방식에서 '디버그 포트로 띄우고 attach' 방식으로 전환합니다.
- 2단계 쿠팡(cell_8)과 동일한 검증된 방식. 개인 크롬 세션을 그대로 써서 봇 감지를 근본 우회.
- 셀록홈즈가 로그인 페이지로 튕기면 사용자가 로그인할 때까지 대기(최대 3분) 후 자동 진행.
- 원본 크롤링 로직(Cell 4-1 이후)은 건드리지 않음. 실행 전 자동 백업. 여러 번 실행해도 안전.
"""
import os, sys, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "webapp", "modules", "stage1.py")
BACKUP_DIR = os.path.join(HERE, "webapp", "_backups")

# 교체 대상: options 생성 ~ '✅ 접속 성공!' 출력까지 (크롬 생성/스텔스/get 블록 전체)
OLD_START = '        options = webdriver.ChromeOptions()'
OLD_END = '        print(f"✅ 접속 성공! 현재 페이지: {driver.title}")'

NEW_BLOCK = r'''        # ==========================================================
        # [ATTACH 방식] 개인 크롬을 디버그 포트로 띄우고 붙는다 (봇 감지 우회)
        #   2단계 쿠팡(cell_8)과 동일 방식. 로그인 세션을 그대로 재사용.
        # ==========================================================
        import subprocess as _sp
        _DEBUG_PORT = 9223
        _PROFILE_DIR = os.path.join(BASE_DRIVE, "chrome_auto_profile")

        # 이 프로필+포트로 떠 있던 기존 크롬만 정리
        try:
            _cmd = ('wmic process where "name=\'chrome.exe\' and commandline like '
                    '\'%%remote-debugging-port=' + str(_DEBUG_PORT) + '%%\'" get processid')
            _out = _sp.check_output(_cmd, shell=True, encoding='utf-8', errors='replace')
            for _p in _out.split():
                if _p.isdigit():
                    os.system('taskkill /F /PID ' + _p + ' > nul 2>&1')
            time.sleep(1)
        except Exception:
            pass

        _chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.getenv('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe'),
        ]
        _chrome_exe = next((p for p in _chrome_paths if os.path.exists(p)), None)
        if not _chrome_exe:
            raise RuntimeError("크롬 실행파일을 찾을 수 없습니다.")

        _target_url = "https://sellochomes.co.kr/sourcinglife/"
        _launch = [
            _chrome_exe,
            "--remote-debugging-port=" + str(_DEBUG_PORT),
            "--user-data-dir=" + _PROFILE_DIR,
            "--lang=ko-KR",
            "--disable-features=Translate",
            "--no-first-run",
            "--no-default-browser-check",
            "--start-maximized",
            _target_url,
        ]
        _sp.Popen(_launch)
        print("▶️ [ Cell 3 ] 크롬 실행(attach 모드) 완료. 연결 대기...")
        time.sleep(5)

        # 디버그 포트로 attach
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:" + str(_DEBUG_PORT))
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)
        print("✅ 브라우저 연결 성공!")

        # 다운로드 경로 지정 (attach 모드에서는 prefs 대신 CDP 사용)
        try:
            driver.execute_cdp_cmd("Page.setDownloadBehavior",
                                   {"behavior": "allow", "downloadPath": MY_DOWNLOAD_DIR})
        except Exception:
            pass

        # 로그인 페이지로 튕기면 사용자 로그인 대기 (최대 3분, 자동 감지)
        try:
            _cur = driver.current_url
        except Exception:
            _cur = ""
        if "/auth/login" in _cur or "로그인" in (driver.title or ""):
            print("=" * 58)
            print("⛔ 셀록홈즈 로그인이 필요합니다.")
            print("👉 방금 열린 크롬 창에서 '구글로 시작하기' 등으로 로그인해주세요.")
            print("   로그인되면 자동으로 감지하여 진행합니다 (최대 3분 대기)...")
            print("=" * 58)
            _deadline = time.time() + 180
            while time.time() < _deadline:
                if should_stop():
                    raise Stopped()
                time.sleep(3)
                try:
                    _u = driver.current_url
                    _t = driver.title or ""
                except Exception:
                    continue
                # 로그인 페이지를 벗어나면 통과
                if "/auth/login" not in _u and "로그인" not in _t:
                    print("✅ 로그인 감지 → 자동 진행합니다.")
                    break
            else:
                print("⏰ 3분 경과 — 그대로 진행을 시도합니다.")

        # 상품 크롤링을 위해 소싱라이프 메인 확보
        try:
            if "sourcinglife" not in (driver.current_url or ""):
                driver.get(_target_url)
                time.sleep(2)
        except Exception:
            pass
        print(f"✅ 접속 성공! 현재 페이지: {driver.title}")'''

def main():
    if not os.path.exists(TARGET):
        print("[ERROR] stage1.py 를 찾을 수 없습니다:", TARGET)
        return 1

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    if "debuggerAddress" in src and "_DEBUG_PORT = 9223" in src:
        print("[SKIP] 이미 attach 방식으로 되어 있습니다.")
        return 0

    i = src.find(OLD_START)
    j = src.find(OLD_END)
    if i == -1 or j == -1 or j < i:
        print("[ERROR] 교체 대상 블록(크롬 생성~접속 성공)을 찾지 못했습니다. 중단합니다.")
        return 1
    j_end = j + len(OLD_END)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stage1_before_attach_{stamp}.py")
    shutil.copy2(TARGET, backup_path)
    print("[OK] 백업 생성:", backup_path)

    new_src = src[:i] + NEW_BLOCK + src[j_end:]
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(new_src)

    print("[OK] attach 방식 전환 완료.")
    print("     서버(START.bat) 재시작 후 1단계 실행 → 열린 크롬에서 한 번만 로그인하면 됩니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
