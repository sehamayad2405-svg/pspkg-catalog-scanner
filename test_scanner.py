import unittest
from scanner import Document, canonical_page, downloads, parse_page, package, scan, url


class ScannerTests(unittest.TestCase):
    def test_structured_metadata_and_relative_urls(self):
        html = '''<script type="application/ld+json">{"@type":"VideoGame","name":"Demo & Sample","image":"/cover.png"}</script>
        <h1>Fallback</h1><p>PPSA12345</p><a class="gp-dl-btn" href="/ps5/download-demo-1.html">Download</a>'''
        entry, _, pages = parse_page(html, "https://pspkg.com/ps5/demo-1.html")
        self.assertEqual(entry["title"], "Demo & Sample")
        self.assertEqual(entry["posterUrl"], "https://pspkg.com/cover.png")
        self.assertEqual(pages, ["https://pspkg.com/ps5/download-demo-1.html"])
        self.assertEqual(entry["titleId"], "PPSA12345")
        self.assertIsNone(package(entry))

    def test_only_explicit_downloads_and_safe_schemes(self):
        doc = Document('''<a href="javascript:alert(1)" download>Bad</a>
        <a href="https://social.example/">Social</a>
        <a class="download-btn" href="https://files.example/item/1">Provider</a>
        <a href="https://files.example/demo.zip">ZIP</a>''').root
        self.assertEqual(len(downloads(doc, "https://pspkg.com/ps5/tool?slug=demo")), 2)
        self.assertIsNone(url("https://user:secret@example.org/file.zip"))

    def test_unresolved_detail_is_not_a_fake_package(self):
        class Fake:
            def get(self, page):
                if "download-" in page:
                    return "<h1>Login or verification required</h1>"
                return '<h1>Demo</h1><a class="gp-dl-btn" href="/ps5/download-demo-1.html">Download</a>'
        entries, errors, count = scan(["https://pspkg.com/ps5/demo-1.html"], Fake(), 3)
        self.assertEqual(count, 2)
        self.assertEqual(errors, [])
        self.assertEqual(entries[0]["status"], "no_public_download_link")
        self.assertIsNone(package(entries[0]))

    def test_follow_download_page_and_deduplicate(self):
        class Fake:
            def get(self, page):
                if "download-" in page:
                    return '<a class="download-btn" href="https://files.example/demo.pkg">Mirror</a>' * 2
                return '<h1>Demo</h1><a class="gp-dl-btn" href="/ps5/download-demo-1.html">Download</a>'
        entries, _, _ = scan(["https://pspkg.com/ps5/demo-1.html"], Fake(), 3)
        self.assertEqual(len(package(entries[0])["downloadLinks"]), 1)

    def test_request_budget_includes_download_pages(self):
        class Fake:
            def get(self, page):
                return '<h1>Demo</h1><a class="gp-dl-btn" href="/ps5/download-demo-1.html">Download</a>'
        _, _, count = scan(["https://pspkg.com/ps5/demo-1.html"], Fake(), 1)
        self.assertEqual(count, 1)

    def test_verification_is_reported_without_bypass(self):
        class Fake:
            def get(self, page):
                if "download-" in page:
                    return "<p>Complete the check below. Awaiting verification</p>"
                return '<h1>Demo</h1><a class="gp-dl-btn" href="/ps5/download-demo-1.html">Download</a>'
        entries, _, _ = scan(["https://pspkg.com/ps5/demo-1.html"], Fake(), 3)
        self.assertEqual(entries[0]["status"], "manual_verification_required")
        self.assertIsNone(package(entries[0]))

    def test_listing_pagination(self):
        _, next_pages, _ = parse_page('<a href="?page=2">Next</a>', "https://pspkg.com/ps4/")
        self.assertEqual(next_pages, ["https://pspkg.com/ps4/?page=2"])

    def test_language_navigation_does_not_duplicate_items(self):
        self.assertEqual(canonical_page("https://pspkg.com/ar/ps5/demo-1.html#top"),
                         "https://pspkg.com/ps5/demo-1.html")

    def test_title_id_from_public_file_link(self):
        entry, _, _ = parse_page('<h1>Tool</h1><a class="download-btn" href="https://pkg-zone.com/download/ps5/ITEM00001/1.0">Get</a>',
                                 "https://pspkg.com/ps5/tool?slug=tool")
        self.assertEqual(entry["titleId"], "ITEM00001")


if __name__ == "__main__":
    unittest.main()
