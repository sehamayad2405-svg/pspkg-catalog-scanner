# PSPKG public catalogue scanner

Scans public PSPKG HTML pages and produces a JSON catalogue using Pegasus DL's published `packages` / `downloadLinks` format. This is an independent project, not affiliated with PSPKG or Pegasus.

## Feed

Add this URL as a custom JSON source in Pegasus DL+:

https://raw.githubusercontent.com/sehamayad2405-svg/pspkg-catalog-scanner/main/docs/catalog.json

The feed is an adapter, not a new PS5 browser. Import and download behavior in Pegasus DL+ still needs testing on the console. A third-party provider link may require manual browser verification or may be unsupported. Do not assume every package supports firmware 13.60.

The first live scan found 6 tool/app listings with public links. The sampled game download pages display "Complete the check below" / "Awaiting verification"; the scanner does not bypass that check and cannot publish those games as ready downloads. This means the current feed is useful for publicly linked tools, not a complete downloadable games source.

## What it does

- Reads public PS4/PS5 listings and the PS5 tools section.
- Extracts names, images, title IDs where present, source pages and explicit public download links.
- Follows each detail page's public download-page link, with a bounded request budget.
- Excludes unresolved entries from the download catalogue; keeps them in `docs/index.json` with their status.
- Records HTTP failures and unresolved counts in `docs/report.json`.
- Uses a minimum one-second delay between requests. No game files are downloaded.
- Stops at HTTP access errors. It does not log in, bypass CAPTCHA, extract secrets, or manufacture provider URLs.
- Refreshes daily with GitHub Actions; manual refresh is available in Actions.

## Run

Python 3.10+; no dependencies:

```sh
python -m unittest -v
python scanner.py --max-pages 30 --delay 1.5
python scanner.py --sections tools --max-pages 12
python scanner.py --seed 'https://pspkg.com/ps5/tool?slug=fpkgi' --max-pages 4
```

`--max-pages` includes public download pages. Each run is a bounded snapshot, not a claim to index the whole site. Increase the budget up to 1000 for broader scans. Existing JSON is preserved if no detail pages can be parsed. JSON-LD metadata, ordinary HTML headings and explicit download anchors are supported; links available only after JavaScript execution are not resolved.

Only use links and content you are authorized to obtain. The repository contains source code, public listing metadata and links, not game binaries or credentials.

## Outputs

| File | Purpose |
|---|---|
| `docs/catalog.json` | Pegasus-shaped packages with discovered download links |
| `docs/index.json` | All parsed entries, including unresolved listings |
| `docs/report.json` | Scan counts and errors |

## License

MIT for the scanner code. Third-party metadata, artwork and linked content belong to their respective owners.
