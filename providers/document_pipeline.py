import importlib.metadata
import os
import time


def needs_ocr(text, image_fraction):
    visible = ''.join(text.split())
    return len(visible) < 40 or image_fraction >= 0.25 or visible.count('�') / max(len(visible), 1) > 0.02


def version(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def assemble(path, engine, pages, tables, started):
    text = '\n\n'.join('--- Page ' + str(page['page']) + ' ---\n' + page['text'] for page in pages)
    warnings = [{'page': page['page'], 'message': warning} for page in pages for warning in page['warnings']]
    return {'text': text, 'raw_text': text, 'cleaned_text': text,
            'pages': pages, 'tables': tables, 'table_regions': tables,
            'meta': {'source': str(path), 'method': engine, 'document_schema': 'document-1.0',
                     'coordinate_system': 'page_points_top_left', 'pages': len(pages),
                     'parse_warnings': warnings, 'needs_review': bool(warnings),
                     'duration_seconds': round(time.monotonic() - started, 3),
                     'versions': {name: version(name) for name in ('PyMuPDF', 'pdfplumber', 'docling')}}}


def parse_document(path, engine=None, ocr=None, language=None, dpi=None):
    engine = engine or os.getenv('PDF_ENGINE', 'native')
    mode = ocr or os.getenv('PDF_OCR', 'auto')
    language = language or os.getenv('PDF_OCR_LANGUAGE', 'chi_sim+eng')
    dpi = int(dpi or os.getenv('PDF_OCR_DPI', '200'))
    if engine not in {'native', 'docling'} or mode not in {'auto', 'off', 'force'} or not 100 <= dpi <= 300:
        raise ValueError('Invalid PDF engine, OCR mode or DPI (100-300)')
    if engine == 'docling':
        from providers.docling_provider import parse_docling
        return parse_docling(path, mode, language)
    started = time.monotonic()
    try:
        import fitz
    except ImportError:
        if mode == 'force':
            raise RuntimeError('Forced OCR requires PyMuPDF and Tesseract language data')
        import pdfplumber
        pages, tables = [], []
        with pdfplumber.open(path) as document:
            for number, page in enumerate(document.pages, 1):
                warnings = ['pymupdf_unavailable_ocr_not_performed']
                text = ''
                try:
                    text = page.extract_text() or ''
                    for table in page.find_tables():
                        tables.append({'page': number, 'bbox': list(table.bbox), 'rows': table.extract(), 'engine': 'pdfplumber'})
                except Exception as error:
                    warnings.append('page_parse_failed:' + type(error).__name__)
                pages.append({'page': number, 'width': page.width, 'height': page.height, 'text': text,
                              'blocks': [], 'method': 'pdfplumber', 'warnings': warnings})
        return assemble(path, 'pdfplumber', pages, tables, started)
    pages, tables = [], []
    with fitz.open(path) as document:
        if document.needs_pass:
            raise ValueError('Encrypted PDF requires an unlocked copy')
        if len(document) > 1000:
            raise ValueError('PDF exceeds 1000 page limit')
        for index in range(len(document)):
            page = document[index]
            warnings, blocks, text, method = [], [], '', 'native'
            image_fraction = 0.0
            try:
                layout = page.get_text('dict')
                area = max(page.rect.width * page.rect.height, 1)
                image_fraction = min(1.0, sum(max(0, block['bbox'][2]-block['bbox'][0]) * max(0, block['bbox'][3]-block['bbox'][1])
                                             for block in layout['blocks'] if block.get('type') == 1) / area)
                textpage = None
                native_text = page.get_text('text', sort=True)
                requested = mode == 'force' or (mode == 'auto' and needs_ocr(native_text, image_fraction))
                if requested:
                    try:
                        if page.rect.width * page.rect.height * (dpi / 72) ** 2 > 30000000:
                            raise ValueError('OCR render exceeds 30 megapixel budget')
                        textpage = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
                        method = 'tesseract_full_page'
                        warnings.append('ocr_requires_manual_numeric_review')
                    except Exception as error:
                        warnings.append('ocr_failed:' + type(error).__name__)
                elif mode == 'off' and needs_ocr(native_text, image_fraction):
                    warnings.append('ocr_needed_but_disabled')
                for block in page.get_text('blocks', textpage=textpage, sort=True):
                    if len(block) > 6 and block[6] != 0:
                        continue
                    blocks.append({'bbox': list(block[:4]), 'text': block[4], 'page': index + 1, 'method': method})
                text = '\n'.join(block['text'] for block in blocks)
                try:
                    for table in page.find_tables().tables:
                        tables.append({'page': index + 1, 'bbox': list(table.bbox), 'rows': table.extract(),
                                       'engine': 'pymupdf_native_table', 'cells': [list(cell) if cell else None for cell in table.cells]})
                except Exception as error:
                    warnings.append('native_table_failed:' + type(error).__name__)
                if requested:
                    warnings.append('native_tables_do_not_cover_scanned_tables')
                if not text.strip():
                    warnings.append('empty_page_or_unreadable')
            except Exception as error:
                warnings.append('page_parse_failed:' + type(error).__name__)
            pages.append({'page': index + 1, 'width': page.rect.width, 'height': page.rect.height,
                          'text': text, 'blocks': blocks, 'method': method,
                          'image_fraction': image_fraction, 'warnings': warnings})
    return assemble(path, 'native', pages, tables, started)
