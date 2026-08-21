# -*- coding: utf-8 -*-
# banner_filter.py (수동 테스트용) - 실제 로직은 webapp/modules/detail_image_filter.py 와 동일
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8")
except: pass

# 테스트할 상세페이지 폴더 (인자 없이 실행하면 이 폴더를 처리)
DEFAULT_FOLDER = r"C:\Users\Jini\Desktop\대량클로드_로켓배송_자동화\몰투데이 새로운 실리콘 발가락 및 발바닥 기능 운동 보조기구, 다리 근육 및 체형을 아름답게 만들어주는 쉘형 아치 트레이너\상세페이지"

def _load_env(path):
    if not os.path.exists(path): return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(base, "webapp", ".env")); load_dotenv(os.path.join(base, ".env"))
    except ImportError:
        _load_env(os.path.join(base, "webapp", ".env")); _load_env(os.path.join(base, ".env"))

    sys.path.insert(0, os.path.join(base, "webapp"))
    try:
        from modules.detail_image_filter import process_folder
    except Exception as e:
        print("[중단] 모듈 로드 실패:", e)
        import traceback; traceback.print_exc()
        return

    folder = sys.argv[1].strip().strip('"').rstrip("\\/") if len(sys.argv) > 1 else DEFAULT_FOLDER
    print("대상 폴더:", folder)
    if not os.path.isdir(folder):
        print("[중단] 폴더가 없습니다. 경로 확인."); return
    process_folder(folder)
    print("\n완료.")

if __name__ == "__main__":
    try: main()
    except Exception:
        import traceback; traceback.print_exc()
    try: input("\n=== 엔터를 누르면 창이 닫힙니다 ===")
    except Exception: pass
