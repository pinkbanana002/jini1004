# -*- coding: utf-8 -*-
# 상세이미지_배너판별.py
#   상세페이지 폴더(detail_XXX.jpg)를 훑어서 AI(Gemini)로 판단:
#     - 버릴 광고배너/타사브랜드  -> _제외배너 폴더로 이동
#     - 남길 깨끗한 상품사진      -> 그대로 둠
#   중국어 번역도 _판별결과.txt 에 함께 기록.
#   * 파일을 지우지 않고 '이동'만 하므로 안전합니다.
#
# 사용법:
#   상세페이지 폴더를 이 스크립트가 있는 폴더의 bat 위로 끌어다 놓거나,
#   .venv312\Scripts\python.exe 상세이미지_배너판별.py "폴더경로"
import os, sys, re, json, glob, shutil
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

from dotenv import load_dotenv
load_dotenv("webapp/.env"); load_dotenv(".env"); load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("[중단] google-generativeai 가 없습니다.  pip install google-generativeai")
    sys.exit(1)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("[중단] .env 에 GEMINI_API_KEY 가 없습니다. (webapp/.env 확인)")
    sys.exit(1)
genai.configure(api_key=API_KEY)
MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")

PROMPT = """\
이 이미지는 한국 쿠팡 상세페이지에 쓸 후보 이미지다. 아래 기준으로 판단하고 순수 JSON만 출력해라(코드펜스/설명 금지).

[버림 = drop:true]
- UMAY, WOSWEIR, SPG, adidas 등 어떤 상표/브랜드 로고라도 이미지에 있으면 버림
- 중국어 마케팅 문구가 이미지를 크게 덮는 광고 배너
- 공장/원청/OEM/ODM/판매량/아시안게임 등 홍보 문구가 들어간 이미지
[남김 = drop:false]
- 제품만 깔끔하게 보이는 사진 (배경 단순, 중국어가 없거나 위쪽 작은 소제목 정도)

JSON 형식:
{"drop": true, "reason": "짧은 이유(한국어)", "has_brand_logo": true, "chinese": [{"orig":"원문중국어","ko":"한국어번역"}]}
중국어가 없으면 "chinese": [] 로.
"""

def classify(path, model):
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    resp = model.generate_content([{"mime_type": mime, "data": data}, PROMPT])
    raw = (resp.text or "").strip()
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"drop": False, "reason": "판독실패(안전하게 보관)", "has_brand_logo": False, "chinese": []}

def main():
    DEFAULT_FOLDER = r"C:\Users\Jini\Desktop\대량클로드_로켓배송_자동화\몰투데이 8자형 탄성 밴드 여성용 등 운동 스트레칭 어깨 확장 요가 MD-01 대형 실리콘 텐셔너\상세페이지"
    folder = sys.argv[1].strip().strip('"') if len(sys.argv) > 1 else DEFAULT_FOLDER
    folder = folder.rstrip("\\/")
    if not os.path.isdir(folder):
        print(f"[중단] 폴더가 아닙니다: {folder}"); return

    files = sorted(glob.glob(os.path.join(folder, "detail_*.jpg")) +
                   glob.glob(os.path.join(folder, "detail_*.png")) +
                   glob.glob(os.path.join(folder, "detail_*.jpeg")))
    if not files:
        print(f"[중단] {folder} 에 detail_*.jpg 가 없습니다."); return
    print(f"대상 폴더: {folder}")
    print(f"이미지 {len(files)}장 판별 시작...\n")

    drop_dir = os.path.join(folder, "_제외배너")
    os.makedirs(drop_dir, exist_ok=True)
    model = genai.GenerativeModel(MODEL)

    report = []
    kept = dropped = 0
    for i, f in enumerate(files, 1):
        name = os.path.basename(f)
        try:
            r = classify(f, model)
        except Exception as e:
            print(f"  [{i}/{len(files)}] {name} → 오류(보관): {e}")
            report.append(f"[보관-오류] {name} : {e}")
            kept += 1
            continue
        drop = bool(r.get("drop"))
        reason = r.get("reason", "")
        brand = " (타사브랜드!)" if r.get("has_brand_logo") else ""
        trans = r.get("chinese", []) or []
        trans_txt = "  ".join(f"{t.get('orig','')}→{t.get('ko','')}" for t in trans)

        if drop:
            shutil.move(f, os.path.join(drop_dir, name))
            dropped += 1
            print(f"  [{i}/{len(files)}] 🗑️ 버림  {name}{brand} : {reason}")
            report.append(f"[버림]{brand} {name} : {reason}\n     번역: {trans_txt}")
        else:
            kept += 1
            print(f"  [{i}/{len(files)}] ✅ 남김  {name} : {reason}")
            report.append(f"[남김] {name} : {reason}\n     번역: {trans_txt}")

    with open(os.path.join(folder, "_판별결과.txt"), "w", encoding="utf-8") as fp:
        fp.write("\n".join(report))

    print(f"\n[완료] 남김 {kept}장 / 버림 {dropped}장")
    print(f" - 버린 이미지: {drop_dir}")
    print(f" - 판별/번역 기록: {os.path.join(folder, '_판별결과.txt')}")

if __name__ == "__main__":
    main()
