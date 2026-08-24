# -*- coding: utf-8 -*-
"""
detail_image_filter.py  (크롭/삭제 버전 — 번역 미사용)
  상세페이지 이미지 정리 파이프라인.
  흐름: 중복 제거(dHash)
        -> 앞쪽 N장만 AI 분류(keep/crop_*/remove/drop) + 글자박스 좌표
        -> crop: 위/아래 글자 띠 잘라내기 / remove: 글자 인페인팅 삭제
        -> 최대 5장 채택

  stage1 등에서:
      from modules.detail_image_filter import process_folder
      process_folder(det_dir)

  * 번역(한글 얹기)은 사용하지 않는다. 자르거나 지우기만 한다.
  * 글자 위치는 Gemini Vision으로 판단한다(정확). => GEMINI_API_KEY 필요.
"""
import os, re, json, glob, shutil, warnings
warnings.filterwarnings("ignore")
from PIL import Image

# ── 설정값 ────────────────────────────────────────────────────────────────
MAX_USE = 6          # 최종 채택 장수
AI_LIMIT = 10        # AI로 분류할 앞쪽 장수
DUP_THRESHOLD = 14   # dHash 해밍거리 (클수록 더 많이 중복으로 제거 = 비용 절감)

# 크롭 안전장치: 위/아래에서 잘라낼 수 있는 최대 비율(각 변 기준).
# 글자 띠가 이보다 두꺼우면 "제품까지 먹는다"고 보고 remove로 돌린다.
MAX_CROP_RATIO = 0.35

_PROMPT = """\
이 이미지는 한국 쿠팡 상세페이지 후보다. 아래 action 중 하나로 분류하고 순수 JSON만 출력해라(설명/코드펜스 금지).

먼저 판단 규칙 (위에서부터 순서대로 확인하고, 처음 맞는 것으로 결정):
- (1) ★최우선★ 광고 포스터는 제품이 크게 보여도 무조건 "drop" 한다.
      아래 중 하나라도 해당하면 제품이 잘 보여도 살리지 말고 버려라:
        · 배경 전체가 빨강/진남색/검정/금색 등 진한 색으로 꽉 차 있다
        · 금색/갈색 액자나 장식 테두리(사진을 액자처럼 감싼 프레임)가 있다
        · 큰 중국어 슬로건 제목(4자 이상, 예: 深层按摩捶, 经络拍痧板, 多种按摩体验)이 배경을 덮는다
        · 여러 칸(2분할·4분할)에 각각 중국어 설명이 붙은 홍보 콜라주
        · 판매자 홍보/과장광고/타사 브랜드/중국어 인증서·성적서/회사명 표기
      => "drop"  (이런 이미지는 글자를 지우려 하지 마라. 지우면 지저분해진다.)
- (2) 글자가 전혀 없는 깨끗한 제품 사진(흰색·연한 단색 배경의 제품컷)은 "keep". (가장 선호)
- (3) 이미지에 사람(모델)이 크게 나오면 => 자르지 말 것. 단, remove 하기 전에 (1)을 반드시 다시 확인:
      ★ 배경이 빨강/진남색/검정 등 진한 색이거나, 액자 테두리가 있거나, 큰 광고 슬로건이 있으면
        => 사람이 있어도 "remove" 가 아니라 "drop" (이건 광고 포스터다. 지우지 말고 버려라)
      * 배경이 흰색·연한 단색이고 글자가 있으면 => "remove"
      * 배경이 복잡/진한색인데 (1)에 딱 안 맞고 못 버리겠으면 => "keep" (글자 남김)
      * 글자가 전혀 없으면 => "keep"
- (4) 사람이 없고 (1)의 광고 포스터도 아니면, 배경과 글자 위치로 정한다:
      * 글자가 거의 없는 깨끗한 제품 사진            => "keep"
      * 배경이 흰색·연한 단색 + 글자가 '위쪽 가장자리 띠'에만  => "crop_top"
      * 배경이 흰색·연한 단색 + 글자가 '아래쪽 가장자리 띠'에만 => "crop_bottom"
      * 배경이 흰색·연한 단색 + 글자가 '위·아래 띠' 양쪽에     => "crop_both"
      * 배경이 흰색·연한 단색 + 글자가 제품 위에 겹침          => "remove"

핵심 원칙: 배경이 흰색·연한 단색일 때만 remove/crop 로 깨끗해진다.
배경이 진하거나 화려하거나 액자가 있으면 => remove 하지 말고, 광고면 "drop", 아니면 "keep".
확신이 안 서면 remove 대신 keep(글자 남김) 을 택해라. 뿌옇게 번지는 것보다 낫다.
remove 로 지울 대상: 흰/연한 배경 위의 중국어 문구, '02' 같은 페이지 번호 등. (제품 음각 로고는 제외)

drop 세부 기준(정보처럼 보여도 아래면 무조건 drop):
  판매자 홍보(源头工厂,现货速发,品质保障,支持定制,OEM/ODM), 판매실적/과장(판매량,回头客,TOP1,100万,官方供应商),
  보증문구(N년 免费换新), 타사 브랜드(WOSWEIR,UMAY,SPG,adidas 등), 중국어 검사보고서/인증서 표(检测报告,判定要求,GB 6675 등),
  중국어 슬로건이 대부분을 덮는 순수 광고 포스터.
주의: 제품에 음각된 자체 로고는 브랜드 문제 아님.

박스 좌표는 [ymin,xmin,ymax,xmax] 형식이며 0~1000 으로 정규화한다(이미지 좌상단 0, 우하단 1000).
- crop_* 인 경우: 잘라낼 글자 띠의 세로 범위를 boxes 에 넣어라(위 띠, 아래 띠 각각).
- remove 인 경우: 지울 글자 영역들을 boxes 에 넣어라(여러 개 가능).
- keep / drop 인 경우: boxes 는 [] 로 둔다.

JSON 형식(정확히 이 키만):
{"action":"keep","reason":"짧은이유","boxes":[[ymin,xmin,ymax,xmax]]}
"""

