p=r"webapp/modules/stage2_cells/09_cell_10.py"
s=open(p,encoding="utf-8").read()
OLD="    raw_data = worksheet.get_all_records(^)\n    df = pd.DataFrame(raw_data^)"
NEW="    _rv = worksheet.get_all_values(^)\n    df = pd.DataFrame(_rv[1:], columns=_rv[0]^) if _rv else pd.DataFrame(^)"
if "get_all_records" not in s: print("SKIP-already")
elif OLD in s:
    open(p,"w",encoding="utf-8").write(s.replace(OLD,NEW,1)); print("OK")
else: print("NOTFOUND")
