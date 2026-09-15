import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from internet_explorer import PageParser, allowed_host, crawlable_url, make_cloze, validate_url


class InternetExplorerSafetyTest(unittest.TestCase):
    def test_allowlist_is_exact_or_subdomain(self):
        self.assertTrue(allowed_host("en.wikipedia.org"))
        self.assertTrue(allowed_host("x.en.wikipedia.org"))
        self.assertFalse(allowed_host("en.wikipedia.org.evil.test"))
        self.assertFalse(allowed_host("wikipedia.org"))

    def test_blocks_scheme_credentials_ports_and_private_hosts(self):
        for url in (
            "http://en.wikipedia.org/wiki/Physics",
            "https://user:pass@en.wikipedia.org/wiki/Physics",
            "https://en.wikipedia.org:444/wiki/Physics",
            "https://127.0.0.1/",
        ):
            with self.assertRaises(ValueError):
                validate_url(url, resolve=False)

    def test_parser_ignores_script_and_non_allowlisted_links(self):
        parser = PageParser("https://en.wikipedia.org/wiki/Physics")
        parser.feed('<p>Useful physics text.</p><script>steal()</script><a href="/wiki/Energy">Energy</a><a href="https://evil.test">bad</a>')
        self.assertIn("Useful physics text.", parser.text)
        self.assertNotIn("steal()", parser.text)
        self.assertEqual(parser.links, ["https://en.wikipedia.org/wiki/Energy"])

    def test_wikipedia_site_machinery_is_not_crawlable(self):
        self.assertTrue(crawlable_url("https://en.wikipedia.org/wiki/Quantum_mechanics"))
        self.assertFalse(crawlable_url("https://en.wikipedia.org/wiki/Wikipedia:Contents"))
        self.assertFalse(crawlable_url("https://en.wikipedia.org/wiki/Physics?oldid=1"))

    def test_cloze_has_exact_answer_contract(self):
        text = ("Gravity describes an interaction between masses, and gravity can be modeled at different scales. " * 3).strip()
        lesson = make_cloze("Gravity", text, "physics", "https://en.wikipedia.org/wiki/Gravity")
        self.assertIsNotNone(lesson)
        self.assertEqual(len(lesson["options"]), 4)
        self.assertIn(lesson["answer"], range(4))
        self.assertIn("____", lesson["question"])
        self.assertTrue(lesson["web_derived"])


if __name__ == "__main__":
    unittest.main()
