#!/usr/bin/env python3
"""
AutoFill 同時実行・リソース監査用の参照箇所を一覧する補助スクリプト。
実装は変更しない。rg（ripgrep）または組み込みのファイル検索で該当行を出力する。
使い方: python scripts/audit-autofill-concurrency-refs.py
"""
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS = [
    ("MAX_ACTIVE_SESSIONS|count_running_jobs", "app.py", "utils.py", "render.yaml", "diagnostics"),
    ("threading\\.Thread|run_automation|/upload", "app.py"),
    ("prune_jobs|register_session|unregister_session|cleanup_user_session", "app.py"),
    ("wait_for|networkidle|set_default_timeout|launch\\(", "automation.py"),
    ("jobs\\[|jobs\\.get|jobs_lock", "app.py"),
    ("deque|MAX_JOB_LOGS|add_job_log", "app.py", "utils.py", "automation.py"),
]

def search_file(path: str, pattern: str) -> list[tuple[int, str]]:
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    out.append((i, line.rstrip()))
    except Exception as e:
        out.append((0, f"# error: {e}"))
    return out

def main():
    os.chdir(REPO_ROOT)
    for pattern, *rel_dirs in PATTERNS:
        print(f"\n## pattern: {pattern}")
        print("-" * 60)
        seen = set()
        for rel in rel_dirs:
            if os.path.isfile(rel):
                files = [rel]
            else:
                files = []
                for root, _, names in os.walk(rel):
                    for n in names:
                        if n.endswith(".py") or n.endswith(".yaml"):
                            files.append(os.path.join(root, n))
            for path in files:
                if path in seen or not os.path.isfile(path):
                    continue
                seen.add(path)
                hits = search_file(path, pattern)
                if hits:
                    print(f"  {path}")
                    for line_no, text in hits[:25]:
                        print(f"    {line_no}: {text[:90]}")
                    if len(hits) > 25:
                        print(f"    ... and {len(hits) - 25} more")
    print("\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
