import os,re,pandas as pd,gspread
from oauth2client.service_account import ServiceAccountCredentials as C
from dotenv import load_dotenv
load_dotenv("webapp/.env")
k=re.search(r"/d/([\w-]+^)",os.getenv("GOOGLE_SHEET_URL")).group(1)
doc=gspread.authorize(C.from_json_keyfile_name("credentials.json",["https://www.googleapis.com/auth/drive"])).open_by_key(k)
rv=doc.worksheet("상품등록목록").get_all_values()
print("행수",len(rv))
df=pd.DataFrame(rv[1:],columns=rv[0]) if rv else pd.DataFrame()
print("shape",df.shape)
print("변환상품명있나","변환상품명" in df.columns)
t=df[df["변환상품명"]!=""] if "변환상품명" in df.columns else df
print("target행수",len(t))
print("첫행변환명",repr(t.iloc[0]["변환상품명"]) if len(t) else "없음")
