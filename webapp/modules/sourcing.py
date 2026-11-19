# -*- coding: utf-8 -*-
"""
sourcing.py - 쿠팡 키워드 경쟁 분석 (소싱 1단계)

키워드를 쿠팡에서 검색해서 '블루오션인지' 판정한다.
  - 로켓배송 상품 수 (적을수록 블루오션)
  - 1등 상품 리뷰 수 (적을수록 블루오션)
  - 가격대 (내 원가로 들어갈 틈이 있는지)

쿠팡은 페이지 구조가 자주 바뀌므로 CSS 클래스에 의존하지 않고
카드의 '텍스트'와 'HTML'에서 패턴(로켓배송, (리뷰수), 숫자원)을 찾는다.

단독 실행:
    python modules/sourcing.py 당구장갑 수면양말
"""
import os
import re
import sys
import time

# ============================================================
# 기준값 (.env 로 조절 가능)
# ============================================================
def _cfg_int(name, default):
    try:
        return int(float(os.getenv(name, str(default))))
    except Exception:
        return default


def get_thresholds():
    return {
        # 블루오션 조건 (둘 다 만족해야 🟢)
        "rocket_blue": _cfg_int("SOURCING_ROCKET_BLUE", 10),   # 로켓 상품 수 미만
        "review_blue": _cfg_int("SOURCING_REVIEW_BLUE", 300),  # 1등 리뷰 수 미만
        # 레드오션 조건 (하나라도 넘으면 🔴)
        "rocket_red": _cfg_int("SOURCING_ROCKET_RED", 30),
        "review_red": _cfg_int("SOURCING_REVIEW_RED", 1000),
    }


# ============================================================
# 순수 파싱 함수 (브라우저 없이도 테스트 가능)
# ============================================================
ROCKET_WORDS = ("로켓배송", "로켓프레시", "로켓직구", "로켓설치", "판매자로켓")
AD_WORDS = ("광고", "AD")


def parse_price(text):
    """'12,900원' 같은 표기에서 첫 번째 가격을 숫자로. 없으면 0."""
    if not text:
        return 0
    m = re.search(r"([\d][\d,]*)\s*원", str(text))
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except Exception:
        return 0


def parse_reviews(text):
    """'(1,234)' 형태의 리뷰 수. 없으면 0.
    가격의 천단위 쉼표와 헷갈리지 않도록 괄호 안 숫자만 본다."""
    if not text:
        return 0
    best = 0
    for m in re.finditer(r"\(\s*([\d][\d,]*)\s*\)", str(text)):
        try:
            v = int(m.group(1).replace(",", ""))
        except Exception:
            continue
        if v > best:
            best = v
    return best


def is_rocket(card):
    """카드가 로켓배송 상품인지. 텍스트와 HTML(img alt) 둘 다 본다."""
    blob = (card.get("text") or "") + " " + (card.get("html") or "")
    return any(w in blob for w in ROCKET_WORDS)


def is_ad(card):
    """광고 상품인지."""
    text = card.get("text") or ""
    html = card.get("html") or ""
    if "광고" in text:
        return True
    # class="...ad-badge..." / data-ad / adBadge 등
    if re.search(r"ad[-_]?badge|isAdProduct|data-ad-", html, re.I):
        return True
    return False


