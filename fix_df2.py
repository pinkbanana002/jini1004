p=r"webapp/modules/stage2_cells/09_cell_10.py"
s=open(p,encoding="utf-8").read()
s=s.replace("    raw_data = worksheet.get_all_records(^)", "    _rv = worksheet.get_all_values(^)")
s=s.replace("    df = pd.DataFrame(raw_data^)", "    df = pd.DataFrame(_rv[1:], columns=_rv[0]^) if _rv else pd.DataFrame(^)")
open(p,"w",encoding="utf-8").write(s)
print("DONE" if "get_all_records" not in s else "FAIL")
