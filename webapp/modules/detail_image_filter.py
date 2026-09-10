# -*- coding: utf-8 -*-
"""
detail_image_filter.py  (단순 선별 버전)
  중복 제거(그룹당 1장) -> 앞쪽 N장 AI 분류(keep/drop)
  -> 걸러진 것(중복/광고/로고/글자많음)은 모두 '_삭제' 폴더 하나로
  -> 최대 MAX_USE 장 채택. 크롭/글자삭제 없음.
"""
import os, re, json, glob, shutil, warnings
warnings.filterwarnings("ignore")
from PIL import Image
try:
    import numpy as np
except Exception:
    np = None

MAX_USE = 5
AI_LIMIT = 10
DUP_THRESHOLD = 10
_DEL = "_삭제"

# 글씨 크롭 / 광고 감지 설정 20260828
AD_BUSY_RATIO = 0.25     # 복잡한 줄 비율 25% 이상이면 광고로 보고 삭제
MAX_CROP_RATIO = 0.28    # 위/아래 글씨 밴드를 잘라낼 수 있는 최대 비율(한쪽). 초과 시 원본 유지
_EDGE_SCAN = 0.25        # 가장자리 25% 구간에서 글씨 밴드 탐색

_PROMPT = """\
이 이미지는 한국 쿠팡 상세페이지 후보다. "keep" 또는 "drop" 으로만 분류하고 순수 JSON만 출력해라(설명/코드펜스 금지).

"drop" (아래 중 하나라도 해당하면 버림):
- 광고 포스터: 배경이 빨강/진남색/검정/금색 등으로 꽉 차거나, 금색/장식 액자 테두리가 있거나,
  큰 중국어 슬로건 제목이 배경을 덮는 홍보 이미지, 2~4분할 홍보 콜라주
- 판매자 홍보/과장광고: 源头工厂, 现货速发, 品质保障, 支持定制, 판매량, TOP1 등
- 타사 브랜드 로고/워터마크가 크게 있는 이미지
- 중국어 인증서/검사보고서/성적서 표, 회사명 표기 이미지
- 제품 없이 글자만 가득한 텍스트 배너

"keep":
- 위 drop 에 해당하지 않는 깨끗한 제품 사진 또는 사용장면 사진(글자 조금 있어도 광고 아니면 keep)

주의: 제품에 음각된 자체 로고는 브랜드 문제 아님.

JSON: {"action":"keep","reason":"짧은이유"}
"""


def _row_activity(gray):
    """각 가로줄의 밝기 변화량(글씨/복잡한 영역일수록 큼)."""
    return np.abs(np.diff(gray.astype(int), axis=1)).sum(axis=1)


def _is_ad(gray):
    """이미지 전체에 글씨가 퍼진 광고/홍보 콜라주인지 판정."""
    h = gray.shape[0]
    act = _row_activity(gray)
    thr = np.median(act) * 1.8
    busy_ratio = (act > thr).sum() / h
    return busy_ratio >= AD_BUSY_RATIO, busy_ratio


