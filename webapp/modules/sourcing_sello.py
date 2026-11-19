# -*- coding: utf-8 -*-
"""
sourcing_sello.py - 소싱라이프(셀록홈즈) x 1688 검색 수집 + 점수화

1688 을 직접 긁지 않고 소싱라이프를 거친다.
  - 한글 검색 / 한글 상품명
  - 원화 단가 + 위안화 단가
  - 월 판매량 / 평점 / 재구매율
  - 차단 위험이 낮고 이미 로그인돼 있음

실행:
    python modules/sourcing_sello.py 털실 당구장갑
"""
import os
import re
import sys
import time
from datetime import datetime

SELLO_HOME = "https://sellochomes.co.kr/sourcinglife/"


# ============================================================
# 기준값 (.env 로 조절)
#   기본값은 2026-11-19 소싱라이프 x 1688 '털실' 검색 화면의
#   실제 분포(월 306~8736개 / 재구매 10~30% / 평점 4.8~5.0)에서 잡았다.
# ============================================================
def _cfg(name, default, cast=float):
    try:
        return cast(os.getenv(name, str(default)))
    except Exception:
        return default


def get_settings():
    return {
        "min_monthly": _cfg("SELLO_MIN_MONTHLY", 1000, int),   # 월 판매량
        "min_repurchase": _cfg("SELLO_MIN_REPURCHASE", 20, float),  # 재구매 %
        "min_rating": _cfg("SELLO_MIN_RATING", 4.5, float),    # 평점
        "max_price_krw": _cfg("SELLO_MAX_PRICE", 0, int),      # 0 이면 제한 없음
        "score_candidate": _cfg("SELLO_SCORE_CANDIDATE", 5, int),
        "score_review": _cfg("SELLO_SCORE_REVIEW", 3, int),
    }


# ============================================================
# 순수 파싱 (브라우저 없이 테스트 가능)
# ============================================================
def parse_krw(text):
    """'1,085원' -> 1085. 가장 먼저 나오는 원화 금액."""
    m = re.search(r"([\d][\d,]*)\s*원", text or "")
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except Exception:
        return 0


def parse_cny(text):
    """'3.50元' -> 3.5.  '4.00元 3.80元' 처럼 할인 전/후가 있으면 '뒤쪽(할인가)'."""
    vals = []
    for m in re.finditer(r"([\d]+(?:\.\d+)?)\s*元", text or ""):
        try:
            vals.append(float(m.group(1)))
        except Exception:
            pass
    if not vals:
        return 0.0
    return vals[-1]


def parse_monthly(text):
    """'월 1879개 판매' -> 1879"""
    m = re.search(r"월\s*([\d,]+)\s*개\s*판매", text or "")
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except Exception:
        return 0


def parse_repurchase(text):
    """'재구매 10.13%' -> 10.13"""
    m = re.search(r"재구매\s*([\d]+(?:\.\d+)?)\s*%", text or "")
    return float(m.group(1)) if m else 0.0


def parse_rating(text):
    """평점(5.0 / 4.8). ★ 뒤 숫자를 우선, 없으면 '판매' 줄 다음의 0~5 소수."""
    m = re.search(r"[★⭐]\s*([0-5](?:\.\d)?)", text or "")
    if m:
        return float(m.group(1))
    # ★ 가 텍스트에 안 들어오는 경우: 재구매 줄 앞의 단독 소수
    for line in [l.strip() for l in (text or "").split("\n") if l.strip()]:
        if re.fullmatch(r"[0-5]\.\d", line):
            return float(line)
    return 0.0


def parse_title(text):
    """상품명 = 가격/판매/재구매 줄이 아닌 첫 줄."""
    skip = ("원", "元", "판매", "재구매", "수입시", "할인", "이미지 검색",
            "찜하기", "★", "배송")
    for line in [l.strip() for l in (text or "").split("\n") if l.strip()]:
        if len(line) < 5:
            continue
        if any(s in line for s in skip):
            continue
        return line
    # 못 찾으면 가장 긴 줄
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    return max(lines, key=len) if lines else ""


