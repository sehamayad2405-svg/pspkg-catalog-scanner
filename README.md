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

The scanner does not import third-party binary links from those repositories. It scans PSPKG's Arabic listing directly and exports only links it can observe on the public pages.

## What it does

- Reads PSPKG's Arabic games listing, public PS4/PS5 listings and the PS5 tools section. Arabic results are identified from their detail pages.
- Extracts names, images, title IDs where present, source pages and explicit public download links.
- Follows each detail page's public download-page link, with a bounded request budget.
- Excludes unresolved entries from the download catalogue; keeps them in `docs/index.json` with their status.
- Records HTTP failures and unresolved counts in `docs/report.json`.
- Scans listing pages before detail pages so the page budget is not spent on only the first titles. The daily run checks up to 200 pages with a minimum one-second delay. No game files are downloaded.
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
