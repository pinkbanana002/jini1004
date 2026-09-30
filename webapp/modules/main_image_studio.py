# -*- coding: utf-8 -*-
"""
main_image_studio.py
  대표이미지를 Gemini 이미지 모델(nano-banana)로 '스튜디오 배경'으로 변환.
  제품은 그대로 두고 배경만 교체. 원본은 _원본 폴더에 백업.

  stage1 등에서:
      from modules.main_image_studio import process_main_images
      process_main_images(img_dir)      # img_dir = '.../대표이미지'
"""
import os, io, glob, shutil, warnings
warnings.filterwarnings("ignore")
from PIL import Image

# 스타일: .env 의 MAIN_IMAGE_STYLE 로 변경 가능 (프로스튜디오 | 미니멀마블)
_STYLES = {
    "프로스튜디오": (
        "Replace the background with a clean professional e-commerce studio backdrop: "
        "soft seamless light-gray to white gradient, soft studio lighting, a subtle realistic "
        "contact shadow under the product. "
        "Also REMOVE every piece of overlaid text, dimension labels, measurement numbers, "
        "arrows, callout lines, watermarks, brand logos and any writing that is printed on top "
        "of the image, leaving only the clean product on the new background."
    ),
    "미니멀마블": (
        "Replace the background with a minimal elegant white marble surface with soft natural "
        "lighting and a gentle realistic shadow, high-end e-commerce look. "
        "Also REMOVE every piece of overlaid text, dimension labels, measurement numbers, "
        "arrows, callout lines, watermarks, brand logos and any writing that is printed on top "
        "of the image, leaving only the clean product on the new background."
    ),
}
_RULE = (
    " Keep the PHYSICAL PRODUCT EXACTLY the same: identical shape, color, texture and proportions. "
    "Do not redraw, add, or remove any physical part of the product itself. "
    "CRITICAL CLEANUP REQUIREMENT: the final image must be COMPLETELY FREE of any graphics that are "
    "overlaid on the photo. Scan ALL FOUR CORNERS and every edge carefully and erase any small "
    "shop logo, brand mark, seller badge, icon, stamp, sticker, semi-transparent watermark, "
    "Chinese or English lettering, numbers, measurement labels, arrows or callout lines - "
    "even if they are small, faint, low-contrast or partially transparent. "
    "Replace those areas with the clean studio background so nothing remains. "
    "The result must contain ZERO text and ZERO logos anywhere in the frame. "
    "Photorealistic, high resolution, centered square composition. "
    "Return a single edited image."
)


def _erase_corner_marks(img, ratio=0.16, tol=14):
    """모서리/상하단 띠에 남은 로고·색상명·워터마크를 배경색으로 덮어 지운다.
    AI가 놓친 마크를 확실히 제거하기 위한 마무리 처리.
    제품이 걸쳐 있는 영역은 건드리지 않는다."""
    try:
        import numpy as _np
    except Exception:
        return img
    w, h = img.size
    side = int(min(w, h) * ratio)
    if side < 8:
        return img
    arr = _np.array(img.convert("RGB")).astype(int)

    # 배경색 추정: 바깥 가장자리 픽셀들의 중앙값
    edge = max(2, side // 6)
    samples = _np.concatenate([
        arr[0:edge, :, :].reshape(-1, 3),
        arr[h - edge:h, :, :].reshape(-1, 3),
        arr[:, 0:edge, :].reshape(-1, 3),
        arr[:, w - edge:w, :].reshape(-1, 3),
    ], axis=0)
    bg = _np.median(samples, axis=0)
    bg_color = tuple(int(v) for v in bg)

    out = img.convert("RGB").copy()
    from PIL import ImageDraw as _ImageDraw
    d = _ImageDraw.Draw(out)

    def _maybe_fill(x0, y0, x1, y1, lo=0.002, hi=0.45):
        """해당 영역에 배경과 다른 것이 조금 있으면(=마크) 배경색으로 덮는다.
        너무 많으면 제품이므로 건드리지 않는다."""
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(w, x1); y1 = min(h, y1)
        if x1 - x0 < 4 or y1 - y0 < 4:
            return
        region = arr[y0:y1, x0:x1, :]
        diff = _np.abs(region - bg).sum(axis=2)
        frac = (diff > tol * 3).mean()
        if lo < frac < hi:
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=bg_color)

    # 1) 상단/하단 가로 띠를 좌우로 나눠 검사 (로고·색상명이 주로 여기 있음)
    band = int(h * 0.13)
    half = w // 2
    _maybe_fill(0, 0, half, band)              # 좌측 상단 띠
    _maybe_fill(half, 0, w, band)              # 우측 상단 띠
    _maybe_fill(0, h - band, half, h)          # 좌측 하단 띠
    _maybe_fill(half, h - band, w, h)          # 우측 하단 띠

    # 2) 네 모서리 정사각 영역도 한 번 더 (작은 아이콘 대비)
    _maybe_fill(0, 0, side, side)
    _maybe_fill(w - side, 0, w, side)
    _maybe_fill(0, h - side, side, h)
    _maybe_fill(w - side, h - side, w, h)
    return out


