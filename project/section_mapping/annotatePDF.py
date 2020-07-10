#!/usr/bin/env python3

import os.path
import fitz
import re
import sys

import paragraph_mapping

from shutil import copy2

ANNOT_DEFAULT_COLOR = {"stroke": (0, 0.8, 0)}

CHAPTER_START_REGEX = r".*\[.*\]$"

ANNOT_OFFSET_X = 10
COVERAGE_ANNOT_X = 550
COVERAGE_ANNOT_Y = 30

MAX_PAGES_TO_SEARCH = 200


def get_toc_compatible_chapter(chapter):
    """ TOC only contains main chapters and first-level subchapters
     (13.1 not 13.1.1 etc.)
    For 13.1.1 it's only important that it's a part of 13.1 when
    searching for the page.
    """
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?).*"
    result = re.search(regex, chapter)

    return result[1]


def find_section_page(doc, section, toc_page_count):
    """ Finds the page where the referenced chapter starts
    so we don't have to traverse the whole document for each
    reference.
    """
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?)[\s\S+]+ (\d+)$"
    toc_compatible_chapter = get_toc_compatible_chapter(section)

    for i in range(toc_page_count):
        page = doc[i]
        blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
        for block in blocks:
            regex_results = re.search(regex, block[4])

            if regex_results and regex_results[1] == toc_compatible_chapter:
                return regex_results[2]


def find_referenced_section_page_number(doc, section, toc_page_count):
    section_page = find_section_page(doc, section[0], toc_page_count)
    if section_page is None:
        print("Wrong section format: %s" % section)

    return int(section_page)


def highlight_section(page, rect, ref):
    """ Highlights the annotation. The color is different for references
    marked as TODO, and the shade of the color depends on how similar the
    text is to the text in the referenced revision.
    """
    annot = page.addHighlightAnnot(rect)
    color_intensity = ref["similarity"]
    if ref["document"]["TODO"] == "true":
        annot.setColors(stroke=(color_intensity, color_intensity, 0))
    else:
        annot.setColors(stroke=(0, color_intensity, 0))


def set_annot_contents(ref):
    annot_contents = ref["semantics"]["file"] + "\n"\
                     + str(ref["semantics"]["lines"])
    if ref["document"]["TODO"] == "true":
        annot_contents += "\nMarked as TODO"

    revision = ref["document"]["document"]
    annot_contents += "\n" + str(round(100 * float(ref["similarity"]), 2))\
                      + "% " + "match with paragraph in referenced " \
                               "revision (%s)" % revision

    return annot_contents


def find_paragraph_annot(page, section):
    """ Find an annotation belonging to a paragraph,
    or a coverage annotation and returns it if found,
    None otherwise.
    """
    annot = page.firstAnnot

    while annot:
        if annot.info["title"] == section:
            return annot

        annot = annot.next

    return None


def annotate_section(page, rect, ref):
    """ Creates an annotation next to the referenced block if
    it doesn't already exist and fill it with relevant information:
    - Path to file of the reference
    - Line numbers of the reference
    - Percentual match to the text from the referenced revision
    If an annotation already exists, the information is appended.
    """
    annot_contents = set_annot_contents(ref)
    annot = find_paragraph_annot(page, ref["document"]["section"])

    if annot:
        content = annot.info["content"]
        new_content = "\n----------------------------\n" + annot_contents
        annot.setInfo(content=content + new_content)
    else:
        annot = page.addTextAnnot((rect[2] + ANNOT_OFFSET_X, rect[1]),
                                  annot_contents, "Comment")
        annot.setInfo(title=ref["document"]["section"])
        annot.setColors(ANNOT_DEFAULT_COLOR)
    annot.update()


def find_chapter_start(chapter, block):
    if re.search(re.compile("^" + chapter + CHAPTER_START_REGEX), block[4]):
        return True
    return False


def annotate_chapter_coverage(coverage_dict, page, rect, section):
    """ Adds an annotation at the start of a chapter containing
    coverage data, if such annotation doesn't already exist.
    """
    coverage = find_paragraph_annot(page, "coverage")
    if not coverage:
        referenced_section, chapter_covered = \
            paragraph_mapping.find_covered_section(coverage_dict,
                                                   section[0].split("."),
                                                   section[1].split("."))
        total_sections = chapter_covered["total"]
        total_covered = chapter_covered["covered"]
        percentage_covered = round(total_covered / total_sections * 100, 2)

        annot = page.addTextAnnot((rect[2] + ANNOT_OFFSET_X, rect[1]),
                                  "%s/%s sections covered (%s" %
                                  (total_covered, total_sections,
                                   percentage_covered) + "%)", "Graph")
        annot.setInfo(title="coverage")
        annot.update()


