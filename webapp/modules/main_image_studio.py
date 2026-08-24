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
        "Replace ONLY the background with a clean professional e-commerce studio backdrop: "
        "soft seamless light-gray to white gradient, soft studio lighting, a subtle realistic "
        "contact shadow under the product."
    ),
    "미니멀마블": (
        "Replace ONLY the background with a minimal elegant white marble surface with soft natural "
        "lighting and a gentle realistic shadow, high-end e-commerce look."
    ),
}
_RULE = (
    " Keep the PRODUCT EXACTLY the same: identical shape, color, texture, proportions, logo and details. "
    "Do not redraw, add, or remove any product part. Photorealistic, high resolution, centered square composition. "
    "Return a single edited image."
)


def process_main_images(img_dir, log=print):
    """대표이미지 폴더 하나의 이미지들을 스튜디오 배경으로 변환(in-place, 원본은 _원본 백업)."""
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
    done = 0
    for f in imgs:
        name = os.path.basename(f)
        # 이미 처리된 것(_원본에 백업 있음)은 건너뜀
        if os.path.exists(os.path.join(backup, name)):
            continue
        try:
            src = Image.open(f).convert("RGB")
            resp = model.generate_content([desc + _RULE, src])
            out_img = None
            for cand in getattr(resp, "candidates", []) or []:
                for part in getattr(cand.content, "parts", []) or []:
                    inline = getattr(part, "inline_data", None)
                    if inline and getattr(inline, "data", None):
                        out_img = Image.open(io.BytesIO(inline.data)).convert("RGB")
                        break
                if out_img: break
            if out_img is None:
                log(f"    ⚠️ 대표이미지 응답 없음: {name} (모델명 확인 필요)")
                continue
            shutil.copy(f, os.path.join(backup, name))   # 원본 백업
            save_name = os.path.splitext(f)[0] + ".jpg"
            out_img.save(save_name, quality=95)
            if save_name != f and os.path.exists(f):
                try: os.remove(f)
                except Exception: pass
            done += 1
        except Exception as e:
            log(f"    ⚠️ 대표이미지 변환 실패 {name}: {e}")
    log(f"    🎨 대표이미지 스튜디오 변환: {done}장 (스타일={style})")
    return {"done": done, "style": style}