def analyze_cards(cards, thresholds=None):
    """카드 목록을 받아 경쟁 지표를 계산한다.
    cards: [{'text': 카드 전체 텍스트, 'html': 카드 outerHTML}, ...]
    """
    th = thresholds or get_thresholds()

    total = len(cards)
    rocket_cards = []
    organic = []          # 광고 제외
    prices = []

    for c in cards:
        ad = is_ad(c)
        rk = is_rocket(c)
        p = parse_price(c.get("text"))
        r = parse_reviews(c.get("text"))
        item = {"ad": ad, "rocket": rk, "price": p, "reviews": r,
                "name": (c.get("name") or "").strip()}
        if rk:
            rocket_cards.append(item)
        if not ad:
            organic.append(item)
        if p > 0:
            prices.append(p)

    rocket_count = len(rocket_cards)

    # 1등 = 광고 아닌 첫 번째 상품
    top1_reviews = organic[0]["reviews"] if organic else 0
    top1_name = organic[0]["name"] if organic else ""

    # 리뷰 많은 상품이 몇 개나 되는지 (시장이 굳었는지 보는 보조 지표)
    heavy = sum(1 for o in organic if o["reviews"] >= th["review_red"])

    prices_sorted = sorted(prices)
    price_min = prices_sorted[0] if prices_sorted else 0
    price_max = prices_sorted[-1] if prices_sorted else 0
    price_mid = prices_sorted[len(prices_sorted) // 2] if prices_sorted else 0

    verdict, reason = judge(rocket_count, top1_reviews, th)

    return {
        "total_cards": total,
        "rocket_count": rocket_count,
        "organic_count": len(organic),
        "top1_reviews": top1_reviews,
        "top1_name": top1_name,
        "heavy_review_count": heavy,
        "price_min": price_min,
        "price_mid": price_mid,
        "price_max": price_max,
        "verdict": verdict,
        "reason": reason,
    }


def judge(rocket_count, top1_reviews, thresholds=None):
    """블루/보통/레드 판정."""
    th = thresholds or get_thresholds()
    if rocket_count > th["rocket_red"] or top1_reviews > th["review_red"]:
        return "RED", f"로켓 {rocket_count}개 / 1등리뷰 {top1_reviews} - 경쟁 치열"
    if rocket_count < th["rocket_blue"] and top1_reviews < th["review_blue"]:
        return "BLUE", f"로켓 {rocket_count}개 / 1등리뷰 {top1_reviews} - 해볼 만함"
    return "YELLOW", f"로켓 {rocket_count}개 / 1등리뷰 {top1_reviews} - 신중히"


VERDICT_MARK = {"BLUE": "[BLUE] 블루오션", "YELLOW": "[MID ] 보통", "RED": "[RED ] 레드오션"}


# ============================================================
# 브라우저로 쿠팡 검색
# ============================================================
def collect_cards(driver, keyword, log=print, debug=False, limit=40):
    """쿠팡에서 키워드를 검색하고 상품 카드들의 text/html 을 수집한다."""
    from urllib.parse import quote
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    url = ("https://www.coupang.com/np/search?q=" + quote(str(keyword))
           + "&channel=user&sorter=scoreDesc&listSize=36")
    driver.get(url)

    # 상품 목록이 뜰 때까지 대기 (여러 셀렉터 중 하나라도)
    selectors = [
        "ul#productList > li",
        "li.search-product",
        "li[class*='search-product']",
        "[class*='ProductUnit_productUnit']",
        "ul[class*='productList'] > li",
    ]
    found_sel = None
    deadline = time.time() + 15
    while time.time() < deadline:
        for sel in selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                els = []
            if len(els) >= 3:
                found_sel = sel
                break
        if found_sel:
            break
        time.sleep(0.6)

    if not found_sel:
        log(f"    [진단] 상품 목록을 못 찾음 - 페이지 제목: {getattr(driver, 'title', '')}")
        try:
            body = driver.find_element(By.TAG_NAME, "body").text[:300]
            log(f"    [진단] 본문 첫 300자: {body}")
        except Exception:
            pass
        return []

    time.sleep(1.0)  # 레이지 로딩 안정화
    els = driver.find_elements(By.CSS_SELECTOR, found_sel)[:limit]
    if debug:
        log(f"    [진단] 사용한 셀렉터: {found_sel} / 카드 {len(els)}개")

    cards = []
    for el in els:
        try:
            t = el.text or ""
        except Exception:
            t = ""
        try:
            h = el.get_attribute("outerHTML") or ""
        except Exception:
            h = ""
        if not t.strip():
            continue
        # 상품명 = 카드 텍스트의 첫 줄 중 가장 긴 줄(가격/배지 줄 제외)
        name = ""
        for line in [x.strip() for x in t.split("\n") if x.strip()]:
            if "원" in line or line.startswith("(") or len(line) < 4:
                continue
            name = line
            break
        cards.append({"text": t, "html": h[:4000], "name": name})

    if debug and cards:
        log("    [진단] 첫 카드 텍스트:")
        for line in cards[0]["text"].split("\n")[:8]:
            log(f"        | {line}")
    return cards


def analyze_keyword(driver, keyword, log=print, debug=False):
    """키워드 하나를 분석해서 결과 dict 반환."""
    cards = collect_cards(driver, keyword, log=log, debug=debug)
    if not cards:
        return {"keyword": keyword, "error": "검색 결과를 읽지 못함",
                "verdict": "ERROR", "reason": "페이지 구조 변경 또는 차단 의심"}
    res = analyze_cards(cards)
    res["keyword"] = keyword
    return res


def format_result(r):
    """사람이 읽는 한 줄 + 상세."""
    if r.get("error"):
        return f"  {r['keyword']}: [ERR ] {r['error']}"
    mark = VERDICT_MARK.get(r["verdict"], r["verdict"])
    return (
        f"  {r['keyword']}: {mark}\n"
        f"      로켓 {r['rocket_count']}개 / 1등리뷰 {r['top1_reviews']} / "
        f"가격 {r['price_min']:,}~{r['price_max']:,}원 (중간 {r['price_mid']:,})\n"
        f"      1등: {r['top1_name'][:40]}"
    )


# ============================================================
# 단독 실행
# ============================================================
def _attach_chrome(log=print):
    """stage1 과 같은 방식으로 개인 크롬에 붙는다(없으면 띄운다)."""
    import subprocess as sp
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    PORT = 9223
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # webapp
    root = os.path.dirname(base)                                        # 프로젝트 루트
    profile = os.path.join(root, "chrome_auto_profile")

    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORT}")
    try:
        drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                               options=options)
        log("크롬에 연결했습니다 (이미 떠 있는 창 재사용).")
        return drv
    except Exception:
        pass

    log("크롬을 새로 띄웁니다...")
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.getenv("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    exe = next((p for p in paths if os.path.exists(p)), None)
    if not exe:
        raise RuntimeError("크롬 실행파일을 찾을 수 없습니다.")
    sp.Popen([exe, f"--remote-debugging-port={PORT}",
              f"--user-data-dir={profile}", "--lang=ko-KR",
              "--no-first-run", "--no-default-browser-check", "--start-maximized",
              "https://www.coupang.com/"])
    time.sleep(6)
    drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                           options=options)
    log("크롬에 연결했습니다.")
    return drv