def process_main_images(img_dir, log=print):
    """대표이미지 폴더 하나의 이미지들을 스튜디오 배경으로 변환(in-place, 원본은 _원본 백업)."""
    # ===== 대표이미지 스튜디오 완전 비활성화 (원본 그대로 사용, 비용 0) =====
    # 다시 켜려면 아래 두 줄을 지우세요.
    log("    🎨 대표이미지 스튜디오: 꺼짐 (원본 그대로 사용)")
    return {"skipped": True, "disabled": True}
    # =====================================================================
    if not os.path.isdir(img_dir):
        return {"skipped": True}
    import google.generativeai as genai
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        log("    ⚠️ GEMINI_API_KEY 없음 — 대표이미지 스튜디오 변환 건너뜀")
        return {"skipped": True}
    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    style = os.getenv("MAIN_IMAGE_STYLE", "미니멀마블")
    desc = _STYLES.get(style, _STYLES["미니멀마블"])
    model = genai.GenerativeModel(model_name)

    imgs = []
    for ext in ("jpg", "jpeg", "png", "webp"):
        imgs += [f for f in glob.glob(os.path.join(img_dir, f"*.{ext}"))
                 if os.path.dirname(f) == img_dir]
    imgs = sorted(imgs)
    if not imgs:
        return {"skipped": True}

    backup = os.path.join(img_dir, "_원본")
    os.makedirs(backup, exist_ok=True)

    # 아직 처리 안 된(_원본에 백업 없는) 이미지만 대상으로 추림
    todo = [f for f in imgs
            if not os.path.exists(os.path.join(backup, os.path.basename(f)))]
    if not todo:
        log(f"    🎨 대표이미지 스튜디오 변환: 0장 (이미 모두 처리됨)")
        return {"done": 0, "style": style}

    # 동시 처리 개수 (.env 의 MAIN_IMAGE_WORKERS 로 조절, 기본 4장 동시)
    # 너무 크게 하면 Gemini 429(quota 초과)가 더 잘 터지므로 3~4 권장.
    try:
        workers = int(os.getenv("MAIN_IMAGE_WORKERS", "4"))
    except Exception:
        workers = 4
    if workers < 1:
        workers = 1

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _one(f):
        """이미지 한 장 변환. 성공하면 True, 실패/건너뜀이면 False."""
        name = os.path.basename(f)
        try:
            src = Image.open(f).convert("RGB")
            resp = model.generate_content([desc + _RULE, src], request_options={"timeout": 30})
            out_img = None
            for cand in getattr(resp, "candidates", []) or []:
                for part in getattr(cand.content, "parts", []) or []:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        out_img = Image.open(io.BytesIO(inline.data)).convert("RGB")
                        break
                if out_img:
                    break
            if out_img is None:
                log(f"    ⚠️ 대표이미지 응답 없음: {name} (모델명 확인 필요)")
                return False
            shutil.copy(f, os.path.join(backup, name))   # 원본 백업
            save_name = os.path.splitext(f)[0] + ".jpg"
            # AI가 놓친 모서리 로고/워터마크를 배경색으로 덮어 마무리 20260901
            # .env 의 MAIN_IMAGE_CORNER_CLEAN=off 로 끌 수 있음
            if str(os.getenv("MAIN_IMAGE_CORNER_CLEAN", "on")).lower() not in ("off", "0", "false"):
                try:
                    out_img = _erase_corner_marks(out_img)
                except Exception:
                    pass
            out_img.save(save_name, quality=95)
            if save_name != f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
            return True
        except Exception as e:
            log(f"    ⚠️ 대표이미지 변환 실패 {name}: {e}")
            return False

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_one, f): f for f in todo}
        for fut in as_completed(futures):
            try:
                if fut.result():
                    done += 1
            except Exception:
                pass
    log(f"    🎨 대표이미지 스튜디오 변환: {done}장 (스타일={style}, 동시 {workers}장)")
    return {"done": done, "style": style}
