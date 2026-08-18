# -*- coding: utf-8 -*-
"""
견적서가 40행 -> 10행으로 주는 원인 진단.
07_cell_9 와 똑같은 방식으로 src_data 개수를 확인.
실행: webapp\.venv312\Scripts\python.exe 진단.py
"""
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
c = Credentials.from_service_account_file("webapp/credentials.json", scopes=SCOPES)
gc = gspread.authorize(c)

ws = gc.open("지니) 로켓 자동등록_사본만들기해주세요의 사본").worksheet("상품등록목록")

# 07_cell_9 와 동일하게 읽기
raw_df = pd.DataFrame(ws.get_all_records())
raw_df = raw_df[raw_df["변환상품명"] != ""]

print("=" * 50)
print("get_all_records 로 읽은 전체행:", len(raw_df))
print("변환상품명 종류:", raw_df["변환상품명"].nunique())

pn = "몰투데이 여성 하이웨이스트 3부 숏레깅스 바이커쇼츠"
src = raw_df[raw_df["변환상품명"].str.strip() == pn]
print("\n07_cell_9 필터 후 src_data 개수:", len(src))

if "옵션2" in raw_df.columns:
    print("\n옵션2(사이즈) 분포:")
    print(src["옵션2"].value_counts().to_dict())
if "옵션1" in raw_df.columns:
    print("\n옵션1(색상) 분포:")
    print(src["옵션1"].value_counts().to_dict())

# get_all_records 가 중복 헤더 때문에 행을 날리는지 체크
print("\n헤더(컬럼) 목록:")
print(list(raw_df.columns))
# 중복 헤더 확인
from collections import Counter
dup = [h for h, cnt in Counter(raw_df.columns).items() if cnt > 1]
print("\n중복된 헤더:", dup if dup else "없음")
