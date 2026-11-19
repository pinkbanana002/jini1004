# -*- coding: utf-8 -*-
"""
sourcing_1688.py - 1688 검색 결과 자동 수집 + 점수화 (소싱)

키워드를 1688에서 검색해서 상품 카드를 읽고, 점수를 매겨 엑셀로 저장한다.
읽는 항목: 상품명 / 링크 / 가격(¥) / 연간판매량 / 재구매율 / 공급사명 /
          공급사등급(实力商家·源头旗舰·超级工厂) / 상품배지(跨境·超级新品·严选)

1688 페이지는 구조가 자주 바뀌므로 CSS 클래스가 아니라
카드 '텍스트'에서 패턴(¥숫자, 回头率N%, 已售N万+件 등)을 찾는다.

실행:
    python modules/sourcing_1688.py 台球手套 耳罩
"""
import os
import re
import sys
import time
from datetime import datetime

# ============================================================
# 설정 (.env 로 조절)
# ============================================================
def _cfg(name, default, cast=float):
    try:
        return cast(os.getenv(name, str(default)))
    except Exception:
        return default


def get_settings():
    return {
        "exchange": _cfg("EXCHANGE_FACTOR", 200, float),      # ¥1 -> 원
        "min_sales": _cfg("SOURCING_MIN_SALES", 1000, int),   # 최소 연간판매량
        "min_return": _cfg("SOURCING_MIN_RETURN", 60, int),   # 최소 재구매율(%)
        "score_candidate": _cfg("SOURCING_SCORE_CANDIDATE", 6, int),
        "score_review": _cfg("SOURCING_SCORE_REVIEW", 4, int),
        "pts_each": _cfg("SOURCING_PTS_EACH", 2, int),
        "pts_new": _cfg("SOURCING_PTS_NEW", 1, int),
    }


GRADE_POINTS = {"황소": 3, "원천": 3, "슈퍼팩토리": 2, "일반": 0}

# 공급사 등급 배지 (중국어 -> 한글)
GRADE_MAP = [
    ("实力商家", "황소"),
    ("源头旗舰", "원천"),
    ("超级工厂", "슈퍼팩토리"),
    ("源头工厂", "슈퍼팩토리"),
]
# 상품 배지
PRODUCT_BADGES = ["跨境", "超级新品", "严选", "新品"]


# ============================================================
# 순수 파싱 (브라우저 없이 테스트 가능)
# ============================================================
def parse_price_cny(text):
    """'¥7.5' -> 7.5
    1688 은 가격을 '¥ / 5 / .3' 처럼 여러 줄로 쪼개 놓는 경우가 있어
    ¥ 뒤의 숫자·점·공백을 모아 붙인 뒤 해석한다."""
    m = re.search(r"¥\s*([\d][\d\s.]*)", text or "")
    if not m:
        return 0.0
    num = re.sub(r"\s+", "", m.group(1))
    m2 = re.match(r"\d+(?:\.\d{1,2})?", num)
    try:
        return float(m2.group(0)) if m2 else 0.0
    except Exception:
        return 0.0


def parse_annual_sales(text):
    """AiPrice 확장의 '연간 판매량: 148711' 을 우선 사용."""
    m = re.search(r"연간\s*판매량\s*[:：]?\s*([\d,]+)", text or "")
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return 0
    return 0


def parse_sold(text):
    """'已售10万+件' / '1.1万+件' / '5600+件' -> 대략 숫자.
    확장 프로그램이 없을 때 쓰는 보조 지표."""
    t = text or ""
    m = re.search(r"([\d]+(?:\.\d+)?)\s*万\s*\+?\s*件", t)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except Exception:
            return 0
    m = re.search(r"已售\s*([\d,]+)\s*\+?\s*件", t)
    if not m:
        m = re.search(r"([\d,]{3,})\s*\+?\s*件", t)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return 0
    return 0


def parse_return_rate(text):
    """'回头率 87%' -> 87"""
    m = re.search(r"回头率\s*([\d]+)\s*%", text or "")
    return int(m.group(1)) if m else 0


def parse_repurchase(text):
    """'近期300人回购' -> 300"""
    m = re.search(r"近期\s*([\d,]+)\s*人回购", text or "")
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            return 0
    return 0


