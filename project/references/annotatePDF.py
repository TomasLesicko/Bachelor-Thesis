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
            # if(regex_results):
            #    print("Chapter " + str(regex_results[1]) + " is on page " + str(regex_results[2]))
            # else:
            #    print("failed")
            if regex_results and regex_results[1] == str(section):
                return regex_results[2]


def annotateReference(doc, ref):
    section = ref["document"]["section"].split(":")
    pageNum = int(findSectionPage(section[0]))
    # page = doc[contentPages + pageNum - 1]
    page = doc[23]  # temp for test PDF


def annotate(doc):
    references = json.load(open("referencesSmall.json")) # TEMP, change to references
    for ref in references:
        # annotateReference(doc, ref)
        section = ref["document"]["section"].split(":")
        pageNum = int(findSectionPage(doc, section[0]))
        # page = doc[contentPages + pageNum - 1]
        page = doc[23]  # temp for test PDF
        blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
        # print(blocks)
        # print("found section " + str(section[0]) + " on page " + str(pageNum))

        for block in blocks:
            reg = "\(" + section[1] + "\)"
            result = re.search(reg, block[4])
            # if section[1] in block[4]: # gonna need regex here
            if result:
                print("found the correct block" + str(block[4]))
                rect = [block[0], block[1], block[2], block[3]]
                annot = page.addHighlightAnnot(rect)
                annot.setColors(stroke=(0, 0.7, 0))
                annot = page.addTextAnnot((rect[2] + commentInfoIconOffsetX, rect[1]), ref["semantics"]["file"],
                                          "Comment")
                annot.setColors(stroke=(0, 0.8, 0))
                annot.update()
                print("annotated the block")

    print("saving document")
    doc.save("n4296_except.pdf", garbage=4, deflate=True, clean=True)

def main(argv):
    try:
        # os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/', argv[1])
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                                             argv[1].lower())
        #path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'WebstormProjects/PDF/',
        #                                     argv[1].lower())
        if path[-4:].lower() != ".pdf":
            path += ".pdf"
        originalPDF = fitz.open(path)
        annotate(originalPDF)
    except (RuntimeError, IndexError):
        # print("Usage: annotatePDF.py <tag>")
        print("Usage: \"annotatePDF.py <tag>\"\ne.g. \"annotatePDF.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
