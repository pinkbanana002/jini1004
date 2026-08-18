# -*- coding: utf-8 -*-
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
c = Credentials.from_service_account_file("webapp/credentials.json", scopes=SCOPES)
gc = gspread.authorize(c)
ws = gc.open("지니) 로켓 자동등록_사본만들기해주세요의 사본").worksheet("상품등록목록")

# 수식 결과값으로 읽기 (get_all_records)
df = pd.DataFrame(ws.get_all_records())
df = df[df["변환상품명"] != ""]

print("전체행:", len(df))
print("\n=== 전체옵션명 40행 (수식 결과) ===")
if "전체옵션명" in df.columns:
    for i, v in enumerate(df["전체옵션명"].tolist()):
        print(f"  {i+1}: {v}")
    print("\n전체옵션명 종류:", df["전체옵션명"].nunique())
else:
    print("전체옵션명 열 없음")

print("\n=== 한글 옵션명 40행 ===")
if "한글 옵션명" in df.columns:
    print("한글옵션명 종류:", df["한글 옵션명"].nunique())
    print("샘플:", df["한글 옵션명"].tolist()[:5])
