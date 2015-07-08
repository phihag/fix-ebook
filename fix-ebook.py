#!/usr/bin/env python3

import io
import re
import sys

sys.path.append('/home/phihag/projects/div/PyPDF2/')
import PyPDF2


def add_page_labels(m):
    page_labels = b'''
        /PageLabels << /Nums [
            0 << /S /D /P (Cover ) >>
            4 << /S /D >>
        ] >>
    '''
    return m.group(1) + page_labels + m.group(2)


def find_by_style(page, style):
    current_state = {s: None for s in style.keys()}

    content = page["/Contents"].getObject()
    if not isinstance(content, PyPDF2.pdf.ContentStream):
        content = PyPDF2.pdf.ContentStream(content, page.pdf)

    cur = ''
    is_matching = False
    for operands, operator in content.operations:
        if operator == b'TJ':
            if is_matching:
                print(operands)
                cur += ''.join(operands[0][::2])
        else:
            current_state[operator] = operands
            new_is_matching = all(
                current_state.get(skey) == val for skey, val in style.items())
            if is_matching and not new_is_matching and cur:
                yield cur
                cur = ''
            is_matching = new_is_matching
    if cur:
        yield cur


def add_toc(pdf):
    inbuf_reader = io.BytesIO(pdf)
    reader = PyPDF2.PdfFileReader(inbuf_reader)

    inbuf = io.BytesIO(pdf)
    merger = PyPDF2.PdfFileMerger()
    merger.append(inbuf)
    writer = merger.output

    parent = merger.addBookmark('Inhalt', 2)

    h1 = None
    for page_num, page in enumerate(reader.pages):
        h1s = list(find_by_style(page, {b'Tf': ['/TT4', 1]}))
        if h1s:
            assert len(h1s) == 1
            h1_text = h1s[0]
            h1 = merger.addBookmark(h1_text, page_num)

    outbuf = io.BytesIO()
    merger.write(outbuf)
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
