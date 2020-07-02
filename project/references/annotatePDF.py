import os.path

import fitz
import json
import re
import sys

sys.path.append("../section_mapping")
#import paragraph_mapping
import paragraph_mapping

from shutil import copy2

ANNOT_DEFAULT_COLOR = {"stroke":(0, 0.8, 0)}

CHAPTER_START_REGEX = ".*\[.*\]$"

commentInfoIconOffsetX = 10


def get_toc_compatible_chapter(chapter):
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?).*"
    x = re.search(regex, chapter)
    y = x[1]
    return y


def find_section_page(doc, section, toc_page_count):
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?) .+ (\d+)$" # TOC only contains subsections depth 1 (13.1 not 13.1.1 etc.)

    for i in range(toc_page_count):
        page = doc[i]
        blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
        for block in blocks:
            regex_results = re.search(regex, block[4])

            if regex_results and regex_results[1] == str(get_toc_compatible_chapter(section)):
                return regex_results[2]


def find_referenced_section_page_number(doc, section, toc_page_count):

    section_page = find_section_page(doc, section[0], toc_page_count)
    if section_page is None:
        print("Wrong section format: %s" % section)

    return int(section_page)


def highlight_section(page, rect, ref):
    annot = page.addHighlightAnnot(rect)
    color_intensity = ref["similarity"]
    if ref["document"]["TODO"] == "true":
        annot.setColors(stroke=(color_intensity, color_intensity, 0))
    else:
        annot.setColors(stroke=(0, color_intensity, 0))
    # even better, create a threshold like 0.8 where it's green, 0.6 yellow, 0.4 orange
    # and a way to force the reference to be greeen once manually checked


def set_annot_contents(ref):
    annot_contents = ref["semantics"]["file"] + "\n" + str(ref["semantics"]["lines"])
    if ref["document"]["TODO"] == "true":
        annot_contents += "\nMarked as TODO"
    annot_contents += "\n" + str(round(100 * float(ref["similarity"]), 2)) + "% match with paragraph in referenced revision"

    return annot_contents


def find_paragraph_annot(page, section):
    annot = page.firstAnnot

    while annot:
        if annot.info["title"] == section:
            return annot

        annot = annot.next

    return None


def annotate_section(page, rect, ref):
    annot_contents = set_annot_contents(ref)
    annot = find_paragraph_annot(page, ref["document"]["section"])

    if annot:
        content = annot.info["content"]
        new_content = "\n----------------------------\n" + annot_contents
        annot.setInfo(content=content+new_content)
    else:
        annot = page.addTextAnnot((rect[2] + commentInfoIconOffsetX, rect[1]), annot_contents, "Comment")
        annot.setInfo(title=ref["document"]["section"])
        annot.setColors(ANNOT_DEFAULT_COLOR)
    annot.update()


def find_chapter_start(chapter, block):
    if re.search(re.compile("^" + chapter + CHAPTER_START_REGEX), block[4]):
        return True
    return False


def find_referenced_paragraph_page(doc, page_number, toc_page_count, section, stoptmp, chapter_start):
    if stoptmp > 20:
        print("Over 20 pages and no result, you probably got a bug in here @ ref %s:%s" % (section[0], section[1]))
        return None, None

    page = doc[toc_page_count + page_number - 1]
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = re.compile("^(?:—\n\()?" + section[1] + "\)?\n")

    for block in blocks:
        if chapter_start:
            result = re.search(regex, block[4])

            if result:
                rect = [block[0], block[1], block[2], block[3]]

                return page, rect
        else:
            chapter_start = find_chapter_start(section[0], block)

    return find_referenced_paragraph_page(doc, page_number + 1, toc_page_count, section, stoptmp + 1, chapter_start)


def find_toc_page_count(doc):
    for i in range(doc.pageCount):
        if doc[i].getText().rstrip()[-1] == "1": # page numbering starts from 1 after toc section
            return i
    print("Error: Couldn't find TOC page count")
    raise IndexError


def process_reference(doc, ref):
    if not ref["error"]:
        section = re.split("[:/]", ref["document"]["section"])
        toc_page_count = find_toc_page_count(doc)
        page_number = find_referenced_section_page_number(doc, section, toc_page_count)

        pageRect = find_referenced_paragraph_page(doc, page_number, toc_page_count, section, 0, False)

        if pageRect[0] is not None and pageRect[1] is not None:
            highlight_section(pageRect[0], pageRect[1], ref)
            annotate_section(pageRect[0], pageRect[1], ref)
        else:
            x = 0 # handle faulty stuff somehow


def annotate_document(doc, target_pdf_tag, port_num):
    try:
        with open("references_mapped_%s.json" % target_pdf_tag, "r") as r:
            references = json.loads(r.read())
    except FileNotFoundError:
        print("references_mapped_%s.json" % target_pdf_tag + " not found, attempting to map references")
        references = paragraph_mapping.map_paragraphs_to_target_revision(target_pdf_tag, port_num)
    finally:
        print("Highlighting and annotating references in %s.pdf" % target_pdf_tag)
        for ref in references:
            process_reference(doc, ref)

    print("Saving document...")
    #doc.save("%s_annotated.pdf" % target_pdf_tag, garbage=4, deflate=True, clean=True)
    doc.saveIncr() # editing a copied PDF is much faster than saving a new PDF


def copy_target_pdf(tag):
    print("Creating a copy of %s.pdf" % tag)
    if tag[-4:].lower() != ".pdf":
        tag += ".pdf"
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/', tag)
    copy2(path, os.getcwd())

    renamed_tag = tag.split(".")[0] + "_annotated.pdf"
    os.rename(tag, renamed_tag)

    return fitz.open(renamed_tag)


def main(argv):
    try:
        target_PDF = copy_target_pdf(argv[1].lower())
        annotate_document(target_PDF, argv[1].lower(), argv[2])
    except (RuntimeError, IndexError, FileNotFoundError) as e:
        print(e)
        print("annotatePDF arguments required: \"<tag> <port number>\"\ne.g. \"n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