def _load_env(log=print):
    """webapp/.env 를 읽어 기준값 설정을 적용한다(단독 실행용)."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    here = os.path.dirname(os.path.abspath(__file__))        # modules
    for p in (os.path.join(os.path.dirname(here), ".env"),   # webapp/.env
              os.path.join(os.path.dirname(os.path.dirname(here)), ".env")):
        if os.path.exists(p):
            try:
                load_dotenv(p, override=False)
            except Exception:
                pass
            return


def main():
    _load_env()
    keywords = [a for a in sys.argv[1:] if a.strip()]
    if not keywords:
        raw = input("분석할 키워드를 입력하세요 (여러 개면 띄어쓰기): ").strip()
        keywords = [k for k in raw.split() if k]
    if not keywords:
        print("키워드가 없습니다.")
        return

    th = get_thresholds()
    print("=" * 60)
    print("쿠팡 키워드 경쟁 분석")
    print(f"  블루오션 기준: 로켓 {th['rocket_blue']}개 미만 + 1등리뷰 {th['review_blue']} 미만")
    print(f"  레드오션 기준: 로켓 {th['rocket_red']}개 초과 또는 1등리뷰 {th['review_red']} 초과")
    print("=" * 60)

    driver = _attach_chrome()
    results = []
    try:
        for i, kw in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] '{kw}' 분석 중...")
            r = analyze_keyword(driver, kw, log=print, debug=True)
            results.append(r)
            print(format_result(r))
            time.sleep(2)
    finally:
        pass  # 크롬은 띄워둔 채로 (다음 실행 때 재사용)

    print("\n" + "=" * 60)
    print("요약 (블루오션 순)")
    print("=" * 60)
    order = {"BLUE": 0, "YELLOW": 1, "RED": 2, "ERROR": 3}
    for r in sorted(results, key=lambda x: (order.get(x.get("verdict"), 9),
                                            x.get("rocket_count", 999))):
        print(format_result(r))
    print()


if __name__ == "__main__":
    main()
