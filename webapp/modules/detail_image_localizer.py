# -*- coding: utf-8 -*-
"""
detail_image_localizer.py

상세페이지 이미지(1688/알리 등에서 받은 원본 detail_XXX.jpg)에 박혀 있는
중국어 오버레이 텍스트를 자동으로 처리하는 모듈.

지원 모드 (옵션으로 선택 가능):
  - "remove"    : 텍스트 영역을 배경과 자연스럽게 합성해서 지움 (OpenCV inpainting)
  - "translate" : 텍스트 영역을 한글 번역으로 교체 (배경색 추정 + PIL 텍스트 렌더링)
  - "none"      : 아무 처리도 하지 않음 (원본 그대로 반환) — 파이프라인 스위치 끄기용

텍스트 검출 + 번역은 Gemini Vision 한 번의 호출로 같이 처리한다.
(프로젝트가 이미 GEMINI_API_KEY / google.generativeai 를 쓰고 있으므로 별도 OCR
 라이브러리(PaddleOCR/EasyOCR) 의존성을 추가하지 않기 위한 선택.)

의존 패키지 (requirements.txt에 없다면 추가 필요):
    google-generativeai
    opencv-python
    pillow
    numpy
    python-dotenv   (프로젝트에서 이미 쓰고 있다면 생략 가능)

.env 설정값:
    GEMINI_API_KEY=...                (이미 있음)
    GEMINI_VISION_MODEL=gemini-2.5-flash   (프로젝트에서 실제 쓰는 모델명으로 맞춰서 조정)
    DETAIL_IMAGE_TEXT_MODE=translate       (remove | translate | none 중 기본값)
    DETAIL_IMAGE_FONT_PATH=../fonts/NotoSansKR-Bold.ttf   (프로젝트 fonts/ 폴더의 한글 폰트 경로)
"""

import os
import re
import json
import argparse
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
load_dotenv()

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger("detail_image_localizer")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

DEFAULT_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
DEFAULT_MODE = os.getenv("DETAIL_IMAGE_TEXT_MODE", "translate")  # remove | translate | none
DEFAULT_FONT_PATH = os.getenv("DETAIL_IMAGE_FONT_PATH", "")

_GEMINI_CONFIGURED = False


def _ensure_gemini():
    global _GEMINI_CONFIGURED
    if genai is None:
        raise RuntimeError(
            "google-generativeai 패키지가 설치되어 있지 않습니다. "
            "pip install google-generativeai 로 설치하세요."
        )
    if not _GEMINI_CONFIGURED:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(".env 에 GEMINI_API_KEY 가 설정되어 있지 않습니다.")
        genai.configure(api_key=api_key)
        _GEMINI_CONFIGURED = True


# ---------------------------------------------------------------------------
# 1. Gemini로 텍스트 영역 검출 + 번역을 한 번에 요청
# ---------------------------------------------------------------------------

_PROMPT = """\
이 이미지는 한국 쿠팡 상세페이지에 쓸 상품 이미지다. 이미지 위에 오버레이된 중국어(간체/번체)
텍스트를 찾아 한국어로 바꾸기 위한 정보를 순수 JSON 배열로만 응답해라(설명/코드펜스 금지).

규칙:
1) 한 덩어리로 보이는 문구(같은 배너/라벨/줄묶음)는 '하나의 블록'으로 묶어서 처리해라. 글자 하나하나 쪼개지 마라.
2) text_ko 는 상세페이지에 어울리는 '자연스럽고 완성된 짧은 한국어 마케팅 문구'로. 직역투/오타 금지.
   (예: "密集按摩点+磁石点位" → "촘촘한 마사지 돌기 + 자석 지압", "邵氏50° 加强型" → "쇼어 경도 50° 강화형")
3) 화면의 중국어를 하나도 빠뜨리지 마라. 작은 알약모양 라벨/캡션/표 안 글자까지 전부 찾아라.
4) 의미를 알 수 없는 조각·깨진 글자·워터마크·장식용 큰 글자처럼 번역 가치가 없는 것은
   text_ko 를 빈 문자열 "" 로 둬라. (그 부분은 배경으로 덮어 '지워'진다)
5) box_1000 은 해당 중국어 글자 전체를 확실히 감싸도록(약간 넉넉하게) 잡아라. 글자가 삐져나오면 안 된다.

형식:
[
  {"text_original":"원문", "text_ko":"자연스러운 한국어 또는 빈문자열", "box_1000":[ymin,xmin,ymax,xmax]}
]
box_1000 은 가로/세로 각각 0~1000 정규화값. 텍스트 없으면 [] 반환.
"""


