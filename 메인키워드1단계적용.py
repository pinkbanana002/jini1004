"""
stage1.py 에 '메인키워드 1단계 자동채움' 을 넣는 스크립트.
실행:  webapp\.venv312\Scripts\python.exe 메인키워드1단계적용.py
"""
import io, ast

p = r'webapp/modules/stage1.py'
s = io.open(p, encoding='utf-8').read()

if 'idx_main_kw' in s:
    print("이미 적용됨")
    raise SystemExit

# 1) 메인키워드 열 찾기 추가
old1 = "            idx_trans_name = find_col(['\ubcc0\ud658\uc0c1\ud488\uba85'])"
new1 = "            idx_trans_name = find_col(['\ubcc0\ud658\uc0c1\ud488\uba85'])\n            idx_main_kw = find_col(['\uba54\uc778\ud0a4\uc6cc\ub4dc'])"

if old1 not in s:
    print("[1] \ub300\uc0c1 \ubabb\ucc3e\uc74c - \uc911\ub2e8")
    raise SystemExit
s = s.replace(old1, new1, 1)

# 2) ai_name 쓰는 곳에 메인키워드도 쓰기
old2 = (
    "                    col_letter = openpyxl.utils.get_column_letter(idx_trans_name + 1)\n"
    "                    updates.append({'range': f\"{col_letter}{row_num}\", 'values': [[ai_name]]})\n"
    "                    if idx_tags != -1 and ai_tags:"
)
new2 = (
    "                    col_letter = openpyxl.utils.get_column_letter(idx_trans_name + 1)\n"
    "                    updates.append({'range': f\"{col_letter}{row_num}\", 'values': [[ai_name]]})\n"
    "                    # \uba54\uc778\ud0a4\uc6cc\ub4dc \uc790\ub3d9\ucc44\uc6c0 20260816: \ubcc0\ud658\uc0c1\ud488\uba85(ai_name)\uc5d0 '\ud5ec\uc2a4' \uc788\uc73c\uba74\n"
    "                    # '\uae30\ud0c0\ud5ec\uc2a4\uc18c\ud488', \uc5c6\uc73c\uba74 \ubcc0\ud658\uc0c1\ud488\uba85 \uadf8\ub300\ub85c(\uac80\uc218\ub294 \uc218\ub3d9). 1\ub2e8\uacc4\uc5d0\uc11c \ubc14\ub85c \ucc44\uc6c0.\n"
    "                    if idx_main_kw != -1:\n"
    "                        _kw = '\uae30\ud0c0\ud5ec\uc2a4\uc18c\ud488' if '\ud5ec\uc2a4' in ai_name else ai_name\n"
    "                        col_letter = openpyxl.utils.get_column_letter(idx_main_kw + 1)\n"
    "                        updates.append({'range': f\"{col_letter}{row_num}\", 'values': [[_kw]]})\n"
    "                    if idx_tags != -1 and ai_tags:"
)

if old2 not in s:
    print("[2] \ub300\uc0c1 \ubabb\ucc3e\uc74c - \uc911\ub2e8")
    raise SystemExit
s = s.replace(old2, new2, 1)

ast.parse(s)  # \ubb38\ubc95\uac80\uc0ac
io.open(p, 'w', encoding='utf-8').write(s)
print("\uc644\ub8cc: \uba54\uc778\ud0a4\uc6cc\ub4dc 1\ub2e8\uacc4 \ucc44\uc6c0 \uc801\uc6a9\ub428")
verify = io.open(p, encoding='utf-8').read()
print("\uac80\uc99d idx_main_kw:", 'idx_main_kw' in verify)
print("\uac80\uc99d \ud5ec\uc2a4\uaddc\uce59:", "'\ud5ec\uc2a4' in ai_name" in verify)