def score_item(it, st=None):
    """월판매 / 재구매 / 평점 3가지에 점수. (각 2,2,1점 = 최대 5점)"""
    st = st or get_settings()
    pts = 0
    reasons = []
    if it.get("monthly", 0) >= st["min_monthly"]:
        pts += 2
        reasons.append("판매량")
    if it.get("repurchase", 0) >= st["min_repurchase"]:
        pts += 2
        reasons.append("재구매")
    if it.get("rating", 0) >= st["min_rating"]:
        pts += 1
        reasons.append("평점")
    # 가격 상한이 설정돼 있으면 넘는 상품은 제외
    if st["max_price_krw"] and it.get("price_krw", 0) > st["max_price_krw"]:
        return 0, "제외", "가격초과"
    if pts >= st["score_candidate"]:
        v = "후보"
    elif pts >= st["score_review"]:
        v = "검토"
    else:
        v = "보류"
    return pts, v, "+".join(reasons) if reasons else "-"


def parse_card(text, html="", keyword=""):
    link = ""
    m = re.search(r"https?://[^\s\"']*itId=\d+", html or "")
    if m:
        link = m.group(0)
    else:
        m = re.search(r"itId=(\d+)", html or "")
        if m:
            link = "https://sellochomes.co.kr/sourcinglife/alibaba/item?itId=" + m.group(1)

    it = {
        "keyword": keyword,
        "title": parse_title(text),
        "link": link,
        "price_krw": parse_krw(text),
        "price_cny": parse_cny(text),
        "monthly": parse_monthly(text),
        "repurchase": parse_repurchase(text),
        "rating": parse_rating(text),
    }
    it["score"], it["verdict"], it["why"] = score_item(it)
    return it


# ============================================================
# 브라우저 수집
# ============================================================
_JS_COLLECT = r"""
var links = Array.prototype.slice.call(
    document.querySelectorAll("a[href*='itId='], a[href*='/item?']"));
var seen = {}, out = [];
for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var href = a.href || '';
    var m = href.match(/itId=(\d+)/);
    if (!m) continue;
    var id = m[1];
    if (seen[id]) continue;
    var el = a, box = null;
    for (var k = 0; k < 8 && el; k++) {
        var t = el.innerText || '';
        if (t.indexOf('\uc6d0') >= 0 && t.length > 20) { box = el; break; }  // '원'
        el = el.parentElement;
    }
    if (!box) continue;
    seen[id] = 1;
    out.push({id: id, href: href,
              text: box.innerText || '',
              html: (box.outerHTML || '').slice(0, 8000)});
}
return out;
"""


def _ensure_1688_mode(driver, log=print):
    """좌측 상단 [타오바오 | 1688] 토글에서 1688 을 선택한다."""
    from selenium.webdriver.common.by import By
    try:
        els = driver.find_elements(By.XPATH, "//*[normalize-space(text())='1688']")
        for el in els:
            try:
                if el.is_displayed() and el.size.get("width", 0) < 260:
                    driver.execute_script("arguments[0].click();", el)
                    log("    1688 모드로 전환")
                    time.sleep(2.5)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _find_search_box(driver, log=print):
    """페이지(및 iframe) 안에서 검색 입력칸을 찾는다.
    못 찾으면 어떤 입력칸들이 있었는지 진단을 남긴다."""
    from selenium.webdriver.common.by import By

    def _scan():
        found = []
        try:
            els = driver.find_elements(By.CSS_SELECTOR, "input, textarea")
        except Exception:
            els = []
        for el in els:
            try:
                if not (el.is_displayed() and el.is_enabled()):
                    continue
                info = {
                    "el": el,
                    "type": (el.get_attribute("type") or "").lower(),
                    "ph": el.get_attribute("placeholder") or "",
                    "name": el.get_attribute("name") or "",
                    "id": el.get_attribute("id") or "",
                    "w": el.size.get("width", 0),
                }
                found.append(info)
            except Exception:
                continue
        return found

    # 1) 최상위 문서
    driver.switch_to.default_content()
    cands = _scan()
    if cands:
        best = _pick_box(cands)
        if best:
            return best, None

    # 2) iframe 안쪽
    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        frames = []
    for idx, fr in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
        except Exception:
            continue
        sub = _scan()
        if sub:
            best = _pick_box(sub)
            if best:
                log(f"    검색창을 iframe #{idx} 안에서 찾았습니다.")
                return best, idx
    driver.switch_to.default_content()

    # 진단
    log("    [진단] 검색창을 찾지 못했습니다. 화면에 있던 입력칸 목록:")
    driver.switch_to.default_content()
    for c in _scan()[:10]:
        log(f"        - type={c['type']!r} placeholder={c['ph']!r} "
            f"name={c['name']!r} id={c['id']!r} width={c['w']}")
    log(f"    [진단] iframe 개수: {len(frames)}")
    return None, None


