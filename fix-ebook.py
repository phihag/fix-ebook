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
        '–': 'Ö',
        '§': 'ß',
    }

    for k, v in replace.items():
        s = s.replace(k, v)

    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(?<![0-9\s])-(?![0-9\s])', '', s)
    s = re.sub(r'\s?\([0-9\s,]+\)\s*$', '', s)

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


def add_toc(reader, writer):
    writer.addBookmark('Cover', 0, fit='/FitB')
    writer.addBookmark('Inhalt', 2, fit='/FitB')
    h1 = None
    for page_num, page in enumerate(reader.pages):
        h1s = list(find_by_style(
            page, lambda style: b'Tm' in style and style[b'Tm'][0] == 45))
        if h1s:
            assert len(h1s) == 1
            h1 = writer.addBookmark(h1s[0], page_num, fit='/FitB')

        h2s = find_by_style(
            page, lambda style: b'Tm' in style and 28 <= style[b'Tm'][0] <= 32)
        for h2 in h2s:
            h2 = writer.addBookmark(h2, page_num, fit='/FitB', parent=h1)


def change_pdf(pdf, title, author):
    inbuf_reader = io.BytesIO(pdf)
    reader = PyPDF2.PdfFileReader(inbuf_reader)

    writer = PyPDF2.PdfFileWriter()
    for page in reader.pages:
        writer.addPage(page)

    add_toc(reader, writer)

    class NumberTree(PyPDF2.generic.PdfObject):
        def writeToStream(self, stream, encryption_key):
            stream.write(b''' << /Nums [
                0 << /P (Cover) >>
                1 << /S /r >>
                3 << /S /D /St 3 >>
            ] >> ''')

    pls = NumberTree()
    writer._root_object[PyPDF2.generic.NameObject('/PageLabels')] = pls

    info = PyPDF2.pdf.DocumentInformation()
    info[PyPDF2.generic.NameObject('/Author')] = PyPDF2.generic.TextStringObject(author)
    info[PyPDF2.generic.NameObject('/Title')] = PyPDF2.generic.TextStringObject(title)
    writer._info = info

    outbuf = io.BytesIO()
    writer.write(outbuf)
    return outbuf.getvalue()


def main():
    _, in_fn, out_fn, title, author = sys.argv

    with open(in_fn, 'rb') as inf:
        pdf = inf.read()
    pdf = change_pdf(pdf, title, author)
    with open(out_fn, 'wb') as outf:
        outf.write(pdf)

if __name__ == '__main__':
    main()
