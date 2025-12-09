from core.services.navidad_loader import zfill_code

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
    out = zfill_code(raw, pad)
    print(f"raw={raw!r:8} pad={pad} -> {out!r}")

print('\nPad 0 examples:')
for raw in ['21', '021', '221', '00']:
    print(raw, '->', zfill_code(raw, 0))
