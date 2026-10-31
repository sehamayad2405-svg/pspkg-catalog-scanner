# PSPKG public catalogue scanner

Scans public PSPKG HTML pages and produces a JSON catalogue using Pegasus DL's published `packages` / `downloadLinks` format. This is an independent project, not affiliated with PSPKG or Pegasus.

## Feed

Add this URL as a custom JSON source in Pegasus DL+:

https://raw.githubusercontent.com/sehamayad2405-svg/pspkg-catalog-scanner/main/docs/catalog.json

The feed is an adapter, not a new PS5 browser. Import and download behavior in Pegasus DL+ still needs testing on the console. A third-party provider link may require manual browser verification or may be unsupported. Do not assume every package supports firmware 13.60.

The latest live scan found 6 tool/app listings with public links. Most sampled game download pages require verification; the scanner reports these entries but cannot list them as ready downloads. The feed is not a complete downloadable games source.

## Arabic game lists on GitHub

- [Almarriq8888/PS5-Catalogs](https://github.com/Almarriq8888/PS5-Catalogs) publishes an Arabic PSPKG PS5 catalogue. Its JSON contains third-party host links, but its GitHub Actions runs were failing when checked on 2026-10-31; treat its snapshot and links as unverified.
- [abboud31/Arabgamesps4](https://github.com/abboud31/Arabgamesps4) describes PS4/PS5 Arabic localization methods, but its only HTML file is a generic placeholder and does not contain a game list.

The Pegasus feed now also converts [the Arabic PS5 JSON catalog](https://raw.githubusercontent.com/Almarriq8888/PS5-Catalogs/refs/heads/main/PS5_Arabic_PSPKG_catalog.json), whose `entries` format Pegasus does not read directly. The adapter keeps only HTTPS links from recognized PKG, FFPFSC, exFAT or folder-dump source labels on known hosts; it omits unknown-format, DLC-only and backport-only links. File availability and firmware compatibility remain unverified. The source project's scheduled PSPKG refresh was returning HTTP 403 when checked on 2026-10-31, so the imported snapshot changes only when that repository updates its JSON.

## What it does

- Reads PSPKG's Arabic PS5 games listing, public PS4/PS5 listings and the PS5 tools section. Arabic results are identified from their listing pages.
- Extracts names, images, title IDs where present, source pages and explicit public download links; adapts the separate Arabic JSON source into Pegasus format.
- Follows each detail page's public download-page link, with a bounded request budget.
- Excludes unresolved entries from the download catalogue; keeps them in `docs/index.json` with their status.
- Records HTTP failures and unresolved counts in `docs/report.json`.
- Reserves the first third of each run for listing pages, then uses the remaining budget for game details and their public download pages. This prevents large PS4/PS5 indexes from starving Arabic game details. The daily run checks up to 200 pages with a minimum one-second delay. No game files are downloaded.
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