def _pick_box(cands):
    """입력칸 후보 중 검색창으로 보이는 것을 고른다."""
    def score(c):
        s = 0
        blob = f"{c['ph']} {c['name']} {c['id']}".lower()
        if any(k in blob for k in ("검색", "search", "keyword", "query", "kw")):
            s += 10
        if c["type"] in ("search", "text", ""):
            s += 3
        s += min(c["w"] / 100.0, 5)
        return s
    ranked = sorted(cands, key=score, reverse=True)
    for c in ranked:
        if c["type"] in ("search", "text", "") and c["w"] >= 60:
            return c["el"]
    return ranked[0]["el"] if ranked else None


def search_url(keyword, mode="1688"):
    """소싱라이프 검색 주소.
    실제 주소 형식(2026-11-19 확인):
      https://sellochomes.co.kr/sourcinglife/1688/list?search=<키워드>
      https://sellochomes.co.kr/sourcinglife/taobao/list?search=<키워드>
    한글 키워드를 그대로 UTF-8 로 넣으면 된다."""
    from urllib.parse import quote
    return (f"https://sellochomes.co.kr/sourcinglife/{mode}/list?search="
            + quote(str(keyword)))


def _search(driver, keyword, log=print, mode="1688"):
    """검색 주소로 바로 이동한다(검색창을 찾을 필요가 없음)."""
    url = search_url(keyword, mode)
    log(f"    이동: {url}")
    driver.get(url)
    time.sleep(5)

    cur = (driver.current_url or "")
    try:
        log(f"    주소: {cur[:120]}")
    except Exception:
        pass
    if "login" in cur.lower():
        log("    [진단] 소싱라이프 로그인이 필요합니다. 열린 크롬에서 로그인 후 다시 실행하세요.")
        return False
    if f"/{mode}/" not in cur:
        log(f"    [진단] {mode} 모드 주소로 안 갔습니다. 현재: {cur[:90]}")
    return True


def _grab_everywhere(driver, log=print):
    """현재 문서와 iframe 안쪽까지 뒤져서 카드를 모은다."""
    from selenium.webdriver.common.by import By
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    try:
        raw = driver.execute_script(_JS_COLLECT) or []
    except Exception:
        raw = []
    if raw:
        return raw
    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception:
        frames = []
    for idx, fr in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(fr)
            sub = driver.execute_script(_JS_COLLECT) or []
        except Exception:
            sub = []
        if sub:
            log(f"    (카드를 iframe #{idx} 안에서 찾음)")
            return sub
    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    return []


