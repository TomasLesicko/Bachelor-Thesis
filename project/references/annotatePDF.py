import os.path

import fitz
import json
import re
import sys

import paragraph_mapping

from shutil import copy2

CHAPTER_START_REGEX = ".*\[.*\]$"

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


def find_referenced_section_page_number(doc, section):  # TODO search next page if section not on current page

    section_page = find_section_page(doc, section[0])
    if section_page is None:
        print("Wrong section format: %s" % section)

    return int(section_page)


def highlight_section(page, rect):
    annot = page.addHighlightAnnot(rect)
    annot.setColors(stroke=(0, 0.7, 0)) # TODO shade depenting on similarity 1 = darkest
    # even better, create a threshold like 0.8 where it's green, 0.6 yellow, 0.4 orange
    # and a way to force the reference to be greeen once manually checked
    print("highlighted the section")


def set_annot_contents(ref):
    annot_contents = ref["semantics"]["file"] + "\n" + str(ref["semantics"]["lines"])
    if ref["document"]["TODO"] == "true":
        annot_contents += "\nMarked as TODO"

    return annot_contents


def annotate_section(page, rect, ref):
    colors = {"stroke":(0, 0.8, 0), "fill":(0, 0, 0)}
    annot_contents = set_annot_contents(ref)

    
    annot = page.addTextAnnot((rect[2] + commentInfoIconOffsetX, rect[1]), annot_contents, "Comment")
    annot.setColors(colors)
    annot.update()


def find_chapter_start(chapter, block):
    if re.search(re.compile("^" + chapter + CHAPTER_START_REGEX), block[4]):
        return True
    return False


def find_referenced_paragraph_page(doc, page_number, section, stoptmp, chapter_start):
    if stoptmp > 20:
        print("Over 20 pages and no result, you probably got a bug in here")
        return None, None

    page = doc[contentPages + page_number - 1]  # TODO contentpages
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = re.compile("^(?:—\n\()?" + section[1] + "\)?") # DO I need multiline?

    for block in blocks:
        if chapter_start:
            result = re.search(regex, block[4])

            if result:
                print("found the correct block" + str(block[4]))
                rect = [block[0], block[1], block[2], block[3]]

                return page, rect
        else:
            chapter_start = find_chapter_start(section[0], block)

    return find_referenced_paragraph_page(doc, page_number + 1, section, stoptmp + 1, chapter_start)


def process_reference(doc, ref):
    section = re.split("[:/]", ref["document"]["section"])

    page_number = find_referenced_section_page_number(doc, section) #return pageNum instead, increment if no
    # match and iterate over blocks again
    # or even better, return pagenum of next chapter so there's upper limit

    pageRect = find_referenced_paragraph_page(doc, page_number, section, 0, False)

    if pageRect[0] is not None and pageRect[1] is not None:
        highlight_section(pageRect[0], pageRect[1])
        annotate_section(pageRect[0], pageRect[1], ref)
        x = 0
    else:
        x = 0 # handle faulty stuff somehow


def annotate_document(doc, target_pdf_tag, port_num):
    print("processing references")

    try:
        with open("references_mapped_%s.json" % target_pdf_tag, "r") as r:
            references = json.loads(r.read())
    except FileNotFoundError:
        print("references_mapped_%s.json" % target_pdf_tag + " not found, attempting to map references")
        references = paragraph_mapping.map_paragraphs_to_target_revision(target_pdf_tag, port_num)
    finally:
        for ref in references:
            process_reference(doc, ref)

    print("Saving document...")
    #doc.save("%s_annotated.pdf" % target_pdf_tag, garbage=4, deflate=True, clean=True)
    doc.saveIncr() # editing a copied PDF is much faster than saving a new PDF


def copy_target_pdf(tag):
    if tag[-4:].lower() != ".pdf":
        tag += ".pdf"
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/', tag)
    copy2(path, os.getcwd())

    return fitz.open(tag)

def main(argv):
    try:
        originalPDF = copy_target_pdf(argv[1].lower())
        annotate_document(originalPDF, argv[1].lower(), argv[2])
    except (RuntimeError, IndexError):
        print("Usage: \"annotatePDF.py <tag> <port number>\"\ne.g. \"annotatePDF.py n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
