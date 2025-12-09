def zfill_code_new(raw, pad):
    s = str(raw).strip()
    try:
        num = float(s)
        if num.is_integer():
            s = str(int(num))
    except Exception:
        pass
    if s.isdigit():
        s = s.lstrip('0') or '0'
    return s

cases = ['009','021','21','221','000','00','0',' 054 ','54.0']
for c in cases:
    print(f"{c!r} -> {zfill_code_new(c,3)!r}")
