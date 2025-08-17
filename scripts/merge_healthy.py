#!/usr/bin/env python3
import sys
import os
from typing import List, Set


def read_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def write_lines(path: str, lines: List[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(f"{line}\n")


def merge_healthy(new_file: str, healthy_file: str) -> None:
    new_lines = [l for l in read_lines(new_file) if l.strip()]
    old_lines = [l for l in read_lines(healthy_file) if l.strip()]

    # Append + de-duplicate preserving order: old first, then new uniques
    seen: Set[str] = set()
    merged: List[str] = []
    for l in old_lines + new_lines:
        if l not in seen:
            seen.add(l)
            merged.append(l)

    write_lines(healthy_file, merged)
    print(f"Merged {len(new_lines)} new lines into {healthy_file}. Total unique lines: {len(merged)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: merge_healthy.py <new_results_file> <healthy_file>")
        sys.exit(1)
    merge_healthy(sys.argv[1], sys.argv[2])