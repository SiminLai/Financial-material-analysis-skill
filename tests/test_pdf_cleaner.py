import unittest

from utils.pdf_cleaner import clean_layout_blocks
from providers.pdf_provider import PDFProvider


class TestPdfCleaner(unittest.TestCase):
    def test_removes_repeated_headers_and_page_numbers(self):
        page_blocks = [
            [
                {
                    "page": 1,
                    "text": "ACME Corp Annual Report",
                    "bbox": (0, 20, 300, 40),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 1,
                    "text": "Revenue increased to $120 million",
                    "bbox": (20, 180, 500, 220),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 1,
                    "text": "Page 1 of 2",
                    "bbox": (250, 960, 380, 985),
                    "page_height": 1000,
                    "is_table_region": False,
                },
            ],
            [
                {
                    "page": 2,
                    "text": "ACME Corp Annual Report",
                    "bbox": (0, 18, 300, 38),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 2,
                    "text": "Net profit was $20 million",
                    "bbox": (20, 200, 480, 240),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 2,
                    "text": "Page 2 of 2",
                    "bbox": (250, 962, 380, 986),
                    "page_height": 1000,
                    "is_table_region": False,
                },
            ],
        ]

        cleaned_text, stats = clean_layout_blocks(page_blocks)

        self.assertIn("Revenue increased", cleaned_text)
        self.assertIn("Net profit", cleaned_text)
        self.assertNotIn("ACME Corp Annual Report", cleaned_text)
        self.assertNotIn("Page 1 of 2", cleaned_text)
        self.assertGreaterEqual(stats.get("removed_blocks_count", 0), 2)

    def test_keeps_financial_titles_near_top(self):
        page_blocks = [
            [
                {
                    "page": 1,
                    "text": "Consolidated Balance Sheets",
                    "bbox": (10, 15, 420, 40),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 1,
                    "text": "(in millions)",
                    "bbox": (10, 45, 180, 65),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 1,
                    "text": "Fiscal year ended December 31, 2025",
                    "bbox": (10, 70, 420, 95),
                    "page_height": 1000,
                    "is_table_region": False,
                },
            ]
        ]

        cleaned_text, _ = clean_layout_blocks(page_blocks)

        self.assertIn("Consolidated Balance Sheets", cleaned_text)
        self.assertIn("(in millions)", cleaned_text)
        self.assertIn("Fiscal year ended December 31, 2025", cleaned_text)

    def test_keeps_table_region_even_in_margin(self):
        page_blocks = [
            [
                {
                    "page": 1,
                    "text": "Header Noise",
                    "bbox": (10, 10, 180, 28),
                    "page_height": 1000,
                    "is_table_region": False,
                },
                {
                    "page": 1,
                    "text": "Total Assets 1000",
                    "bbox": (10, 18, 260, 34),
                    "page_height": 1000,
                    "is_table_region": True,
                },
                {
                    "page": 1,
                    "text": "Total Liabilities 450",
                    "bbox": (10, 35, 280, 52),
                    "page_height": 1000,
                    "is_table_region": True,
                },
                {
                    "page": 1,
                    "text": "第12页",
                    "bbox": (260, 965, 330, 985),
                    "page_height": 1000,
                    "is_table_region": False,
                },
            ]
        ]

        cleaned_text, _ = clean_layout_blocks(page_blocks)

        self.assertIn("Total Assets 1000", cleaned_text)
        self.assertIn("Total Liabilities 450", cleaned_text)
        self.assertNotIn("第12页", cleaned_text)

    def test_table_regions_json_keeps_2d_rows(self):
        tables = [
            {
                "page": 3,
                "bbox": (10.0, 20.0, 300.0, 200.0),
                "rows": [
                    ["Item", "2025", "2024"],
                    ["Revenue", 1200, 1000],
                    ["Net Profit", None, 120],
                ],
            }
        ]

        out = PDFProvider._to_json_table_regions(tables)

        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["page"], 3)
        self.assertEqual(out[0]["bbox"], [10.0, 20.0, 300.0, 200.0])
        self.assertIsInstance(out[0]["rows"], list)
        self.assertIsInstance(out[0]["rows"][0], list)
        self.assertEqual(out[0]["rows"][1], ["Revenue", "1200", "1000"])
        self.assertEqual(out[0]["rows"][2], ["Net Profit", "", "120"])


if __name__ == "__main__":
    unittest.main()
