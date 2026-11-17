import unittest

from providers.document_pipeline import needs_ocr, assemble
from scripts.benchmark_parsers import evaluate


class DocumentPipelineTests(unittest.TestCase):
    def test_image_table_with_text_header_needs_ocr(self):
        self.assertTrue(needs_ocr('Header ' * 30, 0.7))

    def test_good_native_text_does_not_need_ocr(self):
        self.assertFalse(needs_ocr('Revenue and profit disclosure ' * 30, 0))

    def test_empty_and_corrupt_text_need_ocr(self):
        self.assertTrue(needs_ocr('', 0))
        self.assertTrue(needs_ocr('a' * 100 + '�' * 10, 0))

    def test_evaluation_uses_page_and_exact_rows(self):
        document = {'table_regions': [{'page': 2, 'bbox': [0, 0, 1, 1], 'rows': [['Revenue', '100']]}]}
        self.assertEqual(evaluate(document, [{'page': 2, 'row': ['Revenue', '100']}])['exact_row_accuracy'], 1)
        self.assertEqual(evaluate(document, [{'page': 1, 'row': ['Revenue', '100']}])['exact_row_accuracy'], 0)