def find_referenced_paragraph_page(doc, page_number, toc_page_count,
                                   section, pages_searched,
                                   chapter_start, coverage_dict):
    """ Each page consists of blocks which are segments of text
    or some other type of data. Each block contains four points
    that define that blocks borders, two X and two Y coordinates.
    The top left corner of a standard sized page has coordinates
    x=0, y=0, , the bottom right corner has coordinates x=612, y=792.

    Searches for the start of the referenced chapter, and adds a
    coverage annotation once found. Then, the referenced chapter
    is searched until the referenced paragraph is found.
    Returns the page and coordinates of the referenced paragraph,
    or None if too many pages were searched.
    """
    if pages_searched > MAX_PAGES_TO_SEARCH:
        print("Error @ ref %s:%s, over %s pages searched" %
              (section[0], section[1], MAX_PAGES_TO_SEARCH))
        return None, None

    page = doc[toc_page_count + page_number - 1]
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = re.compile(r"^(?:—\n\()?" + section[1] + r"\)?\n?(?!\d\))")

    for block in blocks:
        if chapter_start:
            result = re.search(regex, block[4])

            if result:
                rect = [block[0], block[1], block[2], block[3]]
                return page, rect
        else:
            chapter_start = find_chapter_start(section[0], block)
            if chapter_start:
                rect = [block[0], block[1], block[2], block[3]]
                annotate_chapter_coverage(coverage_dict, page, rect, section)

    return find_referenced_paragraph_page(doc, page_number + 1,
                                          toc_page_count, section,
                                          pages_searched + 1, chapter_start,
                                          coverage_dict)


def find_toc_page_count(doc):
    """ TOC uses Roman numerals instead of Arabic.
    The last character on each page is the page number,
    Counts the number of pages from the start of the
    document until page 1 is found.
    """
    for i in range(doc.pageCount):
        # page numbering starts from 1 after toc section
        if doc[i].getText().rstrip()[-1] == "1":
            return i
    print("Error: Couldn't find TOC page count")
    raise IndexError


def process_reference(doc, ref, toc_page_count, coverage_dict):
    """ Find the location of the referenced paragraph,
    highlights it and adds an annotation.
    """
    if not ref["error"]:
        section = re.split("[:/]", ref["document"]["section"])

        page_number = find_referenced_section_page_number(doc, section,
                                                          toc_page_count)
        page_rect = find_referenced_paragraph_page(doc, page_number,
                                                   toc_page_count, section,
                                                   0, False, coverage_dict)

        if page_rect[0] is not None and page_rect[1] is not None:
            highlight_section(page_rect[0], page_rect[1], ref)
            annotate_section(page_rect[0], page_rect[1], ref)

        else:
            print("[Error] Couldn't find the corresponding block of %s:%s"
                  % (section[0], section[1]))


def annotate_document(doc, target_pdf_tag, port_num):
    """ Obtains output from paragraph mapping
    and uses it to highlight/annotate referenced sections
    and display coverage
    """
    references, coverage_dict = \
        paragraph_mapping.map_paragraphs_to_target_revision(target_pdf_tag,
                                                            port_num)

    if references:
        print("Highlighting and annotating references in %s.pdf"
              % target_pdf_tag)
        annotate_chapter_coverage(coverage_dict, doc[0],
                                  [0, COVERAGE_ANNOT_Y, COVERAGE_ANNOT_X, 0],
                                  ["", ""])
        toc_page_count = find_toc_page_count(doc)
        for ref in references:
            process_reference(doc, ref, toc_page_count, coverage_dict)

        print("Saving document...")
        # editing a copied PDF is much faster than saving a new PDF
        doc.saveIncr()
    else:
        print("Failed to load references")


def copy_target_pdf(tag):
    """ Creates a copy of a revision in PDF format
    located in papers directory of the draft submodule.
    The copy is saved in the current working directory
    """
    print("Creating a copy of %s.pdf" % tag)
    if tag[-4:].lower() != ".pdf":
        tag += ".pdf"
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                        'draft/papers/', tag)
    copy2(path, os.getcwd())

    renamed_tag = tag.split(".")[0] + "_annotated.pdf"
    os.rename(tag, renamed_tag)

    return fitz.open(renamed_tag)


def main(argv):
    try:
        target_pdf = copy_target_pdf(argv[1].lower())
        if len(argv) > 2:
            port_num = argv[2]
        else:
            port_num = None
        annotate_document(target_pdf, argv[1].lower(), port_num)
    except (RuntimeError, IndexError, FileNotFoundError) as e:
        print(e)
        print("annotatePDF arguments required: \"tag [port number]"
              "\"\ne.g. \"n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