def _find_crop(gray):
    """위/아래 가장자리의 글씨 밴드를 찾아 잘라낼 (top, bottom) 반환.
    보수적: 글씨가 뚜렷할 때만 자르고, 글씨 덩어리가 여러 개면(짧은 여백으로 끊겨도)
    이어서 포함한다. 30% 초과로 잘라야 하면 그쪽은 자르지 않는다(제품 보호)."""
    h = gray.shape[0]
    act = _row_activity(gray)
    base = np.median(act[int(h * 0.35):int(h * 0.65)])  # 제품(중앙) 기준선
    strong = base * 2.5          # '확실한 글씨' 임계 (보수적으로 높임)
    quiet = base * 1.3           # 이 아래면 '여백'
    gap_limit = int(h * 0.06)    # 여백이 이보다 길게 이어지면 글씨 끝으로 확정

    # --- 아래쪽: 밑에서 위로 올라가며 글씨 밴드 추적 ---
    bottom = h
    scan_start = int(h * (1 - _EDGE_SCAN))
    found = False
    gap = 0
    y = h - 1
    while y >= scan_start:
        if act[y] > strong:
            found = True
            bottom = y
            gap = 0
        elif found:
            if act[y] < quiet:
                gap += 1
                if gap >= gap_limit:
                    break        # 충분히 긴 여백 -> 글씨 끝
            else:
                gap = 0          # 애매한 구간(소제목 등)은 계속 이어감
                bottom = y
        y -= 1
    if found:
        bottom = max(0, bottom - 4)
    if (h - bottom) > h * MAX_CROP_RATIO:   # 너무 많이 잘려야 하면 포기(제품 보호)
        bottom = h

    # --- 위쪽: 위에서 아래로 내려가며 글씨 밴드 추적 ---
    top = 0
    scan_end = int(h * _EDGE_SCAN)
    found = False
    gap = 0
    y = 0
    while y < scan_end:
        if act[y] > strong:
            found = True
            top = y
            gap = 0
        elif found:
            if act[y] < quiet:
                gap += 1
                if gap >= gap_limit:
                    break
            else:
                gap = 0
                top = y
        y += 1
    if found:
        top = min(h, top + 4)
    if top > h * MAX_CROP_RATIO:
        top = 0

    return top, bottom


def _score_gray(gray):
    """흑백 배열의 깨끗함 점수(낮을수록 깨끗)."""
    h = gray.shape[0]
    if h < 10:
        return 999.0
    act = _row_activity(gray)
    med = np.median(act)
    if med <= 0:
        med = 1.0
    busy = (act > med * 1.8).sum() / h
    edge = int(h * 0.2)
    strong = med * 2.5
    hits = (act[:edge] > strong).sum() + (act[-edge:] > strong).sum()
    return float(busy + (hits / max(1, edge * 2)) * 0.5)


def _try_smart_crop(path):
    """위/아래 글씨 밴드를 잘라보고, 점수가 확실히 좋아질 때만 저장한다.
    애매하거나 많이 잘라야 하면 원본을 그대로 둔다(제품 훼손 방지).
    반환: True면 크롭 저장됨."""
    if np is None:
        return False
    try:
        img = Image.open(path)
        gray = np.array(img.convert("L"))
    except Exception:
        return False
    h, w = gray.shape
    before = _score_gray(gray)
    if before <= 0.02:          # 이미 충분히 깨끗하면 건드리지 않음
        return False

    act = _row_activity(gray)
    base = np.median(act[int(h * 0.35):int(h * 0.65)])
    if base <= 0:
        return False
    strong = base * 2.0
    limit = int(h * MAX_CROP_RATIO)

    # 위쪽: 글씨가 끝나고 조용해지는 지점 찾기
    top = 0
    for y in range(0, limit):
        if act[y] > strong:
            top = y
    if top > 0:
        # 글씨 아래 여백까지 조금 더 내려감
        y = top
        while y < limit and act[y] > base * 1.2:
            y += 1
        top = min(y + 3, limit)

    # 아래쪽
    bottom = h
    for y in range(h - 1, h - limit, -1):
        if act[y] > strong:
            bottom = y
    if bottom < h:
        y = bottom
        while y > h - limit and act[y] > base * 1.2:
            y -= 1
        bottom = max(y - 3, h - limit)

    if top == 0 and bottom == h:
        return False
    if (bottom - top) < h * 0.5:      # 절반 이상 남아야 함
        return False

    cropped = gray[top:bottom, :]
    after = _score_gray(cropped)
    # 점수가 확실히 좋아진 경우에만 채택(30% 이상 개선)
    if after < before * 0.7:
        try:
            Image.open(path).crop((0, top, w, bottom)).save(path, quality=95)
            return True
        except Exception:
            return False
    return False


