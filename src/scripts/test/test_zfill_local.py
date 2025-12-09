def zfill_code_local(raw, pad):
    s = str(raw).strip()
    try:
        num = float(s)
        if num.is_integer():
            s = str(int(num))
    except Exception:
        pass
    return s.zfill(pad) if (pad and s.isdigit()) else s

cases = [
    ("21", 0),
    ("21", 3),
    ("21.0", 3),
    ("221", 3),
    ("021", 3),
    ("0", 3),
    ("00", 3),
    (54, 3),
    (54.0, 3),
    (" 054 ", 3),
]

for raw, pad in cases:
    out = zfill_code_local(raw, pad)
    print(f"raw={raw!r:8} pad={pad} -> {out!r}")

print('\nPad 0 examples:')
for raw in ['21', '021', '221', '00']:
    print(raw, '->', zfill_code_local(raw, 0))
