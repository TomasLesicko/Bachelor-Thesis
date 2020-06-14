import os.path

import fitz
import json
import re
import sys

import paragraph_mapping

from shutil import copy2

commentInfoIconOffsetX = 10
contentPages = 14  # for n4296 #TODO


def get_toc_compatible_chapter(chapter):
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?).*"
    x = re.search(regex, chapter)
    y = x[1]
    return y


def find_section_page(doc, section):
    # regex = r"([A-Z0-9]+\.[A-Z0-9]+) [^\.]+\.+ (\d+)"
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?) .+ (\d+)$" # TOC only contains subsections depth 1 (13.1 not 13.1.1 etc.)

    for i in range(contentPages):
        page = doc[i]
        blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
        for block in blocks:
            regex_results = re.search(regex, block[4])

            if regex_results and regex_results[1] == str(get_toc_compatible_chapter(section)):
                return regex_results[2]


def find_referenced_section(doc, ref):  # TODO search next page if section not on current page
    section = re.split("[:/]", ref["document"]["section"]) # TODO other varatons
    if find_section_page(doc, section[0]) is None:
        x = 0
    pageNum = int(find_section_page(doc, section[0]))
    page = doc[contentPages + pageNum - 1] # TODO contentpages

    return [section, page]


def highlight_section(page, rect):
    annot = page.addHighlightAnnot(rect)
    annot.setColors(stroke=(0, 0.7, 0))
    print("highlighted the section")


def annotate_section(page, rect, ref):
    annot = page.addTextAnnot((rect[2] + commentInfoIconOffsetX, rect[1]), ref["semantics"]["file"],
                              "Comment")
    annot.setColors(stroke=(0, 0.8, 0))
    annot.update()
    print("annotated the section")


def process_reference(doc, ref):
    section, page = find_referenced_section(doc, ref)
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = "\(" + section[1] + "\)" # TODO other varatons

    for block in blocks:
        result = re.search(regex, block[4])

        if result:
            print("found the correct block" + str(block[4]))
            rect = [block[0], block[1], block[2], block[3]]

            highlight_section(page, rect)
            annotate_section(page, rect, ref)
            break


def annotate_document(doc, target_pdf_tag):
    print("processing references")
    #references = json.load(open("referencesSmall.json"))  # TODO references = output from paragraph_mapping
    references = paragraph_mapping.map_paragraphs_to_target_revision(target_pdf_tag)
    for ref in references:
        process_reference(doc, ref)

    print("Saving document...")
    #doc.save("n4296_annotated.pdf", garbage=4, deflate=True, clean=True)
    doc.saveIncr() # much faster though probably want to edit a copy of the PDF, not directly in draft folder


def main(argv):
    try:
        tag = argv[1].lower()

        if tag[-4:].lower() != ".pdf":
            tag += ".pdf"

        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            tag)

        copy2(path, os.getcwd())

        originalPDF = fitz.open(tag)
        annotate_document(originalPDF, argv[1].lower())
    except (RuntimeError, IndexError):
        print("Usage: \"annotatePDF.py <tag>\"\ne.g. \"annotatePDF.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
