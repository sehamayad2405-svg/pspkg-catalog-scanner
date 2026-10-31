"""Read public PSPKG pages and export discovered links; never invent download URLs."""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BASE = "https://pspkg.com/"
SECTIONS = {"ps5": "ps5/", "ps4": "ps4/", "tools": "ps5/ps5-tools", "arabic": "arabic-games/?filters%5B%5D=ps5"}
FILE = re.compile(r"\.(?:pkg|fpkg|ffpkg|ffpfs|ffpfsc|exfat|elf|zip|7z|rar)(?:$|[?#])", re.I)
TITLE_ID = re.compile(r"\b(?:PPSA|CUSA|[A-Z]{4})\d{5}\b")
DETAIL = re.compile(r"/(?:ps[345]|arabic-games)/(?!download-)[^/?]+-\d+\.html$")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def text(self):
        return " ".join(" ".join(c.text() if isinstance(c, Node) else c for c in self.children).split())

    def find(self, tag=None):
        for child in self.children:
            if isinstance(child, Node):
                if tag is None or child.tag == tag:
                    yield child
                yield from child.find(tag)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def url(value, base=BASE):
    parsed = urlsplit(urljoin(base, value or ""))
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))


def onsite(value):
    return urlsplit(value).hostname in {"pspkg.com", "www.pspkg.com"}


def canonical_page(value):
    """Normalize language variants so pagination is scanned only once."""
    parsed = urlsplit(value)
    path = parsed.path[3:] if parsed.path.startswith("/ar/") else parsed.path
    query = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True)
             if key.lower() != "lang" and not (key.lower() == "page" and val == "1")]
    return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(query, doseq=True), ""))


def detail(value):
    p = urlsplit(value)
    return onsite(value) and (bool(DETAIL.search(p.path)) or (p.path.endswith("/tool") and "slug=" in p.query))


def downloads(doc, page):
    found = {}
    for a in doc.find("a"):
        target = url(a.attrs.get("href"), page)
        if not target or target == page or target.endswith("#"):
            continue
        classes = a.attrs.get("class", "").lower()
        explicit = "download" in a.attrs or "download-btn" in classes or "dl-link" in classes
        if FILE.search(target) or (explicit and not onsite(target)):
            found[target] = {"name": a.text()[:100] or urlsplit(target).hostname, "url": target}
    return list(found.values())


def parse_page(html, page):
    doc = Document(html).root
    structured = []
    for script in doc.find("script"):
        if script.attrs.get("type") == "application/ld+json":
            try:
                value = json.loads(script.text())
                structured.extend(value if isinstance(value, list) else [value])
            except (ValueError, TypeError):
                pass
    meta = {m.attrs.get("property", m.attrs.get("name")): m.attrs.get("content", "") for m in doc.find("meta")}
    data = next((x for x in structured if isinstance(x, dict) and x.get("@type") in {"VideoGame", "SoftwareApplication", "Product"}), {})
    headings = list(doc.find("h1"))
    title = data.get("name") or (headings[0].text() if headings else meta.get("og:title", ""))
    image = data.get("image") or meta.get("og:image", "")
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")
    text = doc.text()
    ids = TITLE_ID.findall(text + " " + " ".join(a.attrs.get("href", "") for a in doc.find("a")))
    links = downloads(doc, page)
    next_pages, link_pages = [], []
    for a in doc.find("a"):
        target = url(a.attrs.get("href"), page)
        if not target or not onsite(target):
            continue
        target = canonical_page(target)
        if detail(target):
            next_pages.append(target)
        elif (urlsplit(target).path == urlsplit(page).path
              and re.search(r"(?:^|&)page=\d+(?:&|$)", urlsplit(target).query)):
            next_pages.append(target)
        elif "/download-" in urlsplit(target).path or "gp-dl-btn" in a.attrs.get("class", ""):
            link_pages.append(target)
    platform = ("PS4" if "/ps4/" in page else "PS5" if "/ps5/" in page else
                "PS5" if re.search(r"\bPS5\b", text, re.I) else
                "PS4" if re.search(r"\bPS4\b", text, re.I) else "Unknown")
    return {
        "title": str(title).strip(), "pageUrl": page, "platform": platform,
        "titleId": next((x for x in ids if x.startswith(("PPSA", "CUSA"))), ids[0] if ids else ""),
        "posterUrl": url(str(image), page) if image else "",
        "description": data.get("description") or meta.get("description", ""),
        "downloadLinks": links,
    }, list(dict.fromkeys(next_pages)), list(dict.fromkeys(link_pages))


