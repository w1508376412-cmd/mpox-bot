"""Tests for limiting user-visible reference sources."""
import unittest


class ReferenceSourceTest(unittest.TestCase):
    def test_select_reference_sources_deduplicates_and_limits_to_two(self):
        from backend.reference_sources import select_reference_sources

        sources = [
            {"source": "国家卫健委", "title": "猴痘防控技术指南", "url": "https://example.com/nhc"},
            {"source": "国家卫健委", "title": "猴痘防控技术指南", "url": "https://example.com/nhc"},
            {"source": "国家疾控局", "title": "猴痘防控方案", "url": "https://example.com/ndcpa"},
            {"source": "WHO", "title": "Mpox", "url": "https://example.com/who"},
        ]

        selected = select_reference_sources(sources)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["source"], "国家卫健委")
        self.assertEqual(selected[1]["source"], "国家疾控局")

    def test_select_reference_sources_supports_model_like_objects(self):
        from backend.reference_sources import select_reference_sources

        class Source:
            def __init__(self, source, title, url):
                self.source = source
                self.title = title
                self.url = url

        sources = [
            Source("国家卫健委", "猴痘防控技术指南", "https://example.com/nhc"),
            Source("国家疾控局", "猴痘防控方案", "https://example.com/ndcpa"),
            Source("WHO", "Mpox", "https://example.com/who"),
        ]

        selected = select_reference_sources(sources)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0].source, "国家卫健委")
        self.assertEqual(selected[1].source, "国家疾控局")


if __name__ == "__main__":
    unittest.main()