def _text_band_score(gray):
    """가로 '글씨 띠'가 차지하는 비율을 측정.
    핵심: 글씨 줄은 한 줄 안에서 밝음<->어두움 전환이 여러 번 반복된다(획 때문).
    털/니트 질감도 전환이 많지만 '밝은 배경(>=200)'과 '진한 획(<=90)' 사이의
    극단적 전환은 드물다. 두 조건을 함께 쓰면 질감에 속지 않고 글씨만 잡힌다."""
    h, w = gray.shape
    if h < 30 or w < 20:
        return 0.0
    g = gray.astype(int)

    dark = (g <= 90)
    light = (g >= 200)

    # 각 줄에서 '밝음 -> 어두움' 전환 횟수(획 개수 근사)
    # 밝은 픽셀 뒤에 어두운 픽셀이 오는 지점을 센다.
    trans = (light[:, :-1] & dark[:, 1:]).sum(axis=1)

    dark_r = dark.sum(axis=1) / float(w)
    # 글씨 줄: 극단 전환이 충분히 많고(획 4개 이상), 어두운 비율은 과하지 않음
    text_rows = (trans >= 4) & (dark_r < 0.45)

    frac = float(text_rows.sum()) / h
    return frac


def _clean_score(path):
    """이미지의 '깨끗함' 점수(낮을수록 글씨 없는 깨끗한 사진).
    단순화 20260901: 실물로 검증된 '글씨 획 감지' 하나만 사용한다.
    (모서리 로고/원색 지표는 오탐이 많아 제거)
      실측: 깨끗한 사진 0.0000 / 글씨 있는 사진 0.07~0.11"""
    if np is None:
        return 999.0
    try:
        gray = np.array(Image.open(path).convert("L"))
    except Exception:
        return 999.0
    if gray.shape[0] < 10:
        return 999.0
    return float(_text_band_score(gray))


def _clean_score_old3(path):
    """이미지의 '깨끗함' 점수. 낮을수록 글씨가 적은 깨끗한 제품컷.
    글씨/텍스트가 많으면 가로줄 밝기 변화가 큰 줄이 많아진다."""
    if np is None:
        return 999.0
    try:
        gray = np.array(Image.open(path).convert("L"))
    except Exception:
        return 999.0
    h = gray.shape[0]
    if h < 10:
        return 999.0
    act = _row_activity(gray)
    med = np.median(act)
    if med <= 0:
        med = 1.0
    thr = med * 1.8
    busy_ratio = (act > thr).sum() / h          # 복잡한 줄 비율
    # 가장자리(위/아래 20%)에 글씨 밴드가 있으면 가산점(=나쁨)
    edge = int(h * 0.2)
    strong = med * 2.5
    edge_hits = (act[:edge] > strong).sum() + (act[-edge:] > strong).sum()
    edge_ratio = edge_hits / max(1, edge * 2)
    return float(busy_ratio + edge_ratio * 0.5)


def _process_image(path):
    """이미지 한 장 처리. 반환: 'ad'(광고=삭제) 또는 'clean'(그대로 유지).
    크롭은 제품이 잘리는 사고를 막기 위해 하지 않는다(20260828 옵션1).
    글씨가 사방에 퍼진 명백한 광고만 삭제하고, 나머지는 원본 유지."""
    if np is None:
        return "clean"
    try:
        img = Image.open(path)
        gray = np.array(img.convert("L"))
    except Exception:
        return "clean"
    is_ad, _ = _is_ad(gray)
    if is_ad:
        return "ad"
    return "clean"
    return "clean"


def _dhash(path, n=8):
    img = Image.open(path).convert("L").resize((n + 1, n))
    px = list(img.getdata()); w = n + 1; bits = 0; i = 0
    for r in range(n):
        for c in range(n):
            bits |= (1 << i) if px[r * w + c] > px[r * w + c + 1] else 0
            i += 1
    return bits


def _ham(a, b):
    return bin(a ^ b).count("1")


def _list(folder):
    out = []
    for ext in ("jpg", "jpeg", "png"):
        out += glob.glob(os.path.join(folder, f"detail_*.{ext}"))
    return sorted(out)