class Fetcher:
    def __init__(self, delay=1.5, timeout=20):
        self.delay, self.timeout, self.last = delay, timeout, 0.0

    def get(self, target):
        if not onsite(target):
            raise ValueError("Only public PSPKG HTML pages are fetched")
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        request = Request(target, headers={"User-Agent": "PSPKG-Catalog-Scanner/1.0 (public HTML index; no downloads)"})
        with urlopen(request, timeout=self.timeout) as response:
            if not onsite(response.url):
                raise ValueError("Redirect left PSPKG")
            if "html" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Response is not HTML")
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("HTML page exceeds 4 MB limit")
            return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def package(entry):
    if not entry.get("title") or not entry.get("downloadLinks"):
        return None
    identity = sha256(entry["pageUrl"].encode()).hexdigest()[:12]
    return {
        "id": "pspkg-" + identity, "titleId": entry.get("titleId") or "",
        "title": entry["title"], "version": "", "author": "PSPKG listing",
        "category": "Homebrew" if "/tool?" in entry["pageUrl"] else entry["platform"],
        "description": ("Arabic localization listing. " if "Arabic" in entry.get("tags", []) else "")
                       + str(entry.get("description", "")) + "\nSource: " + entry["pageUrl"] + "\nFirmware compatibility not verified.",
        "posterUrl": entry.get("posterUrl", ""), "downloadLinks": entry["downloadLinks"],
    }


def scan(seeds, fetcher, max_pages=30):
    listing_queue = deque(x for x in seeds if not detail(x))
    detail_queue = deque(x for x in seeds if detail(x))
    seen, entries, errors, arabic_details = set(), {}, [], set()
    listing_budget = max(8, max_pages // 3)
    listing_count = 0
    while (listing_queue or detail_queue) and len(seen) < max_pages:
        if detail_queue and (listing_count >= listing_budget or not listing_queue):
            page = detail_queue.popleft()
        else:
            page = listing_queue.popleft()
            listing_count += 1
        if page in seen:
            continue
        seen.add(page)
        try:
            html = fetcher.get(page)
            entry, discovered, link_pages = parse_page(html, page)
            if detail(page):
                if page in arabic_details or "/arabic-games/" in urlsplit(page).path:
                    entry["tags"] = ["Arabic"]
                entries[page] = entry
                verification_required = False
                for target in link_pages[:3]:
                    if len(seen) >= max_pages:
                        break
                    if target in seen:
                        continue
                    seen.add(target)
                    try:
                        download_doc = Document(fetcher.get(target)).root
                        words = download_doc.text().lower()
                        verification_required |= any(x in words for x in [
                            "awaiting verification", "complete the check below", "captcha", "في انتظار التحقق",
                        ])
                        extra = downloads(download_doc, target)
                        entry["downloadLinks"] = list({x["url"]: x for x in entry["downloadLinks"] + extra}.values())
                    except (HTTPError, URLError, ValueError, TimeoutError, OSError) as exc:
                        errors.append({"url": target, "error": str(exc)})
                entry["status"] = ("links_found" if entry["downloadLinks"] else
                                   "manual_verification_required" if verification_required else "no_public_download_link")
            listing_pages = [x for x in discovered if not detail(x) and x not in seen]
            detail_pages = [x for x in discovered if detail(x) and x not in seen]
            if "/arabic-games" in urlsplit(page).path:
                arabic_details.update(detail_pages)
            for target in listing_pages:
                if target not in listing_queue:
                    listing_queue.append(target)
            for target in detail_pages:
                if target not in detail_queue:
                    detail_queue.append(target)
            print(f"[{len(seen)}/{max_pages}] {page}", flush=True)
        except (HTTPError, URLError, ValueError, TimeoutError, OSError) as exc:
            errors.append({"url": page, "error": str(exc)})
    return list(entries.values()), errors, len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", nargs="+", choices=SECTIONS, default=["arabic", "tools", "ps5", "ps4"])
    parser.add_argument("--seed", action="append", help="Public PSPKG listing/detail URL; repeatable")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--output", type=Path, default=Path("docs"))
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 1000 or args.delay < 1:
        parser.error("max-pages must be 1–1000; delay must be at least 1 second")
    seeds = args.seed or [BASE + SECTIONS[x] for x in args.sections]
    if any(not onsite(x) or not url(x) for x in seeds):
        parser.error("Seeds must be public http(s) PSPKG URLs")
    entries, errors, count = scan(seeds, Fetcher(args.delay), args.max_pages)
    if not entries:
        raise SystemExit("No detail pages parsed; existing output preserved")
    timestamp = datetime.now(timezone.utc).isoformat()
    packages = [p for e in entries if (p := package(e))]
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = {
        "index.json": {"generatedAt": timestamp, "entries": entries},
        "catalog.json": {"name": "PSPKG public links", "description": "Public links discovered from PSPKG HTML. File availability and firmware compatibility are not verified.", "packages": packages},
        "report.json": {"generatedAt": timestamp, "pagesAttempted": count, "detailPages": len(entries), "packagesWithLinks": len(packages), "unresolved": sum(not e["downloadLinks"] for e in entries), "manualVerificationRequired": sum(e["status"] == "manual_verification_required" for e in entries), "errors": errors},
    }
    for name, data in outputs.items():
        temp = args.output / (name + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(args.output / name)
    print(json.dumps(outputs["report.json"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