def parse_grade(blob):
    """공급사 등급 배지 -> 한글 등급."""
    for cn, ko in GRADE_MAP:
        if cn in (blob or ""):
            return ko
    return "일반"


def parse_product_badges(blob):
    """상품 배지들을 모아 문자열로."""
    found = []
    b = blob or ""
    for w in PRODUCT_BADGES:
        if w in b and w not in found:
            found.append(w)
    # '超级新品' 이 있으면 '新品' 중복 제거
    if "超级新品" in found and "新品" in found:
        found.remove("新品")
    return " ".join(found)


def parse_supplier(text):
    """공급사명 추출. 배지 뒤 회사명 줄을 찾는다."""
    for line in [l.strip() for l in (text or "").split("\n") if l.strip()]:
        if any(k in line for k in ("有限公司", "商贸", "纺织", "工厂", "厂", "店", "商行")):
            # 배지 글자가 앞에 붙어 있으면 떼어낸다
            out = line
            for cn, _ko in GRADE_MAP:
                out = out.replace(cn, "")
            return out.strip()
    return ""


def parse_title(text):
    """상품명 = 가격/배지 줄이 아닌 첫 번째 의미 있는 줄."""
    skip = ("¥", "回头率", "退货包运费", "下单返", "近期", "运费",
            "배송비", "구매 단가", "최소 주문", "발송 시간", "대리 판매",
            "연간 판매량", "더보기", "已售")
    for line in [l.strip() for l in (text or "").split("\n") if l.strip()]:
        if any(s in line for s in skip):
            continue
        if len(line) < 4:
            continue
        out = line
        for w in PRODUCT_BADGES:
            out = out.replace(w, "")
        return out.strip()
    return ""


def score_item(item, st=None):
    """엑셀과 똑같은 규칙으로 점수를 매긴다."""
    st = st or get_settings()
    pts = GRADE_POINTS.get(item.get("grade", "일반"), 0)
    sales = item.get("annual_sales") or item.get("sold") or 0
    if sales >= st["min_sales"]:
        pts += st["pts_each"]
    if item.get("return_rate", 0) >= st["min_return"]:
        pts += st["pts_each"]
    if "新品" in (item.get("badges") or ""):
        pts += st["pts_new"]
    if pts >= st["score_candidate"]:
        verdict = "후보"
    elif pts >= st["score_review"]:
        verdict = "검토"
    else:
        verdict = "보류"
    return pts, verdict


def parse_card(text, html="", keyword=""):
    """카드 하나 -> 결과 dict"""
    blob = (text or "") + " " + (html or "")
    link = ""
    m = re.search(r"https?://detail\.1688\.com/offer/\d+\.html", html or "")
    if m:
        link = m.group(0)
    else:
        m = re.search(r"//detail\.1688\.com/offer/\d+\.html", html or "")
        if m:
            link = "https:" + m.group(0)

    item = {
        "keyword": keyword,
        "title": parse_title(text),
        "link": link,
        "price": parse_price_cny(text),
        "annual_sales": parse_annual_sales(text),
        "sold": parse_sold(text),
        "return_rate": parse_return_rate(text),
        "repurchase": parse_repurchase(text),
        "supplier": parse_supplier(text),
        "grade": parse_grade(blob),
        "badges": parse_product_badges(blob),
    }
    item["score"], item["verdict"] = score_item(item)
    return item


# ============================================================
# 1688 검색 (브라우저)
# ============================================================
# 상품 링크에서 거슬러 올라가 '카드' 전체를 잡는 자바스크립트.
# 1688 은 클래스 이름이 자주 바뀌므로 구조에 기대지 않는다.
_JS_COLLECT = r"""
var links = Array.prototype.slice.call(
    document.querySelectorAll("a[href*='detail.1688.com/offer'], a[href*='//detail.1688.com/offer']"));
var seen = {}, out = [];
for (var i = 0; i < links.length; i++) {
    var a = links[i];
    var href = a.href || '';
    var m = href.match(/offer\/(\d+)/);
    if (!m) continue;
    var id = m[1];
    if (seen[id]) continue;
    // 가격(¥)이 들어있는 조상까지 최대 7단계 올라간다
    var el = a, box = null;
    for (var k = 0; k < 7 && el; k++) {
        var t = el.innerText || '';
        if (t.indexOf('¥') >= 0 && t.length > 15) { box = el; break; }
        el = el.parentElement;
    }
    if (!box) continue;
    seen[id] = 1;
    out.push({id: id, href: href,
              text: box.innerText || '',
              html: (box.outerHTML || '').slice(0, 14000)});
}
return out;
"""


