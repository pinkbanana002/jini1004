# -*- coding: utf-8 -*-
# 완료 이관 최종 수정: reindex 제거, 상품등록목록 값을 그대로 완료에 append
import io
p = r"webapp/modules/stage2_cells/09_cell_10.py"
s = io.open(p, encoding="utf-8").read()

OLD = '''        _dv=done_sheet.get_all_values()
        _dh=[c for c in (_dv[0] if _dv else []) if str(c).strip()!=""]
        if not _dh:
            _dh=target_df.columns.tolist()
            done_sheet.append_row(_dh)
        _al=target_df.reindex(columns=_dh, fill_value="")
        done_sheet.append_rows(_al.astype(str).values.tolist())'''

NEW = '''        if len(done_sheet.get_all_values()) == 0:
            done_sheet.append_row(target_df.columns.tolist())
        done_sheet.append_rows(target_df.astype(str).values.tolist())'''

if "target_df.astype(str).values.tolist()" in s and "reindex" not in s:
    print("[SKIP] 이미 적용됨")
elif OLD in s:
    io.open(p, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
    print("[OK] 수정 완료")
else:
    print("[NOTFOUND] 대상 블록 못 찾음")
