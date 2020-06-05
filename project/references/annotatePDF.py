import os.path

import fitz
import json
import re
import sys

commentInfoIconOffsetX = 10
contentPages = 14  # for n4296 #TODO


def findSectionPage(doc, section):
    regex = r"([A-Z0-9]+\.[A-Z0-9]+) [^\.]+\.+ (\d+)"

    for i in range(contentPages):
        page = doc[i]
        blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
        for block in blocks:
            regex_results = re.search(regex, block[4])

            if regex_results and regex_results[1] == str(section):
                return regex_results[2]


def findReferencedSection(doc, ref):  # TODO search next page if section not on current page
    section = ref["document"]["section"].split(":")
    pageNum = int(findSectionPage(doc, section[0]))
    # page = doc[contentPages + pageNum - 1]
    page = doc[23]  # temp for test PDF

    return [section, page]


def highlightSection(page, rect):
    annot = page.addHighlightAnnot(rect)
    annot.setColors(stroke=(0, 0.7, 0))
    print("highlighted the section")

def annotateSection(page, rect, ref):
    annot = page.addTextAnnot((rect[2] + commentInfoIconOffsetX, rect[1]), ref["semantics"]["file"],
                              "Comment")
    annot.setColors(stroke=(0, 0.8, 0))
    annot.update()
    print("annotated the section")

def processReference(doc, ref):
    section, page = findReferencedSection(doc, ref)
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = "\(" + section[1] + "\)"

    for block in blocks:
        result = re.search(regex, block[4])

        if result:
            print("found the correct block" + str(block[4]))
            rect = [block[0], block[1], block[2], block[3]]

            highlightSection(page, rect)
            annotateSection(page, rect, ref)

def annotateDocument(doc):
    print("processing references")
    references = json.load(open("referencesSmall.json"))  # TEMP, change to references
    for ref in references:
        processReference(doc, ref)

    print("saving document")
    doc.save("n4296_except.pdf", garbage=4, deflate=True, clean=True)


def main(argv):
    try:
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            argv[1].lower())
        # path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'WebstormProjects/PDF/',
        #                                     argv[1].lower())
        if path[-4:].lower() != ".pdf":
            path += ".pdf"
        originalPDF = fitz.open(path)
        annotateDocument(originalPDF)
    except (RuntimeError, IndexError):
        print("Usage: \"annotatePDF.py <tag>\"\ne.g. \"annotatePDF.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