def _search_url(keyword, encoding="gbk"):
    """1688 검색 주소. 1688 은 검색어를 GBK 로 받는다."""
    from urllib.parse import quote
    try:
        kw = quote(str(keyword), encoding=encoding)
    except Exception:
        kw = quote(str(keyword))
    return "https://s.1688.com/selloffer/offer_search.htm?keywords=" + kw


def collect(driver, keyword, log=print, limit=40, debug=True):
    from selenium.webdriver.common.by import By

    # 1688 은 GBK 로 검색어를 받는다. 혹시 몰라 UTF-8 도 예비로 시도.
    for enc in ("gbk", "utf-8"):
        url = _search_url(keyword, enc)
        log(f"    검색({enc}): {url}")
        driver.get(url)
        time.sleep(3)

        # 지연 로딩 대비: 몇 번 스크롤
        for _ in range(3):
            try:
                driver.execute_script("window.scrollBy(0, 1200);")
            except Exception:
                pass
            time.sleep(0.8)
        try:
            driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass

        raw = []
        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                raw = driver.execute_script(_JS_COLLECT) or []
            except Exception as e:
                log(f"    [진단] 수집 스크립트 오류: {type(e).__name__}")
                raw = []
            if len(raw) >= 3:
                break
            time.sleep(1.0)

        if raw:
            if debug:
                log(f"    [진단] 카드 {len(raw)}개 수집 (인코딩 {enc})")
                log("    [진단] 첫 카드 텍스트:")
                for line in (raw[0].get("text") or "").split("\n")[:12]:
                    log(f"        | {line}")
                # 등급 배지가 페이지에 존재하는지 확인 (텍스트/HTML 양쪽)
                alltext = " ".join((r.get("text") or "") for r in raw)
                allhtml = " ".join((r.get("html") or "") for r in raw)
                for cn, ko in GRADE_MAP:
                    nt = alltext.count(cn)
                    nh = allhtml.count(cn)
                    if nt or nh:
                        log(f"    [진단] 배지 '{cn}'({ko}): 텍스트 {nt}건 / HTML {nh}건")
                if "연간 판매량" not in alltext:
                    log("    [진단] ' 연간 판매량' 표기 없음 "
                        "-> AiPrice 확장프로그램이 이 크롬에 없습니다. 已售 수치를 대신 씁니다.")
            cards = []
            for r in raw[:limit]:
                t = r.get("text") or ""
                h = (r.get("html") or "") + f"\n<!--href:{r.get('href','')}-->"
                if "¥" in t:
                    cards.append((t, h))
            return cards

        # 실패 진단
        log(f"    [진단] 상품 카드를 못 찾았습니다. (인코딩 {enc})")
        try:
            log(f"    [진단] 제목: {driver.title}")
        except Exception:
            pass
        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            log(f"    [진단] 본문 길이: {len(body)}자")
            log(f"    [진단] 본문 첫 300자: {body[:300]}")
            for word, mean in (("登录", "로그인 요구"), ("验证", "캡차/인증 요구"),
                               ("滑块", "슬라이더 인증"), ("没有找到", "검색 결과 없음")):
                if word in body:
                    log(f"    [진단] >>> '{word}' 발견 - {mean}")
        except Exception:
            pass
        try:
            n = driver.execute_script(
                "return document.querySelectorAll(\"a[href*='detail.1688.com/offer']\").length;")
            log(f"    [진단] 상품 링크 개수: {n}")
            log(f"    [진단] page_source 길이: {len(driver.page_source)}자")
        except Exception:
            pass

    return []