def analyze_text_regions(image_path: str, model_name: str = DEFAULT_MODEL) -> List[Dict]:
    """Gemini Vision으로 이미지 내 중국어 텍스트 박스 + 한글 번역을 검출한다."""
    _ensure_gemini()
    model = genai.GenerativeModel(model_name)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"

    response = model.generate_content(
        [
            {"mime_type": mime, "data": image_bytes},
            _PROMPT,
        ]
    )

    raw = (response.text or "").strip()
    # 코드펜스 제거 (프로젝트 stage1.py 파서 관례와 동일하게 처리)
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        regions = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Gemini 응답 JSON 파싱 실패, raw 앞 200자: %s", raw[:200])
        return []

    if not isinstance(regions, list):
        return []
    return regions


def _box_1000_to_pixels(box_1000, width: int, height: int):
    ymin, xmin, ymax, xmax = box_1000
    x1 = int(xmin / 1000 * width)
    y1 = int(ymin / 1000 * height)
    x2 = int(xmax / 1000 * width)
    y2 = int(ymax / 1000 * height)
    # 살짝 여유를 둬서 글자 테두리까지 확실히 덮는다
    pad_x = max(2, int((x2 - x1) * 0.03))
    pad_y = max(2, int((y2 - y1) * 0.08))
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)
    return x1, y1, x2, y2


# ---------------------------------------------------------------------------
# 2. remove 모드 — OpenCV inpainting
# ---------------------------------------------------------------------------

def remove_text_regions(image_bgr: np.ndarray, regions: List[Dict]) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for r in regions:
        box = r.get("box_1000")
        if not box or len(box) != 4:
            continue
        x1, y1, x2, y2 = _box_1000_to_pixels(box, w, h)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

    if not mask.any():
        return image_bgr

    # INPAINT_TELEA가 배너 같은 단순 배경에서 자연스러운 편
    result = cv2.inpaint(image_bgr, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
    return result


# ---------------------------------------------------------------------------
# 3. translate 모드 — 배경색 추정 후 한글 텍스트 렌더링
# ---------------------------------------------------------------------------

def _sample_background_color(image_bgr: np.ndarray, x1, y1, x2, y2) -> tuple:
    """박스 테두리 바로 바깥 픽셀들을 샘플링해서 배경색을 추정한다."""
    h, w = image_bgr.shape[:2]
    margin = 4
    samples = []

    top = image_bgr[max(0, y1 - margin):y1, x1:x2]
    bottom = image_bgr[y2:min(h, y2 + margin), x1:x2]
    left = image_bgr[y1:y2, max(0, x1 - margin):x1]
    right = image_bgr[y1:y2, x2:min(w, x2 + margin)]

    for patch in (top, bottom, left, right):
        if patch.size > 0:
            samples.append(patch.reshape(-1, 3))

    if not samples:
        return (255, 255, 255)  # fallback: 흰색

    all_pixels = np.concatenate(samples, axis=0)
    median_bgr = np.median(all_pixels, axis=0)
    b, g, r = median_bgr
    return (int(r), int(g), int(b))  # PIL은 RGB


def _fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str, box_w: int, box_h: int) -> ImageFont.FreeTypeFont:
    """박스 크기에 맞는 최대 폰트 크기를 이진 탐색으로 찾는다."""
    lo, hi = 6, max(6, box_h)
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            font = ImageFont.truetype(font_path, mid) if font_path else ImageFont.load_default()
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= box_w * 0.92 and th <= box_h * 0.85:
            best = font
            lo = mid + 1
        else:
            hi = mid - 1
    return best or ImageFont.load_default()


