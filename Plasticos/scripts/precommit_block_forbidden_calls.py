import os
import re
import sys

ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PLASTICOS = os.path.join(ROOT, "Plasticos")

FORBIDDEN = [
    r"\brequests\.",
    r"\bhttpx\.",
    r"\burllib3\.",
    r"\burllib\.request\b",
]

ALLOW_DIRS = {
    os.path.join(PLASTICOS, "l9_adapter"),
}

def is_allowed(path: str) -> bool:
    ap = os.path.abspath(path)
    for a in ALLOW_DIRS:
        if ap.startswith(os.path.abspath(a) + os.sep) or ap == os.path.abspath(a):
            return True
    return False

def main() -> int:
    bad = []
    for base, _, files in os.walk(PLASTICOS):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(base, fn)
            if is_allowed(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            for pat in FORBIDDEN:
                if re.search(pat, txt):
                    bad.append((path, pat))
    if bad:
        print("FORBIDDEN network call patterns found outside Plasticos/l9_adapter:")
        for p, pat in bad:
            print(f"- {p}  (pattern: {pat})")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
B) CI workflow to run replay tests (no clicking)
