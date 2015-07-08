#!/usr/bin/env python3
# coding: utf-8

import collections
import io
import re
import sys

sys.path.append('/home/phihag/projects/div/PyPDF2/')
import PyPDF2


def _fix_text(s):
    replace = {
        'ƒ': 'Ü',
        'ã': '„',
        'Ò': '“',
        '•': 'Ä',
    }

    for k, v in replace.items():
        s = s.replace(k, v)

    s = re.sub(r'\s+', ' ', s)

    return s


def _build_pdf_dict(reader):
    to_visit = collections.deque([reader.resolvedObjects])
    res = {}
    while to_visit:
        haystack = to_visit.pop()
        for key in haystack:
            val = haystack[key]
            res[key] = val
            if (isinstance(val, dict) or
                    isinstance(val, PyPDF2.generic.DictionaryObject)):
                to_visit.append(val)
    return res


def _pdf_find_xobject(name, reader):
    if not hasattr(reader, '_fix_ebook_pdf_dict'):
        reader._fix_ebook_pdf_dict = _build_pdf_dict(reader)
    return reader._fix_ebook_pdf_dict[name]


def add_page_labels(m):
    page_labels = b'''
        /PageLabels << /Nums [
            0 << /S /D /P (Cover ) >>
            4 << /S /D >>
        ] >>
    '''
    return m.group(1) + page_labels + m.group(2)


def find_by_style(page, match_style):
    current_state = {}

    content = page["/Contents"].getObject()
    if not isinstance(content, PyPDF2.pdf.ContentStream):
        content = PyPDF2.pdf.ContentStream(content, page.pdf)

    cur = ''
    is_matching = False
    operations = list(content.operations)
    for operands, operator in operations:
        if operator == b'Do':
            if operands[0].startswith('/Fm'):
                xobject = _pdf_find_xobject(operands[0], page.pdf)
                add_content = PyPDF2.pdf.ContentStream(
                    xobject.getObject(), page.pdf)
                operations.extend(add_content.operations)

        if is_matching and operator in (b'TJ', b'Tj'):
            if operator == b'TJ':
                text = ''.join(operands[0][::2])
            elif operator == b'Tj':
                text = ''.join(operands[0])
            else:
                assert False

            cur += _fix_text(text)
        else:
            current_state[operator] = operands
            new_is_matching = match_style(current_state)
            if is_matching and not new_is_matching and cur:
                yield cur
                cur = ''
            is_matching = new_is_matching
    if cur:
        yield cur


def add_toc(pdf):
    inbuf_reader = io.BytesIO(pdf)
    reader = PyPDF2.PdfFileReader(inbuf_reader)

    writer = PyPDF2.PdfFileWriter()
    for page in reader.pages:
        writer.addPage(page)

    writer.addBookmark('Inhalt', 2, fit='/FitB')

    h1 = None
    for page_num, page in enumerate(reader.pages):
        h1s = list(find_by_style(
            page, lambda style: b'Tm' in style and style[b'Tm'][0] == 45))
        if h1s:
            assert len(h1s) == 1
            h1 = writer.addBookmark(h1s[0], page_num, fit='/FitB')

        # h2s = list(find_by_style(page, {b'BDC': ['/AAPL:Style', '/Pl1']}))
        # if h2s:
        #     for h2 in h2s:
        #         h2 = writer.addBookmark(_fix_text(h2), page_num, fit='/FitB')

    outbuf = io.BytesIO()
    writer.write(outbuf)
    return outbuf.getvalue()


def main():
    _, in_fn, out_fn = sys.argv

    with open(in_fn, 'rb') as inf:
        pdf = inf.read()
    pdf = add_toc(pdf)
    # TODO set title
    pdf = re.sub(br'(<<\s*/Type /Catalog)(.*>>)', add_page_labels, pdf)
    with open(out_fn, 'wb') as outf:
        outf.write(pdf)

if __name__ == '__main__':
    main()
