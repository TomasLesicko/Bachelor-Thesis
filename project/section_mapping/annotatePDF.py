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


def get_toc_compatible_chapter(chapter):
    regex = r"(^[A-Z0-9](?:\d)*(?:\.\d+)?).*"
    result = re.search(regex, chapter)

    return result[1]


def find_section_page(doc, section, toc_page_count):
    # TOC only contains subsections depth 1 (13.1 not 13.1.1 etc.)
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
    annot = page.addHighlightAnnot(rect)
    color_intensity = ref["similarity"]
    if ref["document"]["TODO"] == "true":
        annot.setColors(stroke=(color_intensity, color_intensity, 0))
    else:
        annot.setColors(stroke=(0, color_intensity, 0))


def set_annot_contents(ref):
    annot_contents = ref["semantics"]["file"] + "\n" + str(ref["semantics"]["lines"])
    if ref["document"]["TODO"] == "true":
        annot_contents += "\nMarked as TODO"

    revision = ref["document"]["document"]
    annot_contents += "\n" + str(round(100 * float(ref["similarity"]), 2)) + "% " + \
                      "match with paragraph in referenced revision (%s)" % revision

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
        annot.setInfo(content=content + new_content)
    else:
        annot = page.addTextAnnot((rect[2] + ANNOT_OFFSET_X, rect[1]), annot_contents, "Comment")
        annot.setInfo(title=ref["document"]["section"])
        annot.setColors(ANNOT_DEFAULT_COLOR)
    annot.update()


def find_chapter_start(chapter, block):
    if re.search(re.compile("^" + chapter + CHAPTER_START_REGEX), block[4]):
        return True
    return False


def annotate_chapter_coverage(coverage_dict, page, rect, section):
    coverage = find_paragraph_annot(page, "coverage")
    if not coverage:
        referenced_section, chapter_covered = paragraph_mapping.find_covered_section(coverage_dict,
                                                                                     section[0].split("."),
                                                                                     section[1].split("."))
        total_sections = chapter_covered["total"]
        total_covered = chapter_covered["covered"]
        percentage_covered = round(total_covered / total_sections * 100, 2)

        annot = page.addTextAnnot((rect[2] + ANNOT_OFFSET_X, rect[1]),
                                  "%s/%s sections covered (%s" %
                                  (total_covered, total_sections, percentage_covered) + "%)", "Graph")
        annot.setInfo(title="coverage")
        annot.update()


def find_referenced_paragraph_page(doc, page_number, toc_page_count, section, pages_searched, chapter_start,
                                   coverage_dict):
    if pages_searched > 200:
        print("Error @ ref %s:%s, over 200 pages searched" % (section[0], section[1]))
        return None, None

    page = doc[toc_page_count + page_number - 1]
    blocks = page.getTextBlocks(flags=fitz.TEXT_INHIBIT_SPACES)
    regex = re.compile(r"^(?:—\n\()?" + section[1] + r"\)?\n")

    for block in blocks:
        if chapter_start:
            result = re.search(regex, block[4])

            if result:
                rect = [block[0], block[1], block[2], block[3]]

                return page, rect
        else:
            chapter_start = find_chapter_start(section[0], block)
            if chapter_start:
                annotate_chapter_coverage(coverage_dict, page, [block[0], block[1], block[2], block[3]], section)

    return find_referenced_paragraph_page(doc, page_number + 1, toc_page_count, section, pages_searched + 1,
                                          chapter_start, coverage_dict)


def find_toc_page_count(doc):
    for i in range(doc.pageCount):
        if doc[i].getText().rstrip()[-1] == "1":  # page numbering starts from 1 after toc section
            return i
    print("Error: Couldn't find TOC page count")
    raise IndexError


def process_reference(doc, ref, toc_page_count, coverage_dict):
    if not ref["error"]:
        section = re.split("[:/]", ref["document"]["section"])

        page_number = find_referenced_section_page_number(doc, section, toc_page_count)
        page_rect = find_referenced_paragraph_page(doc, page_number, toc_page_count, section, 0, False, coverage_dict)

        if page_rect[0] is not None and page_rect[1] is not None:
            highlight_section(page_rect[0], page_rect[1], ref)
            annotate_section(page_rect[0], page_rect[1], ref)

        else:
            print("[Error] Couldn't find the corresponding block of %s:%s" % (section[0], section[1]))


def annotate_document(doc, target_pdf_tag, port_num):
    references, coverage_dict = paragraph_mapping.map_paragraphs_to_target_revision(target_pdf_tag, port_num)

    if references:
        print("Highlighting and annotating references in %s.pdf" % target_pdf_tag)
        annotate_chapter_coverage(coverage_dict, doc[0], [0, COVERAGE_ANNOT_Y, COVERAGE_ANNOT_X, 0], ["", ""])
        toc_page_count = find_toc_page_count(doc)
        for ref in references:
            process_reference(doc, ref, toc_page_count, coverage_dict)

        print("Saving document...")
        doc.saveIncr()  # editing a copied PDF is much faster than saving a new PDF
    else:
        print("Failed to load references")


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
        target_pdf = copy_target_pdf(argv[1].lower())
        if len(argv) > 2:
            port_num = argv[2]
        else:
            port_num = None
        annotate_document(target_pdf, argv[1].lower(), port_num)
    except (RuntimeError, IndexError, FileNotFoundError) as e:
        print(e)
        print("annotatePDF arguments required: \"tag [port number]\"\ne.g. \"n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
