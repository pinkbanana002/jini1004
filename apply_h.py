import io,ast
p=r"webapp/modules/stage2_cells/02_cell_6_2.py"
s=io.open(p,encoding="utf-8").read()
old=chr(10).join(["                if not h_val and g_val:","                    batch_updates.append({","                        \x27range\x27: rowcol_to_a1(current_row_num, h_idx + 1),","                        \x27values\x27: [[g_val]],","                    })","                    fill_count += 1","                    row[h_idx] = g_val"])
new=chr(10).join(["                if not h_val and g_val:","                    _kw = \x27기타헬스소품\x27 if \x27헬스\x27 in g_val else g_val","                    batch_updates.append({","                        \x27range\x27: rowcol_to_a1(current_row_num, h_idx + 1),","                        \x27values\x27: [[_kw]],","                    })","                    fill_count += 1","                    row[h_idx] = _kw"])
print("OK" if old in s else "NOTFOUND")
s=s.replace(old,new,1)
ast.parse(s)
io.open(p,"w",encoding="utf-8").write(s)
print("DONE")
