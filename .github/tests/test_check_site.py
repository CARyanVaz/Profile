"""Tests for tools/check_site.py. Run from the repository root:  python .github/tests/test_check_site.py
Kept under .github/ because GitHub Pages does not publish that folder, so the tests stay off the live site.
Standard library only; runs the same on Windows and Linux."""
import os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "..", "tools")
sys.dont_write_bytecode = True
sys.path.insert(0, TOOLS)
import check_site as cs


class ResolveTests(unittest.TestCase):
    def test_relative_links(self):
        self.assertEqual(cs.resolve("../about/", "services/tds-tcs/index.html"), "/services/about/")
        self.assertEqual(cs.resolve("../../about/", "services/tds-tcs/index.html"), "/about/")
        self.assertIn(cs.resolve("../", "web-design/index.html"), ("/", "//"))  # "//" is the long-standing result; it maps to the home page
        self.assertEqual(cs.resolve("../assets/img/favicon-48.png", "about/index.html"), "/assets/img/favicon-48.png")
        self.assertEqual(cs.resolve("faq/", "index.html"), "/faq/")

    def test_url_paths_never_contain_backslashes(self):
        for href in ("../", "../../privacy/", "../css/styles.css?v=1"):
            self.assertNotIn("\\", cs.resolve(href, "services/gst/index.html"))

    def test_windows_style_page_path(self):
        # os.path.relpath on Windows gives 'services\\gst\\index.html'
        self.assertEqual(cs.resolve("../../contact/", "services\\gst\\index.html"), "/contact/")
        self.assertIn(cs.resolve("../", "web-design\\index.html"), ("/", "//"))

    def test_absolute_and_ignored_links(self):
        self.assertEqual(cs.resolve("/faq/", "x/index.html"), "/faq/")
        self.assertEqual(cs.resolve("https://vazassociates.in/faq/", "x/index.html"), "/faq/")
        self.assertEqual(cs.resolve("https://www.vazassociates.in/", "x/index.html"), "/")
        self.assertIsNone(cs.resolve("https://example.com/", "x/index.html"))
        self.assertIsNone(cs.resolve("mailto:a@b.in", "x/index.html"))
        self.assertIsNone(cs.resolve("#top", "x/index.html"))


class TargetExistsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.tmp.name
        for rel in ("index.html", "about/index.html", "services/gst/index.html", "css/styles.css", "stub.html"):
            full = os.path.join(r, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            open(full, "w").close()
        self.root = r

    def tearDown(self):
        self.tmp.cleanup()

    def exists(self, p):
        return cs.target_exists(p, self.root)

    def test_existing_targets(self):
        for p in ("/", "/about/", "/about", "/services/gst/", "/css/styles.css", "/stub", "/stub.html"):
            self.assertTrue(self.exists(p), p)

    def test_genuinely_broken_links_are_still_reported(self):
        for p in ("/missing/", "/about/missing/", "/css/nope.css", "/services/", "/nope.html"):
            self.assertFalse(self.exists(p), p)

    def test_no_escape_or_windows_separators(self):
        for p in ("/../index.html", "/about/../../index.html", "/about\\", "\\about\\", "/C:/Windows/", "/css\\styles.css"):
            self.assertFalse(self.exists(p), p)

    def test_resolve_then_check_from_windows_page_path(self):
        path = cs.resolve("../../about/", "services\\gst\\index.html")
        self.assertTrue(self.exists(path))
        path = cs.resolve("../../missing/", "services\\gst\\index.html")
        self.assertFalse(self.exists(path))


class WordingTests(unittest.TestCase):
    def problems(self, text):
        return [why for why, _ in cs.wording_problems(text)]

    def test_statutory_late_fee_is_allowed(self):
        for t in (
            "A statement filed late attracts a fee of Rs 200 a day, capped at the tax in the statement.",
            "A late fee of Rs 200 a day applies, capped at the tax in the statement.",
            "Under section 234E a fee of Rs 200 a day is levied until the statement is filed.",
            "A penalty and a fee of Rs 10,000 under the Income-tax Act may apply for default.",
        ):
            self.assertEqual(self.problems(t), [], t)

    def test_promotional_pricing_is_still_flagged(self):
        for t in (
            "Our fees are low.",
            "Our fee of Rs 2,000 covers everything.",
            "Consultation fee starting from Rs 500.",
            "Audit fees start from Rs 10,000.",
            "Affordable pricing for every client.",
            "Starting at Rs 999 per return.",
            "Fee of Rs 1,500 for ITR filing.",
            "File with us today. Retainer fee of Rs 5,000 a month.",
        ):
            self.assertIn("fees or price", self.problems(t), t)

    def test_statutory_word_does_not_excuse_our_fees(self):
        # the exemption applies only to the 'fee of/from/start' form, never to 'our fees'
        self.assertIn("fees or price", self.problems("Delay costs more. Our fees are fixed."))

    def test_other_rules_unchanged(self):
        self.assertIn("superlative 'best'", self.problems("We are the best CA firm."))
        self.assertIn("testimonial", self.problems("Read our testimonials."))
        self.assertEqual(self.problems("There are restrictions on testimonials."), [])
        self.assertIn("ICAI membership number", self.problems("Membership 110356"))

    def test_existing_site_pages_in_scope(self):
        # the sentence that failed CI on 19-21 Nov 2026
        s = "Only the first quarter of FY 2023-24 was extended, to 30 September 2023. A statement filed late attracts a fee of Rs 200 a day, capped at the tax in the statement."
        self.assertEqual(self.problems(s), [])


class WholeSiteTests(unittest.TestCase):
    def test_checker_passes_on_the_site(self):
        script = os.path.join(TOOLS, "check_site.py")
        r = subprocess.run([sys.executable, script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:])


if __name__ == "__main__":
    unittest.main(verbosity=2)