_HERE = os.path.dirname(os.path.abspath(__file__))


# ── 유틸 ──────────────────────────────────────────────────────────────────
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


def _box_to_px(box, width, height):
    """[ymin,xmin,ymax,xmax] (0~1000) -> (x1,y1,x2,y2) 픽셀."""
    ymin, xmin, ymax, xmax = box
    x1 = max(0, int(xmin / 1000 * width))
    y1 = max(0, int(ymin / 1000 * height))
    x2 = min(width, int(xmax / 1000 * width))
    y2 = min(height, int(ymax / 1000 * height))
    return x1, y1, x2, y2


def _crop_bands(path, boxes, action):
    """위/아래 글자 띠를 잘라내고 저장(in-place). 성공 시 True."""
    try:
        pil = Image.open(path).convert("RGB")
    except Exception:
        return False
    w, h = pil.size

    top_cut = 0            # 위에서 잘라낼 y (여기까지 버림)
    bottom_cut = h         # 아래에서 이 y부터 버림

    for box in boxes or []:
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = _box_to_px(box, w, h)
        mid = (y1 + y2) / 2
        if mid < h / 2:                       # 위쪽 띠
            top_cut = max(top_cut, y2)
        else:                                  # 아래쪽 띠
            bottom_cut = min(bottom_cut, y1)

    if action == "crop_top":
        bottom_cut = h
    elif action == "crop_bottom":
        top_cut = 0
    # crop_both 는 둘 다 사용

    # 안전장치: 너무 많이 자르면(제품까지) 크롭 취소
    if top_cut > h * MAX_CROP_RATIO:
        top_cut = 0
    if bottom_cut < h * (1 - MAX_CROP_RATIO):
        bottom_cut = h

    if top_cut <= 0 and bottom_cut >= h:
        return False  # 자를 게 없음

    if bottom_cut - top_cut < h * 0.3:
        return False  # 남는 게 너무 적으면 크롭 포기

    cropped = pil.crop((0, top_cut, w, bottom_cut))
    cropped.save(path)
    return True