def translate_text_regions(
    image_bgr: np.ndarray, regions: List[Dict], font_path: str = DEFAULT_FONT_PATH
) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    pil_img = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    for r in regions:
        box = r.get("box_1000")
        text_ko = (r.get("text_ko") or "").strip()
        if not box or len(box) != 4:
            continue

        x1, y1, x2, y2 = _box_1000_to_pixels(box, w, h)
        box_w, box_h = x2 - x1, y2 - y1
        if box_w <= 0 or box_h <= 0:
            continue

        pad = int(max(x2 - x1, y2 - y1) * 0.15)
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        bg_color = _sample_background_color(image_bgr, x1, y1, x2, y2)
        draw.rectangle([x1, y1, x2, y2], fill=bg_color)

        # 번역문이 없으면(의미없는 조각) 배경으로 덮어 '지우기'만 하고 끝
        if not text_ko:
            continue

        # 배경 밝기에 따라 텍스트 색(검/흰) 자동 선택
        brightness = sum(bg_color) / 3
        text_color = (30, 30, 30) if brightness > 140 else (245, 245, 245)

        font = _fit_font(draw, text_ko, font_path, box_w, box_h)
        tb = draw.textbbox((0, 0), text_ko, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = x1 + (box_w - tw) / 2
        ty = y1 + (box_h - th) / 2
        draw.text((tx, ty), text_ko, font=font, fill=text_color)

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ---------------------------------------------------------------------------
# 4. 메인 진입점
# ---------------------------------------------------------------------------

def process_detail_image(
    image_path: str,
    mode: str = DEFAULT_MODE,
    output_path: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    font_path: str = DEFAULT_FONT_PATH,
) -> str:
    """
    detail 이미지 1장을 처리한다.
    mode: "remove" | "translate" | "none"
    반환값: 저장된 파일 경로
    """
    if mode not in ("remove", "translate", "none"):
        raise ValueError(f"알 수 없는 mode: {mode} (remove/translate/none 중 선택)")

    output_path = output_path or image_path

    if mode == "none":
        if output_path != image_path:
            import shutil
            shutil.copy(image_path, output_path)
        return output_path

    regions = analyze_text_regions(image_path, model_name=model_name)
    if not regions:
        logger.info("[%s] 중국어 텍스트 미검출 — 원본 유지", os.path.basename(image_path))
        if output_path != image_path:
            import shutil
            shutil.copy(image_path, output_path)
        return output_path

    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"이미지를 열 수 없습니다: {image_path}")

    if mode == "remove":
        result = remove_text_regions(image_bgr, regions)
    else:  # translate
        result = translate_text_regions(image_bgr, regions, font_path=font_path)

    cv2.imwrite(output_path, result)
    logger.info(
        "[%s] 처리 완료 (mode=%s, 텍스트 %d건)",
        os.path.basename(image_path), mode, len(regions),
    )
    return output_path


def process_detail_images_in_folder(
    folder: str,
    mode: str = DEFAULT_MODE,
    output_folder: Optional[str] = None,
    pattern: str = r"detail_\d+\.(jpg|jpeg|png)$",
) -> List[str]:
    """
    폴더 안의 detail_XXX.jpg 파일들을 전부 처리한다.
    output_folder 를 지정하지 않으면 원본을 덮어쓴다(주의).
    """
    output_folder = output_folder or folder
    os.makedirs(output_folder, exist_ok=True)

    results = []
    for fname in sorted(os.listdir(folder)):
        if not re.search(pattern, fname, flags=re.IGNORECASE):
            continue
        src = os.path.join(folder, fname)
        dst = os.path.join(output_folder, fname)
        try:
            out = process_detail_image(src, mode=mode, output_path=dst)
            results.append(out)
        except Exception as e:
            logger.error("처리 실패 [%s]: %s", fname, e)
    return results


# ---------------------------------------------------------------------------
# CLI (독립 실행 테스트용)
# ---------------------------------------------------------------------------

def _main():
    parser = argparse.ArgumentParser(description="상세페이지 이미지 중국어 텍스트 처리")
    parser.add_argument("--folder", required=True, help="detail_XXX.jpg 들이 있는 폴더")
    parser.add_argument("--mode", choices=["remove", "translate", "none"], default=DEFAULT_MODE)
    parser.add_argument("--output", default=None, help="결과 저장 폴더 (미지정 시 원본 덮어씀)")
    args = parser.parse_args()

    results = process_detail_images_in_folder(args.folder, mode=args.mode, output_folder=args.output)
    print(f"완료: {len(results)}개 파일 처리됨 (mode={args.mode})")


if __name__ == "__main__":
    _main()
