# -*- coding: utf-8 -*-
"""
detail_image_filter.py
  상세페이지 이미지 정리 파이프라인 (banner_filter 검증본을 모듈화).
  흐름: 중복 제거(dHash) -> 앞쪽 N장만 AI 분류(keep/translate/drop) -> 최대 6장 채택
        -> 채택된 '번역대상'만 중국어를 한글로 교체(in-place)

  stage1 등에서:
      from modules.detail_image_filter import process_folder
      process_folder(det_dir)
"""
import os, re, json, glob, shutil, warnings
warnings.filterwarnings("ignore")
from PIL import Image

MAX_USE = 6
AI_LIMIT = 8
MAX_TRANSLATE = 2
DUP_THRESHOLD = 10

_PROMPT = """\
이 이미지는 한국 쿠팡 상세페이지 후보다. 아래 3가지 중 하나로 분류하고 순수 JSON만 출력해라(설명/코드펜스 금지).

category:
- "keep"      : 중국어 거의 없는 제품 사진 또는 사용장면 사진
- "translate" : 제품 자체의 '성분/인증/기능/사용법/사용상황' 정보만. (예: 0异味 0重金属 0塑化剂 0甲醛, 150G 경량, 居家/出差/办公, 초급~상급 강도)
- "drop"      : 아래 중 하나라도 해당되면 정보처럼 보여도 무조건 drop
    * 판매자/쇼핑몰 홍보: 源头工厂, 现货速发, 品质保障, 正品保障, 售后无忧, 支持定制, OEM/ODM
    * 판매실적/과장광고: 판매량, 回头客, TOP1, 100万/1000万, 亚运会, 官方供应商
    * 보증문구: "N년 拉断 免费换新"
    * 다른 회사 브랜드: WOSWEIR, UMAY, SPG, Nanbowan, adidas 등
    * 중국어 슬로건이 대부분을 덮는 순수 광고 포스터

주의: 제품에 음각된 자체 로고(o:ooup, onoop, gooup 등)는 브랜드 문제 아님. 홍보성 섞이면 drop.

JSON: {"category":"keep","reason":"짧은이유","chinese":[{"orig":"원문","ko":"번역"}]}
중국어 없으면 chinese:[] .
"""

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT = os.path.join(_HERE, "..", "..", "fonts", "강원교육모두 Bold.ttf")
if not os.path.exists(_FONT):
    _FONT = r"C:\Windows\Fonts\malgun.ttf"


def _dhash(path, n=8):
    img = Image.open(path).convert("L").resize((n + 1, n))
    px = list(img.getdata()); w = n + 1; bits = 0; i = 0
    for r in range(n):
        for c in range(n):
            bits |= (1 << i) if px[r * w + c] > px[r * w + c + 1] else 0
            i += 1
    return bits


def _ham(a, b): return bin(a ^ b).count("1")


def _list(folder):
    out = []
    for ext in ("jpg", "jpeg", "png"):
        out += glob.glob(os.path.join(folder, f"detail_*.{ext}"))
    return sorted(out)


def process_folder(folder, log=print):
    """상세페이지 폴더 하나를 정리한다. 요약 dict 반환."""
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        log("    ⚠️ GEMINI_API_KEY 없음 — 상세이미지 정리 건너뜀")
        return {"skipped": True}
    genai.configure(api_key=key)
    model = genai.GenerativeModel(os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash"))

    if not os.path.isdir(folder):
        return {"skipped": True}
    sub = {k: os.path.join(folder, v) for k, v in
           {"tr": "_번역대상", "drop": "_제외배너", "dup": "_중복", "over": "_초과보관"}.items()}
    for d in sub.values():
        os.makedirs(d, exist_ok=True)
    # 재실행 복구
    for d in sub.values():
        for f in glob.glob(os.path.join(d, "detail_*.*")):
            try: shutil.move(f, os.path.join(folder, os.path.basename(f)))
            except Exception: pass

    files = _list(folder)
    if not files:
        return {"skipped": True}

    # 1) 중복 제거
    kept, hashes, dup = [], [], 0
    for f in files:
        try: h = _dhash(f)
        except Exception: kept.append(f); continue
        if any(_ham(h, kh) <= DUP_THRESHOLD for kh in hashes):
            try: shutil.move(f, os.path.join(sub["dup"], os.path.basename(f))); dup += 1
            except Exception: kept.append(f)
        else:
            hashes.append(h); kept.append(f)

    # 2) 앞쪽 8장만 AI
    to_ai = kept[:AI_LIMIT]; overflow = kept[AI_LIMIT:]
    keeps, trans, report = [], [], []
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
        cat = str(r.get("category", "keep")).lower()
        reason = r.get("reason", "")
        tr_txt = "  ".join(f"{t.get('orig','')}->{t.get('ko','')}" for t in (r.get("chinese") or []))
        if cat == "drop":
            try: shutil.move(f, os.path.join(sub["drop"], name))
            except Exception: pass
            report.append(f"[버림] {name}: {reason}")
        elif cat == "translate":
            trans.append(f); report.append(f"[번역대상] {name}: {reason}\n   {tr_txt}")
        else:
            keeps.append(f); report.append(f"[남김] {name}: {reason}")

    # 3) 최대 6장 채택 (번역대상 우선 1~2장)
    chosen = list(trans[:MAX_TRANSLATE])
    for f in keeps:
        if len(chosen) >= MAX_USE: break
        chosen.append(f)
    for f in trans:
        if len(chosen) >= MAX_USE: break
        if f not in chosen: chosen.append(f)
    chosen = chosen[:MAX_USE]; chosen_set = set(chosen)

    for f in keeps + trans + overflow:
        if f not in chosen_set and os.path.exists(f):
            try: shutil.move(f, os.path.join(sub["over"], os.path.basename(f)))
            except Exception: pass

    # 4) 채택된 번역대상 한글화 (PIL로 읽고/써서 한글 경로 안전)
    translated = 0
    chosen_tr = [f for f in chosen if f in trans]
    if chosen_tr:
        try:
            from modules.detail_image_localizer import analyze_text_regions, translate_text_regions
            import numpy as np
            for f in chosen_tr:
                try: shutil.copy(f, os.path.join(sub["tr"], os.path.basename(f)))  # 원본 보관
                except Exception: pass
                try:
                    regions = analyze_text_regions(f)
                    if not regions: continue
                    pil = Image.open(f).convert("RGB")
                    bgr = np.array(pil)[:, :, ::-1].copy()
                    out = translate_text_regions(bgr, regions, font_path=_FONT)
                    Image.fromarray(out[:, :, ::-1]).save(f)
                    translated += 1
                except Exception as e:
                    log(f"    ⚠️ 한글화 실패 {os.path.basename(f)}: {e}")
        except Exception as e:
            log(f"    ⚠️ 번역 모듈 로드 실패: {e}")

    try:
        open(os.path.join(folder, "_판별결과.txt"), "w", encoding="utf-8").write("\n".join(report))
    except Exception: pass

    log(f"    🖼️ 상세이미지 정리: 채택 {len(chosen)}장(번역 {translated}) / 중복 {dup} / 버림 {len(to_ai)-len(keeps)-len(trans)}")
    return {"chosen": len(chosen), "translated": translated, "dup": dup}


def process_folders(folders, log=print):
    for f in folders:
        try: process_folder(f, log=log)
        except Exception as e:
            log(f"    ⚠️ 상세이미지 정리 실패 ({f}): {e}")