def _remove_text(path, boxes):
    """글자 영역을 인페인팅으로 지우고 저장(in-place). 성공 시 True."""
    try:
        import numpy as np
        import cv2
    except Exception:
        return False
    try:
        pil = Image.open(path).convert("RGB")
    except Exception:
        return False
    bgr = np.array(pil)[:, :, ::-1].copy()
    h, w = bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    for box in boxes or []:
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = _box_to_px(box, w, h)
        # 글자 테두리까지 확실히 덮도록 약간 여유
        pad = max(2, int((y2 - y1) * 0.08))
        y1 = max(0, y1 - pad); y2 = min(h, y2 + pad)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
    if not mask.any():
        return False
    result = cv2.inpaint(bgr, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
    Image.fromarray(result[:, :, ::-1]).save(path)
    return True


# ── 메인 ──────────────────────────────────────────────────────────────────
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
           {"drop": "_제외배너", "dup": "_중복", "over": "_초과보관", "orig": "_원본백업"}.items()}
    for d in sub.values():
        os.makedirs(d, exist_ok=True)

    # 재실행 복구: 하위 폴더의 detail_* 를 상위로 되돌림(원본백업 제외)
    for kk, d in sub.items():
        if kk == "orig":
            continue
        for f in glob.glob(os.path.join(d, "detail_*.*")):
            try:
                shutil.move(f, os.path.join(folder, os.path.basename(f)))
            except Exception:
                pass

    files = _list(folder)
    if not files:
        return {"skipped": True}

    # 1) 중복 제거
    kept, hashes, dup = [], [], 0
    for f in files:
        try:
            h = _dhash(f)
        except Exception:
            kept.append(f); continue
        if any(_ham(h, kh) <= DUP_THRESHOLD for kh in hashes):
            try:
                shutil.move(f, os.path.join(sub["dup"], os.path.basename(f))); dup += 1
            except Exception:
                kept.append(f)
        else:
            hashes.append(h); kept.append(f)

    # 2) 앞쪽 N장만 AI 분류
    to_ai = kept[:AI_LIMIT]
    overflow = kept[AI_LIMIT:]
    results = []   # (path, action, boxes)
    report = []
    n_drop = 0

    for f in to_ai:
        name = os.path.basename(f)
        try:
            data = open(f, "rb").read()
            mime = "image/png" if f.lower().endswith(".png") else "image/jpeg"
            resp = model.generate_content([{"mime_type": mime, "data": data}, _PROMPT])
            raw = re.sub(r"^```json\s*|^```\s*|```$", "", (resp.text or "").strip(), flags=re.MULTILINE).strip()
            r = json.loads(raw)
        except Exception as e:
            results.append((f, "keep", [])); report.append(f"[남김-오류] {name}: {e}"); continue

        action = str(r.get("action", "keep")).lower()
        reason = r.get("reason", "")
        boxes = r.get("boxes") or []
        if action not in ("keep", "crop_top", "crop_bottom", "crop_both", "remove", "drop"):
            action = "keep"

        if action == "drop":
            try:
                shutil.move(f, os.path.join(sub["drop"], name)); n_drop += 1
            except Exception:
                pass
            report.append(f"[버림] {name}: {reason}")
        else:
            results.append((f, action, boxes))
            report.append(f"[{action}] {name}: {reason}")

    # 3) 최대 5장 채택 — 우선순위: 깨끗한 제품컷(keep+글자없음) > 나머지
    #    각 그룹 안에서는 원래 등장 순서를 유지한다(stable).
    def _priority(t):
        _path, _action, _boxes = t
        if _action == "keep" and not _boxes:
            return 0   # 글자 없는 깨끗한 이미지 최우선
        if _action == "keep":
            return 1   # keep 인데 글자 남긴 것(복잡배경)
        return 2       # crop / remove 처리 대상
    ordered = sorted(results, key=_priority)  # sorted 는 안정 정렬이라 그룹 내 순서 유지
    chosen = ordered[:MAX_USE]
    chosen_paths = {t[0] for t in chosen}

    # 채택 안 된 것 + overflow → 초과보관
    for f, _, _ in results:
        if f not in chosen_paths and os.path.exists(f):
            try:
                shutil.move(f, os.path.join(sub["over"], os.path.basename(f)))
            except Exception:
                pass
    for f in overflow:
        if os.path.exists(f):
            try:
                shutil.move(f, os.path.join(sub["over"], os.path.basename(f)))
            except Exception:
                pass

    # 4) 채택본에 크롭/삭제 적용 (원본은 _원본백업에 보관)
    n_crop = n_removed = 0
    for f, action, boxes in chosen:
        if action in ("crop_top", "crop_bottom", "crop_both", "remove"):
            try:
                shutil.copy(f, os.path.join(sub["orig"], os.path.basename(f)))
            except Exception:
                pass
        try:
            if action in ("crop_top", "crop_bottom", "crop_both"):
                if _crop_bands(f, boxes, action):
                    n_crop += 1
                elif boxes:
                    # 크롭이 안전장치에 걸리면 글자 삭제로 대체
                    if _remove_text(f, boxes):
                        n_removed += 1
            elif action == "remove":
                if _remove_text(f, boxes):
                    n_removed += 1
        except Exception as e:
            log(f"    ⚠️ 이미지 처리 실패 {os.path.basename(f)}: {e}")

    try:
        open(os.path.join(folder, "_판별결과.txt"), "w", encoding="utf-8").write("\n".join(report))
    except Exception:
        pass

    log(f"    🖼️ 상세이미지 정리: 채택 {len(chosen)}장 "
        f"(크롭 {n_crop} / 글자삭제 {n_removed}) / 중복 {dup} / 버림 {n_drop}")
    return {"chosen": len(chosen), "crop": n_crop, "removed": n_removed, "dup": dup, "drop": n_drop}


def process_folders(folders, log=print):
    for f in folders:
        try:
            process_folder(f, log=log)
        except Exception as e:
            log(f"    ⚠️ 상세이미지 정리 실패 ({f}): {e}")