def collect(driver, keyword, log=print, limit=60, debug=True, use_current=False):
    from selenium.webdriver.common.by import By

    if use_current:
        log("    지금 열려 있는 화면에서 수집합니다 (검색 안 함).")
    else:
        if not _search(driver, keyword, log=log):
            log("    >>> 자동 검색에 실패했습니다. 크롬에서 직접 검색해 두신 뒤,")
            log("        키워드 없이(엔터만) 다시 실행하면 그 화면을 읽습니다.")
            return []

    try:
        log(f"    현재 주소: {driver.current_url[:120]}")
    except Exception:
        pass

    # 지연 로딩: 카드 수가 더 안 늘어날 때까지 스크롤
    raw = []
    same = 0
    for step in range(20):
        try:
            driver.execute_script("window.scrollBy(0, 1600);")
        except Exception:
            pass
        time.sleep(1.1)
        cur = _grab_everywhere(driver, log=log)
        if len(cur) > len(raw):
            raw = cur
            same = 0
        else:
            same += 1
            if same >= 3 and raw:
                break
    try:
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass
    if raw:
        log(f"    [진단] 스크롤 후 카드 {len(raw)}개")

    if not raw:
        log("    [진단] 상품 카드를 못 찾았습니다.")
        try:
            log(f"    [진단] 제목: {driver.title}")
            log(f"    [진단] 주소: {driver.current_url[:140]}")
            body = driver.find_element(By.TAG_NAME, "body").text
            log(f"    [진단] 본문 길이: {len(body)}자")
            log(f"    [진단] 본문 첫 300자: {body[:300]}")
        except Exception:
            pass
        log("    >>> 열린 크롬 화면을 직접 확인해 주세요.")
        return []

    if debug:
        log(f"    [진단] 카드 {len(raw)}개 수집")
        log("    [진단] 첫 카드 텍스트:")
        for line in (raw[0].get("text") or "").split("\n")[:10]:
            log(f"        | {line}")

    return [(r.get("text") or "", (r.get("html") or "") +
             f"\n<!--href:{r.get('href','')}-->") for r in raw[:limit]]


def analyze_keyword(driver, keyword, log=print, use_current=False):
    cards = collect(driver, keyword, log=log, use_current=use_current)
    items = []
    for t, h in cards:
        it = parse_card(t, h, keyword)
        if it["title"] and (it["price_krw"] or it["price_cny"]):
            items.append(it)
    return items


# ============================================================
# 엑셀 저장
# ============================================================
def save_excel(items, path, log=print):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    F = "Arial"
    HEAD = PatternFill("solid", fgColor="44546A")
    thin = Side(style="thin", color="BFBFBF")
    BD = Border(left=thin, right=thin, top=thin, bottom=thin)
    FILL = {"후보": PatternFill("solid", fgColor="C6EFCE"),
            "검토": PatternFill("solid", fgColor="FFEB9C"),
            "보류": PatternFill("solid", fgColor="F2F2F2"),
            "제외": PatternFill("solid", fgColor="FFC7CE")}

    st = get_settings()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "소싱결과"

    ws["A1"] = "소싱라이프 x 1688 수집 결과"
    ws["A1"].font = Font(name=F, size=15, bold=True)
    ws["A2"] = (f"수집 {datetime.now():%Y-%m-%d %H:%M}  |  기준: 월판매 "
                f"{st['min_monthly']:,}개+ / 재구매 {st['min_repurchase']}%+ / "
                f"평점 {st['min_rating']}+  |  후보 {st['score_candidate']}점")
    ws["A2"].font = Font(name=F, size=9, italic=True, color="7F7F7F")

    heads = [("판정", 8), ("점수", 7), ("충족", 16), ("키워드", 11), ("상품명", 46),
             ("단가(원)", 11), ("단가(¥)", 10), ("월 판매", 10),
             ("재구매(%)", 10), ("평점", 7), ("링크", 44)]
    for i, (h, w) in enumerate(heads, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(name=F, bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BD
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[4].height = 26

    order = {"후보": 0, "검토": 1, "보류": 2, "제외": 3}
    items = sorted(items, key=lambda x: (order.get(x["verdict"], 9),
                                         -x["score"], -x["monthly"]))
    r = 5
    for it in items:
        vals = [it["verdict"], it["score"], it["why"], it["keyword"], it["title"],
                it["price_krw"], it["price_cny"], it["monthly"],
                it["repurchase"], it["rating"], it["link"]]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=F)
            c.border = BD
        ws.cell(row=r, column=1).fill = FILL.get(it["verdict"], FILL["보류"])
        for i in (1, 2, 8, 9, 10):
            ws.cell(row=r, column=i).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=6).number_format = "#,##0"
        ws.cell(row=r, column=7).number_format = "0.00"
        ws.cell(row=r, column=8).number_format = "#,##0"
        ws.cell(row=r, column=9).number_format = "0.0"
        r += 1

    ws.freeze_panes = "A5"
    if r > 5:
        ws.auto_filter.ref = f"A4:K{r-1}"
    wb.save(path)
    log(f"\n엑셀 저장: {path}")


