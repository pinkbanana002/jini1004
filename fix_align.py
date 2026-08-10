# -*- coding: utf-8 -*-
p=r"webapp/modules/stage2_cells/09_cell_10.py"
s=open(p,encoding="utf-8").read()
OLD='        done_sheet.append_rows(target_df.values.tolist()) '
NEW='        _dv=done_sheet.get_all_values()\n        _dh=[c for c in (_dv[0] if _dv else []) if str(c).strip()!=""]\n        if not _dh:\n            _dh=target_df.columns.tolist()\n            done_sheet.append_row(_dh)\n        _al=target_df.reindex(columns=_dh, fill_value="")\n        done_sheet.append_rows(_al.astype(str).values.tolist())'
if "reindex" in s: print("SKIP")
elif OLD in s:
    open(p,"w",encoding="utf-8").write(s.replace(OLD,NEW,1)); print("OK")
else: print("NOTFOUND")