def analyze_keyword(driver, keyword, log=print, limit=40):
    cards = collect(driver, keyword, log=log, limit=limit)
    items = []
    for t, h in cards:
        it = parse_card(t, h, keyword)
        if it["title"]:
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
            "보류": PatternFill("solid", fgColor="F2F2F2")}

    st = get_settings()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "수집결과"

    ws["A1"] = "1688 소싱 수집 결과"
    ws["A1"].font = Font(name=F, size=15, bold=True)
    ws["A2"] = (f"수집 시각 {datetime.now():%Y-%m-%d %H:%M}  |  "
                f"기준: 판매량 {st['min_sales']:,}+ / 재구매율 {st['min_return']}%+ / "
                f"후보 {st['score_candidate']}점+  |  환율 ¥1 = {st['exchange']:,.0f}원")
    ws["A2"].font = Font(name=F, size=9, italic=True, color="7F7F7F")

    heads = [("판정", 8), ("총점", 7), ("키워드", 11), ("상품명", 40),
             ("가격(¥)", 9), ("원가(원)", 11), ("연간 판매량", 12),
             ("누적 판매(已售)", 13), ("재구매율(%)", 11), ("최근 재구매", 11),
             ("공급사 등급", 12), ("상품 배지", 14), ("공급사명", 26), ("링크", 40)]
    for i, (h, w) in enumerate(heads, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(name=F, bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BD
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[4].height = 28

    order = {"후보": 0, "검토": 1, "보류": 2}
    items = sorted(items, key=lambda x: (order.get(x["verdict"], 9), -x["score"], x["price"]))

    r = 5
    for it in items:
        vals = [it["verdict"], it["score"], it["keyword"], it["title"],
                it["price"], None, it["annual_sales"], it["sold"],
                it["return_rate"], it["repurchase"],
                it["grade"], it["badges"], it["supplier"], it["link"]]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=i, value=v)
            c.font = Font(name=F)
            c.border = BD
        # 원가는 수식으로 (환율 바꾸면 다시 계산되게)
        ws.cell(row=r, column=6, value=f"=ROUND(E{r}*{st['exchange']},0)")
        ws.cell(row=r, column=1).fill = FILL.get(it["verdict"], FILL["보류"])
        ws.cell(row=r, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=r, column=5).number_format = "0.00"
        for col in (6, 7, 8):
            ws.cell(row=r, column=col).number_format = "#,##0"
        r += 1

    ws.freeze_panes = "A5"
    if r > 5:
        ws.auto_filter.ref = f"A4:N{r - 1}"
    wb.save(path)
    log(f"\n엑셀 저장: {path}")


# ============================================================
# 크롬 연결
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
              "--start-maximized", "https://www.1688.com/"])
    time.sleep(7)
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
    if not kws:
        raw = input("검색할 키워드(중국어)를 입력하세요. 여러 개면 띄어쓰기: ").strip()
        kws = [k for k in raw.split() if k]
    if not kws:
        print("키워드가 없습니다.")
        return

    st = get_settings()
    print("=" * 60)
    print("1688 소싱 수집")
    print(f"  환율 ¥1 = {st['exchange']:,.0f}원 / 최소 판매량 {st['min_sales']:,} / "
          f"최소 재구매율 {st['min_return']}%")
    print("=" * 60)

    driver = attach_chrome()
    allitems = []
    for i, kw in enumerate(kws, 1):
        print(f"\n[{i}/{len(kws)}] '{kw}' 검색 중...")
        items = analyze_keyword(driver, kw, log=print)
        print(f"    읽은 상품: {len(items)}개")
        cand = [x for x in items if x["verdict"] == "후보"]
        print(f"    후보 {len(cand)}개 / 검토 {sum(1 for x in items if x['verdict']=='검토')}개")
        for x in sorted(cand, key=lambda z: -z["score"])[:5]:
            print(f"      [{x['score']}점] ¥{x['price']} {x['grade']} "
                  f"판매 {x['annual_sales'] or x['sold']:,} 재구매 {x['return_rate']}% "
                  f"| {x['title'][:28]}")
        allitems += items
        time.sleep(2)

    if not allitems:
        print("\n수집된 상품이 없습니다. 위 [진단] 내용을 캡처해서 보내주세요.")
        return

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    out = os.path.join(root, f"소싱결과_{datetime.now():%Y%m%d_%H%M}.xlsx")
    save_excel(allitems, out)

    n = {"후보": 0, "검토": 0, "보류": 0}
    for x in allitems:
        n[x["verdict"]] = n.get(x["verdict"], 0) + 1
    print(f"총 {len(allitems)}개 | 후보 {n['후보']} / 검토 {n['검토']} / 보류 {n['보류']}")


if __name__ == "__main__":
    main()