# ============================================================
# 크롬 연결 / 실행
# ============================================================
def attach_chrome(log=print):
    import subprocess as sp
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    PORT = 9223
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    profile = os.path.join(root, "chrome_auto_profile")

    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORT}")
    try:
        d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        log("크롬 연결 완료 (열려 있는 창 재사용).")
        return d
    except Exception:
        pass

    log("크롬을 새로 띄웁니다...")
    paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             os.path.join(os.getenv("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")]
    exe = next((p for p in paths if os.path.exists(p)), None)
    if not exe:
        raise RuntimeError("크롬 실행파일을 찾을 수 없습니다.")
    sp.Popen([exe, f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
              "--lang=ko-KR", "--no-first-run", "--no-default-browser-check",
              "--start-maximized", SELLO_HOME])
    time.sleep(8)
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    log("크롬 연결 완료.")
    return d


def _load_env():
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.join(os.path.dirname(here), ".env"),
              os.path.join(os.path.dirname(os.path.dirname(here)), ".env")):
        if os.path.exists(p):
            try:
                load_dotenv(p, override=False)
            except Exception:
                pass
            return


def main():
    _load_env()
    kws = [a for a in sys.argv[1:] if a.strip()]
    use_current = False
    if not kws:
        print("키워드를 입력하면 자동으로 검색합니다.")
        print("크롬에서 이미 검색해 두셨다면, 그냥 [엔터]만 치세요 (그 화면을 읽습니다).")
        raw = input("검색할 키워드(한글 가능): ").strip()
        kws = [k for k in raw.split() if k]
        if not kws:
            use_current = True
            kws = ["(현재화면)"]

    st = get_settings()
    print("=" * 62)
    print("소싱라이프 x 1688 수집")
    print(f"  기준: 월판매 {st['min_monthly']:,}개+ / 재구매 {st['min_repurchase']}%+ / "
          f"평점 {st['min_rating']}+")
    print("=" * 62)

    driver = attach_chrome()
    allitems = []
    for i, kw in enumerate(kws, 1):
        print(f"\n[{i}/{len(kws)}] '{kw}' 검색 중...")
        items = analyze_keyword(driver, kw, log=print, use_current=use_current)
        print(f"    읽은 상품: {len(items)}개")
        if items and all(x["monthly"] == 0 for x in items):
            print("    ⚠️ 판매량·재구매·평점이 하나도 없습니다.")
            print("       타오바오 모드 화면일 가능성이 큽니다. 1688 모드로 보셔야 점수가 나옵니다.")
        cand = [x for x in items if x["verdict"] == "후보"]
        print(f"    후보 {len(cand)}개 / 검토 "
              f"{sum(1 for x in items if x['verdict']=='검토')}개")
        for x in sorted(cand, key=lambda z: -z["monthly"])[:5]:
            print(f"      [{x['score']}점] {x['price_krw']:,}원 "
                  f"월{x['monthly']:,}개 재구매{x['repurchase']}% ★{x['rating']} "
                  f"| {x['title'][:26]}")
        allitems += items
        time.sleep(2)

    if not allitems:
        print("\n수집된 상품이 없습니다. 위 [진단] 내용을 캡처해서 보내주세요.")
        return

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    out = os.path.join(root, f"소싱결과_{datetime.now():%Y%m%d_%H%M}.xlsx")
    save_excel(allitems, out)

    n = {}
    for x in allitems:
        n[x["verdict"]] = n.get(x["verdict"], 0) + 1
    print(f"총 {len(allitems)}개 | 후보 {n.get('후보',0)} / 검토 {n.get('검토',0)} / "
          f"보류 {n.get('보류',0)}")


if __name__ == "__main__":
    main()