def process_folder(folder, log=print):
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        log("    warn: GEMINI_API_KEY 없음 - 건너뜀")
        return {"skipped": True}
    genai.configure(api_key=key)
    model = genai.GenerativeModel(os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash"))

    if not os.path.isdir(folder):
        return {"skipped": True}

    del_dir = os.path.join(folder, _DEL)
    os.makedirs(del_dir, exist_ok=True)

    for f in glob.glob(os.path.join(del_dir, "detail_*.*")):
        try:
            shutil.move(f, os.path.join(folder, os.path.basename(f)))
        except Exception:
            pass

    files = _list(folder)
    if not files:
        return {"skipped": True}

    # 중복 제거 (dhash 해밍거리 <= DUP_THRESHOLD 이면 같은 이미지로 보고 _삭제로 이동)
    kept, hashes, dup = [], [], 0
    for f in files:
        try:
            h = _dhash(f)
        except Exception:
            kept.append(f); continue
        if any(_ham(h, kh) <= DUP_THRESHOLD for kh in hashes):
            try:
                shutil.move(f, os.path.join(del_dir, os.path.basename(f))); dup += 1
            except Exception:
                kept.append(f)
        else:
            hashes.append(h); kept.append(f)

    # ===== 깨끗한 이미지 상위 N장만 채택 20260829 =====
    # 중복제거 → 각 이미지의 '깨끗함 점수' 측정(글씨 적을수록 낮음)
    # → 점수 낮은 순으로 정렬 → 상위 MAX_USE 장만 남기고 나머지는 _삭제.
    # 글씨 있는 이미지를 자르거나 번역하지 않고 애초에 안 쓰는 방식(제품 훼손 없음).
    # 채택 장수는 .env 의 DETAIL_USE_COUNT 로 조절(기본 5).
    _ai_on = str(os.getenv("DETAIL_AI_FILTER", "off")).lower() in ("on", "1", "true", "yes")
    if not _ai_on:
        try:
            use_n = int(os.getenv("DETAIL_USE_COUNT", str(MAX_USE)))
        except Exception:
            use_n = MAX_USE
        if use_n < 1:
            use_n = 1

        scored = []
        n_crop = 0
        # 크롭 비활성화 20260901: 인물 사진이 잘리는 사고가 있어 자르기는 하지 않는다.
        # 글씨 있는 이미지는 자르지 말고 그냥 탈락시키고, 부족분은 대표이미지로 채운다.
        for f in kept:
            scored.append((_clean_score(f), f))
        scored.sort(key=lambda x: x[0])          # 깨끗한 순(점수 낮은 순)

        # '깨끗하다'고 인정할 점수 상한 (.env 의 DETAIL_CLEAN_MAX 로 조절)
        try:
            clean_max = float(os.getenv("DETAIL_CLEAN_MAX", "0.02"))
        except Exception:
            clean_max = 0.02

        chosen = [f for s, f in scored[:use_n] if s <= clean_max]
        chosen_set = set(chosen)
        dropped = [f for _s, f in scored if f not in chosen_set]
        n_drop = 0
        for f in dropped:
            try:
                shutil.move(f, os.path.join(del_dir, os.path.basename(f))); n_drop += 1
            except Exception:
                pass

        # 부족분은 대표이미지(스튜디오 변환본)에서 보충 20260831
        # 상세이미지 중 깨끗한 것이 use_n 장에 못 미치면, 같은 상품의
        # '대표이미지' 폴더에서 깨끗한 순으로 가져와 채운다.
        n_fill = 0
        if len(chosen) < use_n:
            try:
                prod_dir = os.path.dirname(os.path.abspath(folder))
                main_dir = os.path.join(prod_dir, "대표이미지")
                if os.path.isdir(main_dir):
                    cands = []
                    for ext in ("jpg", "jpeg", "png"):
                        for p in glob.glob(os.path.join(main_dir, f"*.{ext}")):
                            if os.path.dirname(p) == main_dir:
                                cands.append(p)
                    cands = sorted(set(cands))
                    cands.sort(key=lambda p: _clean_score(p))
                    need = use_n - len(chosen)
                    # 이미 채택된 상세이미지의 해시(대표이미지와 겹치는지 확인용)
                    detail_hashes = []
                    for f in chosen:
                        try:
                            detail_hashes.append(_dhash(f))
                        except Exception:
                            pass
                    used_hashes = list(detail_hashes)
                    for src in cands:
                        if need <= 0:
                            break
                        # 보충은 기준을 느슨하게(3배) 적용해 확실히 채운다.
                        # 대표이미지는 스튜디오 변환본이라 대체로 깨끗하다.
                        if _clean_score(src) > clean_max * 3:
                            continue
                        try:
                            hh = _dhash(src)
                            # 이미 채택된 '상세이미지'와 거의 같을 때만 건너뛴다.
                            # 대표이미지끼리(색상만 다른 컷)는 중복으로 보지 않는다.
                            if any(_ham(hh, uh) <= 3 for uh in detail_hashes):
                                continue
                        except Exception:
                            hh = None
                        dst = os.path.join(folder, f"__fill_{n_fill+1:03d}.jpg")
                        try:
                            shutil.copy(src, dst)
                            chosen.append(dst)
                            if hh is not None:
                                used_hashes.append(hh)
                            n_fill += 1; need -= 1
                        except Exception:
                            pass
            except Exception:
                pass

        # 채택된 이미지들을 detail_001..N 으로 순서 정리(상세페이지 배치용)
        try:
            tmp = []
            for i, f in enumerate(chosen, 1):
                ext = os.path.splitext(f)[1].lower() or ".jpg"
                t = os.path.join(folder, f"__tmp_{i:03d}{ext}")
                shutil.move(f, t); tmp.append((i, t, ext))
            for i, t, ext in tmp:
                shutil.move(t, os.path.join(folder, f"detail_{i:03d}{ext}"))
        except Exception:
            pass

        log(f"    상세이미지 정리: 채택 {len(chosen)}장 / 중복 {dup} / 크롭 {n_crop} / 제외 {n_drop} / 대표보충 {n_fill}")
        return {"chosen": len(chosen), "dup": dup, "drop": n_drop, "crop": n_crop, "fill": n_fill}

    to_ai = kept[:AI_LIMIT]
    overflow = kept[AI_LIMIT:]
    keeps, report, n_drop = [], [], 0

    for f in to_ai:
        name = os.path.basename(f)
        try:
            data = open(f, "rb").read()
            mime = "image/png" if f.lower().endswith(".png") else "image/jpeg"
            resp = model.generate_content([{"mime_type": mime, "data": data}, _PROMPT])
            raw = re.sub(r"^```json\s*|^```\s*|```$", "", (resp.text or "").strip(), flags=re.MULTILINE).strip()
            r = json.loads(raw)
        except Exception as e:
            keeps.append(f); report.append(f"[남김-오류] {name}: {e}"); continue

        action = str(r.get("action", "keep")).lower()
        reason = r.get("reason", "")
        if action == "drop":
            try:
                shutil.move(f, os.path.join(del_dir, name)); n_drop += 1
            except Exception:
                pass
            report.append(f"[삭제] {name}: {reason}")
        else:
            keeps.append(f)
            report.append(f"[남김] {name}: {reason}")

    chosen = keeps[:MAX_USE]
    chosen_set = set(chosen)
    for f in keeps + overflow:
        if f not in chosen_set and os.path.exists(f):
            try:
                shutil.move(f, os.path.join(del_dir, os.path.basename(f)))
            except Exception:
                pass

    try:
        open(os.path.join(folder, "_판별결과.txt"), "w", encoding="utf-8").write("\n".join(report))
    except Exception:
        pass

    log(f"    상세이미지 정리: 채택 {len(chosen)}장 / 중복 {dup} / 삭제 {n_drop}")
    return {"chosen": len(chosen), "dup": dup, "drop": n_drop}


def process_folders(folders, log=print):
    for f in folders:
        try:
            process_folder(f, log=log)
        except Exception as e:
            log(f"    정리 실패 ({f}): {e}")
