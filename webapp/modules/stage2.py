"""
2단계 (Cell 6-1 ~ Cell 10) 통합 실행 모듈.

원본 노트북의 셀 소스를 `stage2_cells/` 폴더에 그대로 보관하고
`exec()`로 실행합니다. 셀 코드는 한 글자도 수정되지 않았습니다.

웹앱 환경 적응을 위해 다음만 조정:
- print() 출력은 stdout 리다이렉션으로 log_callback에 전달
- 원본 노트북에서 전역으로 공유되던 변수(doc, MY_BRAND_NAME 등)는
  실행 네임스페이스에 사전 주입
- 원본의 input() 블로킹 프롬프트는 UI 환경에 맞게 override
  (login 대기 등은 URL 폴링으로 자동 감지)
"""
import os
import sys
import time
from pathlib import Path


class Stopped(Exception):
    """사용자 중지 요청 시 내부적으로 발생시키는 예외."""


CELLS_DIR = Path(__file__).parent / "stage2_cells"


def _supplier_auto_login(driver, log, should_stop, max_retries=2):
    """쿠팡 서플라이허브 자동 로그인 (Cell 8 '카테고리 추가등록' 구간 보조).

    원본 Cell 8은 1회 시도만 수행하므로, 네트워크 지연이나 DOM 지연으로
    실패할 때 대비해 동일 로직으로 최대 (1 + max_retries)회 재시도한다.

    - 자격증명은 반드시 os.getenv() 에서 읽는다 (하드코딩 금지).
    - 각 시도 후 최대 15초까지 URL 변경으로 성공 여부 확인.
    - 실패 시 5초 대기 후 재시도, 최종 실패 시 log(...)에 에러 push.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    supply_id = (os.getenv("SUPPLY_ID") or "").strip()
    supply_pw = (os.getenv("SUPPLY_PW") or "").strip()
    if not supply_id or not supply_pw:
        log("⚠️ .env의 SUPPLY_ID / SUPPLY_PW 가 비어 있습니다. 수동 로그인이 필요합니다.",
            level="warn")
        return False

    try:
        if "login" not in (driver.current_url or ""):
            return True
    except Exception:
        pass

    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        if should_stop():
            raise Stopped()
        try:
            log(f"🔑 서플라이허브 자동 로그인 시도 {attempt}/{attempts}...", level="info")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            time.sleep(1)

            # ID/PW 필드: type(text/email/password) 또는 name/id/placeholder 속성 기반 탐지
            inputs = driver.find_elements(By.TAG_NAME, "input")
            id_box = None
            pw_box = None
            for el in inputs:
                try:
                    t = (el.get_attribute("type") or "").lower()
                    name = (el.get_attribute("name") or "").lower()
                    eid = (el.get_attribute("id") or "").lower()
                    ph = (el.get_attribute("placeholder") or "").lower()
                    haystack = f"{name} {eid} {ph}"
                    if t == "password" and pw_box is None:
                        pw_box = el
                    elif t in ("text", "email") and id_box is None:
                        if any(k in haystack for k in ("id", "user", "email", "아이디")) or t == "email":
                            id_box = el
                except Exception:
                    continue
            if id_box is None or pw_box is None:
                # 폴백: 원본 Cell 8 방식 — 앞의 두 text-like input
                text_inputs = [i for i in inputs
                               if (i.get_attribute("type") or "").lower()
                               in ("text", "email", "password")]
                if len(text_inputs) >= 2:
                    id_box, pw_box = text_inputs[0], text_inputs[1]
                else:
                    raise RuntimeError("ID/PW 입력 필드를 찾지 못했습니다.")

            for box, val in [(id_box, supply_id), (pw_box, supply_pw)]:
                box.click()
                box.send_keys(Keys.CONTROL + "a")
                box.send_keys(Keys.BACKSPACE)
                time.sleep(0.3)
                box.send_keys(val)

            try:
                btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(., '로그인') or contains(., 'Login')]",
                )
                driver.execute_script("arguments[0].click();", btn)
            except Exception:
                pw_box.send_keys(Keys.ENTER)

            # 최대 15초 대기하며 URL 변경(login 탈출) 감지
            deadline = time.time() + 15
            while time.time() < deadline:
                if should_stop():
                    raise Stopped()
                try:
                    if "login" not in (driver.current_url or ""):
                        log("🎉 서플라이허브 자동 로그인 성공!", level="success")
                        return True
                except Exception:
                    pass
                time.sleep(1)

            if attempt < attempts:
                log(f"⚠️ 로그인 확인 실패 (시도 {attempt}/{attempts}). 5초 후 재시도...",
                    level="warn")
                time.sleep(5)
        except Stopped:
            raise
        except Exception as e:
            log(f"⚠️ 로그인 시도 {attempt} 중 오류: {e}", level="warn")
            if attempt < attempts:
                time.sleep(5)

    log("❌ 자동 로그인 최대 재시도 초과 — 브라우저에서 수동 로그인을 완료해주세요.",
        level="error")
    return False

CELL_SEQUENCE = [
    ("01_cell_6_1.py",  "Cell 6-1: 백업 데이터 복구"),
    ("02_cell_6_2.py",  "Cell 6-2: 파일명 변경 + 400px 확대"),
    ("03_cell_7.py",    "Cell 7: 폴더명 변경 및 파일 정리"),
    ("04_cell_7_1.py",  "Cell 7-1: 경로 최신화 + 품질 라벨"),
    ("05_cell_7_2.py",  "Cell 7-2: 상세페이지 제작"),
    ("06_cell_8.py",    "Cell 8: 서플라이허브 다운로드"),
    ("07_cell_9.py",    "Cell 9: 견적서 작성"),
    ("08_cell_9_1.py",  "Cell 9-1: 쿠팡 상품 등록"),
    ("09_cell_10.py",   "Cell 10: 최종 이관 및 시트 정리"),
]


def _make_log_stream(log_callback):
    class LogStream:
        def __init__(self):
            self.buf = ""
        def write(self, s):
            self.buf += s
            while "\n" in self.buf:
                line, _, self.buf = self.buf.partition("\n")
                level = "info"
                if any(t in line for t in ["❌", "오류", "에러", "실패", "Error"]):
                    level = "error"
                elif any(t in line for t in ["⚠️", "경고"]):
                    level = "warn"
                elif any(t in line for t in ["✅", "🎉"]):
                    level = "success"
                log_callback(line, level=level)
        def flush(self):
            if self.buf:
                log_callback(self.buf, level="info")
                self.buf = ""
    return LogStream()


def run_stage2(config: dict, log, progress, should_stop, set_counter=None,
               gate_signal=None, gate_wait=None):
    """Cell 6-1 ~ Cell 10을 순차 실행.

    set_counter(current, limit): Cell 9-1 진행 중 등록 개수 UI 표시용 콜백(optional).
    gate_signal(name): 특정 체크포인트(예: 견적서 완료) 도달 시 UI에 통지.
    gate_wait(name): UI가 계속 진행 신호를 줄 때까지 블로킹 대기.
    """
    original_stdout = sys.stdout
    original_cwd = os.getcwd()
    sys.stdout = _make_log_stream(log)

    project_root = config["PROJECT_ROOT"]
    os.chdir(project_root)

    ns = {"__name__": "__stage2_exec__", "__builtins__": __builtins__}

    try:
        total_steps = len(CELL_SEQUENCE)

        # ------------------------------------------------------------
        # [ Cell 0 equivalent ] 환경 설정 (config → local)
        # ------------------------------------------------------------
        progress(0, total_steps, "환경 설정 / 구글시트 연결 중...")

        GOOGLE_JSON_FILE = config["GOOGLE_JSON_FILE"]
        GOOGLE_SHEET_URL = config["GOOGLE_SHEET_URL"]
        TARGET_SHEET_NAME = config.get("TARGET_SHEET_NAME") or "상품등록목록"
        GEMINI_API_KEY = config["GEMINI_API_KEY"]
        SUPPLY_ID = config.get("SUPPLY_ID", "")
        SUPPLY_PW = config.get("SUPPLY_PW", "")
        MY_BRAND_NAME = config.get("MY_BRAND_NAME") or "브랜드"
        MY_COMPANY_NAME = config.get("MY_COMPANY_NAME") or ""
        MY_PHONE_NUMBER = config.get("MY_PHONE_NUMBER") or ""

        BASE_DRIVE = project_root
        PATH_TEMPLATES = os.path.join(BASE_DRIVE, "templates")
        PATH_FONTS = os.path.join(BASE_DRIVE, "fonts")
        FONT_BOLD = "강원교육모두 Bold.ttf"
        FONT_REGULAR = "강원교육모두 Light.ttf"
        MY_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
        PATH_PROFILE = os.path.join(BASE_DRIVE, "chrome_profile")
        PATH_COMPLETED = os.path.join(BASE_DRIVE, "완료된_상품")

        for p in [PATH_TEMPLATES, PATH_FONTS, PATH_PROFILE, PATH_COMPLETED]:
            if not os.path.exists(p):
                os.makedirs(p)

        # Gemini model 초기화 (Cell 7-2에서 사용)
        model = None
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                except Exception:
                    model = genai.GenerativeModel('gemini-flash-latest')
            except Exception:
                model = None

        # 구글 시트 연결 (Cell 2 상응)
        import gspread
        if not os.path.exists(GOOGLE_JSON_FILE):
            raise FileNotFoundError(f"credentials.json 파일이 없습니다: {GOOGLE_JSON_FILE}")
        gc_client = gspread.service_account(filename=GOOGLE_JSON_FILE)
        doc = gc_client.open_by_url(GOOGLE_SHEET_URL)
        print(f"✅ 구글시트 연결 성공: {doc.title}")

        # ------------------------------------------------------------
        # 실행 네임스페이스 주입 (원본 노트북의 globals 역할)
        # ------------------------------------------------------------
        ns.update({
            "doc": doc,
            "gc": gc_client,
            "SHEET_URL": GOOGLE_SHEET_URL,
            "GOOGLE_SHEET_URL": GOOGLE_SHEET_URL,
            "TARGET_SHEET_NAME": TARGET_SHEET_NAME,
            "GEMINI_API_KEY": GEMINI_API_KEY,
            "SUPPLY_ID": SUPPLY_ID,
            "SUPPLY_PW": SUPPLY_PW,
            "MY_BRAND_NAME": MY_BRAND_NAME,
            "MY_COMPANY_NAME": MY_COMPANY_NAME,
            "MY_PHONE_NUMBER": MY_PHONE_NUMBER,
            "BASE_DRIVE": BASE_DRIVE,
            "PATH_TEMPLATES": PATH_TEMPLATES,
            "PATH_FONTS": PATH_FONTS,
            "FONT_BOLD": FONT_BOLD,
            "FONT_REGULAR": FONT_REGULAR,
            "MY_DOWNLOAD_DIR": MY_DOWNLOAD_DIR,
            "PATH_PROFILE": PATH_PROFILE,
            "PATH_COMPLETED": PATH_COMPLETED,
            "model": model,
            # Cell 9-1에서 이동된 폴더 개수 카운터를 외부로 노출하기 위한 훅
            "_stage2_set_counter": set_counter,
            "_stage2_should_stop": should_stop,
        })

        # ------------------------------------------------------------
        # input() override
        # ------------------------------------------------------------
        def _ui_input(prompt=""):
            s = str(prompt)
            if s:
                print(s)
            # 수동 개입 필요한 프롬프트는 드라이버 상태 폴링
            if any(k in s for k in ["로그인이 완료", "해결하셨다면", "로그인"]):
                drv = ns.get("driver")
                if drv is None:
                    return ""
                # 로그인 관련 프롬프트(Oops 새로고침 요청은 제외)면 먼저 자동 로그인 재시도
                if ("로그인" in s) and ("해결하셨다면" not in s):
                    try:
                        if _supplier_auto_login(drv, log, should_stop):
                            return ""
                    except Stopped:
                        raise
                    except Exception as _e:
                        log(f"⚠️ 자동 로그인 헬퍼 예외: {_e}", level="warn")
                print("⏳ [자동 대기] 브라우저에서 수동 조치 후 자동 감지합니다 (최대 1분)...")
                deadline = time.time() + 60
                while time.time() < deadline:
                    if should_stop():
                        raise Stopped()
                    try:
                        from selenium.webdriver.common.by import By
                        url = drv.current_url
                        body_text = drv.find_element(By.TAG_NAME, "body").text
                        if "login" not in url and "Oops" not in body_text and len(body_text) >= 50:
                            print("✅ 브라우저 정상 상태 감지 → 자동 진행")
                            return ""
                    except Exception:
                        pass
                    time.sleep(3)
                print("⏰ 1분 경과 — 자동 진행합니다.")
                return ""
            # Cell 9/10 말미의 단순 확인 프롬프트: 즉시 Enter
            print("ℹ️ [자동진행] UI에서 자동으로 다음 단계로 넘어갑니다.")
            return ""

        ns["input"] = _ui_input

        # ------------------------------------------------------------
        # 셀 순차 실행
        # ------------------------------------------------------------
        import threading

        for idx, (filename, label) in enumerate(CELL_SEQUENCE, start=1):
            if should_stop():
                raise Stopped()
            progress(idx, total_steps, label)
            print("\n" + "=" * 60)
            print(f"[{idx}/{total_steps}] {label}")
            print("=" * 60)

            # ---- 쿠팡 크롬 실행 직전 훅 (Cell 8) ----
            # 원본 Cell 8의 launch_robot_chrome() 은 --user-data-dir={PATH_PROFILE} 을
            # 이미 쓰고 있지만, 이전 실행이 force-kill 로 남긴 프로필 락 파일 / 잔존
            # chrome.exe 프로세스 때문에 Coupang "Oops" 가 뜨는 문제가 있어
            # 해당 셀 실행 전에 환경을 초기화한다.
            if filename.startswith("06_cell_8"):
                import subprocess as _sp
                import glob as _glob
                print("🧹 쿠팡 크롬 실행 준비: 기존 봇 크롬만 정확히 종료 + 프로필 락 정리")

                # [SAFE-KILL] PATH_PROFILE 을 user-data-dir 로 쓰는 chrome.exe 만 PID 잡아 종료.
                # 사용자가 평소 쓰는 일반 크롬 창은 절대 건드리지 않는다.
                # (원래 코드의 'taskkill /F /IM chrome.exe' 는 모든 크롬을 죽여서
                #  사용자 화면의 모든 크롬 창이 사라지는 사고가 발생했다.)
                _profile_norm = os.path.normpath(PATH_PROFILE).replace("\\", "\\\\")
                _ps = (
                    'powershell -NoProfile -Command "'
                    '$ErrorActionPreference=\'SilentlyContinue\';'
                    '$p=Get-CimInstance Win32_Process -Filter \\"Name=\'chrome.exe\'\\" |'
                    ' Where-Object { $_.CommandLine -like \'*--user-data-dir=*'
                    + _profile_norm + '*\' -or '
                    '$_.CommandLine -like \'*--remote-debugging-port=9222*\' };'
                    'if ($p) { $p | ForEach-Object {'
                    ' Stop-Process -Id $_.ProcessId -Force;'
                    ' Write-Host (\'    🛑 종료된 봇 크롬 PID=\' + $_.ProcessId)'
                    ' } } else { Write-Host \'    ℹ️ 종료할 봇 크롬 없음 (안전)\' }"'
                )
                try:
                    _r = _sp.run(
                        _ps, shell=True, capture_output=True,
                        text=True, encoding='utf-8', errors='replace', timeout=15,
                    )
                    if _r.stdout:
                        for _ln in _r.stdout.splitlines():
                            if _ln.strip():
                                print(_ln)
                    time.sleep(2)
                except Exception as _e:
                    print(f"    ⚠️ 크롬 종료 단계 건너뜀: {_e}")

                # 프로필 락 파일 제거 (이 부분은 안전, 원본 그대로)
                try:
                    for pat in ("Singleton*", "lockfile", "Lock*", "parent.lock"):
                        for p in _glob.glob(os.path.join(PATH_PROFILE, pat)):
                            try:
                                os.remove(p)
                            except Exception:
                                pass
                except Exception:
                    pass
                print(f"    ✅ user-data-dir 로 사용할 PATH_PROFILE: {PATH_PROFILE}")
            # Cell 9-1 진행 중 등록 개수(success_count) 폴링 → UI 카운터 반영
            poller_stop = threading.Event()
            poller_thread = None
            if "9_1" in filename and set_counter is not None:
                def _poll():
                    while not poller_stop.is_set():
                        try:
                            cur = ns.get("success_count", 0) or 0
                            lim = ns.get("DAILY_LIMIT", 50) or 50
                            set_counter(int(cur), int(lim))
                        except Exception:
                            pass
                        time.sleep(1)
                poller_thread = threading.Thread(target=_poll, daemon=True)
                poller_thread.start()

            try:
                cell_path = CELLS_DIR / filename
                src = cell_path.read_text(encoding="utf-8")
                code = compile(src, str(cell_path), "exec")
                exec(code, ns)
            finally:
                if poller_thread is not None:
                    poller_stop.set()
                    poller_thread.join(timeout=2)
                    if set_counter is not None:
                        try:
                            cur = ns.get("success_count", 0) or 0
                            lim = ns.get("DAILY_LIMIT", 50) or 50
                            set_counter(int(cur), int(lim))
                        except Exception:
                            pass

            if should_stop():
                raise Stopped()

            # ---- 견적서 확인 게이트: Cell 9(07_cell_9.py) 완료 직후 UI 승인 대기 ----
            if filename.startswith("07_cell_9") and gate_signal and gate_wait:
                print("\n⏸️ [견적서 확인 게이트] 엑셀 견적서 검수를 위해 대기합니다...")
                gate_signal("quote_ready")
                gate_wait("quote_ready")
                print("▶️ 사용자 승인 감지 → 쿠팡 상품 등록(Cell 9-1)으로 진행합니다.")

        print("\n🎉 [2단계 전체 완료]")

    finally:
        sys.stdout = original_stdout
        # Selenium driver 종료
        drv = ns.get("driver")
        if drv is not None:
            try:
                drv.quit()
            except Exception:
                pass
        os.chdir(original_cwd)
