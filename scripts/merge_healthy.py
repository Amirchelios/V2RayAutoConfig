#!/usr/bin/env python3
import sys, os, tempfile, shutil

SCHEMES = (
    "vmess://","vless://","trojan://","ss://",
    "ssr://","hysteria://","hysteria2://","tuic://","socks://"
)

def read_lines(path, accept_all=False):
    lines = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                s = raw.strip()
                if not s:
                    continue
                if accept_all:
                    lines.append(s)
                else:
                    low = s.lower()
                    if low.startswith(SCHEMES):
                        lines.append(s)
    return lines

def merge(old_path, new_path, dest_path):
    old_lines = read_lines(old_path, accept_all=True)
    new_lines = read_lines(new_path, accept_all=False)

    seen = set()
    merged = []
    # قدیمی‌ها اول
    for ln in old_lines:
        key = ln.strip()
        if key and key not in seen:
            merged.append(key)
            seen.add(key)
    # بعد جدیدها
    for ln in new_lines:
        key = ln.strip()
        if key and key not in seen:
            merged.append(key)
            seen.add(key)

    # ایجاد دایرکتوری اگر وجود ندارد
    dest_dir = os.path.dirname(dest_path)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
    
    # نوشتن اتمیک
    tmp_dir = dest_dir if dest_dir else "."
    fd, tmp = tempfile.mkstemp(prefix=".healthy_", suffix=".tmp", dir=tmp_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for ln in merged:
                f.write(ln + "\n")
        shutil.move(tmp, dest_path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    print(f"[merge_healthy] old={len(old_lines)} new={len(new_lines)} merged={len(merged)}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/merge_healthy.py <new_results_file> <dest_file>")
        sys.exit(1)
    new_results = sys.argv[1]
    dest = sys.argv[2]
    old = dest if os.path.isfile(dest) else ""
    merge(old, new_results, dest)

if __name__ == "__main__":
    main()
