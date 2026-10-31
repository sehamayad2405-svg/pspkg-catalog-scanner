"""Open PSPKG pages flagged for manual verification in the user's Chrome profile."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "docs" / "index.json"


def find_chrome():
    candidates = [
        shutil.which("chrome"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    return next((Path(item) for item in candidates if item and Path(item).is_file()), None)


def console_text(value):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return str(value).encode(encoding, errors="replace").decode(encoding, errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Open pages that need your manual verification in Chrome.")
    parser.add_argument("--index", type=Path, default=INDEX, help="Scanner index JSON (default: docs/index.json)")
    parser.add_argument("--limit", type=int, help="Open at most this many pages")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    chrome = find_chrome()
    if not chrome:
        sys.exit("Chrome was not found. Install Chrome or add chrome.exe to PATH.")

    try:
        index = json.loads(args.index.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"Cannot read {args.index}: {exc}")

    pages = []
    seen = set()
    for entry in index.get("entries", []):
        target = entry.get("pageUrl", "")
        parsed = urlsplit(target)
        if (entry.get("status") == "manual_verification_required" and
                parsed.scheme == "https" and parsed.hostname == "pspkg.com" and target not in seen):
            pages.append((entry.get("title", "Untitled"), target))
            seen.add(target)

    if args.limit is not None:
        pages = pages[:args.limit]
    if not pages:
        print("No PSPKG pages are currently marked as requiring manual verification.")
        return

    print(f"Found {len(pages)} page(s). Chrome will use your normal profile; complete any check yourself.")
    for number, (title, target) in enumerate(pages, start=1):
        print(f"\n[{number}/{len(pages)}] {console_text(title)}\n{target}")
        subprocess.Popen([str(chrome), target], close_fds=True)
        if number < len(pages):
            try:
                if input("Complete the page, then press Enter for the next one (q to stop): ").strip().lower() == "q":
                    break
            except EOFError:
                break
    print("Finished. The helper does not solve or submit verification challenges.")


if __name__ == "__main__":
    main()
