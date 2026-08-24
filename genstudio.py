# -*- coding: utf-8 -*-
# genstudio.py : 대표이미지를 Gemini 이미지 모델로 '스튜디오 배경'으로 바꾸기 (테스트판)
#   - 제품은 그대로 두고 배경만 교체하도록 지시
#   - 두 스타일: 프로 스튜디오 / 미니멀 마블
#   - 테스트로 각 대표이미지 폴더에서 앞 MAX_TEST장만 처리 → '_스튜디오' 폴더에 저장
import os, sys, io, glob
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass
import warnings; warnings.filterwarnings("ignore")
from PIL import Image

MAX_TEST = 2  # 폴더당 테스트 장수 (확인되면 늘림)

STYLES = {
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
BASE_RULE = (
    " Keep the PRODUCT EXACTLY the same: identical shape, color, texture, proportions, logo and details. "
    "Do not redraw, add, or remove any product part. Photorealistic, high resolution, centered composition. "
    "Return a single edited image."
)

def _load_env(path):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def run():
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(base, "webapp", ".env")); load_dotenv(os.path.join(base, ".env"))
    except ImportError:
        _load_env(os.path.join(base, "webapp", ".env")); _load_env(os.path.join(base, ".env"))

    try:
        import google.generativeai as genai
    except ImportError:
        print("[중단] google-generativeai 없음 (webapp\\.venv312 로 실행해야 함)"); return
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("[중단] GEMINI_API_KEY 없음"); return
    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    print("이미지 모델:", model_name)
    model = genai.GenerativeModel(model_name)

    cwd = os.getcwd()
    folders = [d for d in glob.glob(os.path.join(cwd, "*", "대표이미지")) if os.path.isdir(d)]
    if len(sys.argv) > 1:
        folders = [sys.argv[1].strip().strip('"').rstrip("\\/")]
    if not folders:
        print("[중단] '대표이미지' 폴더 없음"); return

    for folder in folders:
        imgs = []
        for ext in ("jpg","jpeg","png","webp"):
            imgs += [f for f in glob.glob(os.path.join(folder, f"*.{ext}"))
                     if os.path.dirname(f) == folder]
        imgs = sorted(imgs)[:MAX_TEST]
        prod = os.path.basename(os.path.dirname(folder))
        print(f"\n▶ {prod} : 테스트 {len(imgs)}장")
        for f in imgs:
            try:
                src = Image.open(f).convert("RGB")
            except Exception as e:
                print("   열기 실패:", e); continue
            for style, desc in STYLES.items():
                out_dir = os.path.join(folder, "_스튜디오", style)
                os.makedirs(out_dir, exist_ok=True)
                try:
                    resp = model.generate_content([desc + BASE_RULE, src])
                    saved = False
                    for cand in getattr(resp, "candidates", []) or []:
                        for part in getattr(cand.content, "parts", []) or []:
                            inline = getattr(part, "inline_data", None)
                            if inline and getattr(inline, "data", None):
                                out = Image.open(io.BytesIO(inline.data)).convert("RGB")
                                name = os.path.splitext(os.path.basename(f))[0] + ".jpg"
                                out.save(os.path.join(out_dir, name), quality=95)
                                print(f"   ✅ [{style}] {os.path.basename(f)}")
                                saved = True; break
                        if saved: break
                    if not saved:
                        print(f"   ⚠️ [{style}] 이미지 응답 없음 (모델이 이미지 출력 안 함)")
                except Exception as e:
                    print(f"   ⚠️ [{style}] 실패: {e}")
    print("\n완료. 각 대표이미지 폴더의 _스튜디오\\{스타일}\\ 확인")

if __name__ == "__main__":
    try: run()
    except Exception:
        import traceback; traceback.print_exc()
    try: input("\n=== 엔터를 누르면 창이 닫힙니다 ===")
    except Exception: pass
