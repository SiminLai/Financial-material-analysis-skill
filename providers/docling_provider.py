import time


def parse_docling(path, mode='auto', language='chi_sim+eng'):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from providers.document_pipeline import assemble

    started = time.monotonic()
    options = PdfPipelineOptions()
    options.do_ocr = mode != 'off'
    options.do_table_structure = True
    options.ocr_options = TesseractCliOcrOptions(lang=language.split('+'), force_full_page_ocr=mode == 'force')
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    converted = converter.convert(str(path))
    document = converted.document
    pages = {int(number): {'page': int(number), 'width': page.size.width, 'height': page.size.height,
                          'text': '', 'blocks': [], 'method': 'docling',
                          'warnings': ['structured_model_output_requires_review']}
             for number, page in document.pages.items()}
    tables = []
    for item, level in document.iterate_items():
        for provenance in getattr(item, 'prov', []):
            number = provenance.page_no
            if number not in pages:
                continue
            box = provenance.bbox.to_top_left_origin(page_height=pages[number]['height'])
            bbox = [box.l, box.t, box.r, box.b]
            text = getattr(item, 'text', '')
            if text:
                pages[number]['blocks'].append({'page': number, 'bbox': bbox, 'text': text, 'method': 'docling'})
                pages[number]['text'] += text + '\n'
            if hasattr(item, 'data') and hasattr(item.data, 'grid'):
                if len(item.prov) != 1:
                    pages[number]['warnings'].append('multi_page_table_not_flattened')
                    continue
                rows = [[cell.text for cell in row] for row in item.data.grid]
                tables.append({'page': number, 'bbox': bbox, 'rows': rows, 'engine': 'docling',
                               'needs_review': True})
                pages[number]['text'] += '\n'.join(' | '.join(row) for row in rows) + '\n'
    return assemble(path, 'docling', [pages[number] for number in sorted(pages)], tables, started)
