import sys
import re
import json
import difflib
from urllib.error import URLError
import chapter_mapping

sys.path.append("../tools")
from revision_PDF_to_txt import read_referenced_revision

DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.7
DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD = 0.55
DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE = 0.05

PARAGRAPH_PARSING_REGEX = r"(?:^—?\(?(\d+(?:\.\d+)*)\)?) ([\s\S]+?)(?=(?:^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"

#NEW_PAGE_REDUNDANT_CHARS = r"(?:(?:^\d+\)[\s\S]+?)?.*\s+c©ISO\/IEC N\d+)"

PARAGRAPH_PARSING_REGEX_NUM_ID = r"(\d+(?:\.\d+)*)"

CHAPTER_PARSING_REGEX = r"^(?:Annex )?([A-Z0-9](?:\d)*(?:\.\d+)*)(?: (?:.+\n){0,3}?.*\[(\D\S+)\]$([\s\S]+?))(?=(?:^(?:Annex )?[A-Z0-9](?:\d)*(?:\.\d+)* (?:.+\n){0,3}?.*\[\D\S+\]$)|\Z)"
CHAPTER_PARSING_REGEX_NUM_ID = r"[A-Z0-9](?:\d)*(?:\.\d+)*"
#CHAPTER_PARSING_REGEX_BRACKET_ID = r"(.+)"


def load_txt_revisions(revision_set, port_num):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        try:
            txt_revision = open("%s.txt" % revision_tag, "r")
            print("\tLoading %s" % revision_tag)
            revisions_text_dict[revision_tag] = txt_revision.read()
        except FileNotFoundError:
            revisions_text_dict[revision_tag] = read_referenced_revision(revision_tag, port_num)

    return revisions_text_dict


def find_referenced_chapter_text(revision_text, referenced_chapter):
    referenced_chapter_text = revision_text[referenced_chapter]
    return referenced_chapter_text


def find_referenced_paragraph_text(referenced_chapter_text, referenced_paragraph):
    # TODO return a dict of all paragraphs to access later, would be faster if multiple references
    # reference a paragraph in this chapter
    referenced_paragraph_regex = PARAGRAPH_PARSING_REGEX.replace(PARAGRAPH_PARSING_REGEX_NUM_ID,
                                                                 re.escape(referenced_paragraph), 1)
    referenced_paragraph_text = re.findall(referenced_paragraph_regex, referenced_chapter_text, re.M)
    # TODO paragraph regex matches everything until next identifier, may cause issues
    return referenced_paragraph_text


def extract_paragraph_from_referenced_revision(revision_text_chapters, referenced_section):
    referenced_chapter = referenced_section[0]
    referenced_paragraph = referenced_section[1]

    referenced_chapter_match = find_referenced_chapter_text(revision_text_chapters, referenced_chapter)
    if not referenced_chapter_match:
        return None, None

    referenced_chapter_bracket_id = referenced_chapter_match[0]
    referenced_chapter_text = referenced_chapter_match[1]

    referenced_paragraph_match = find_referenced_paragraph_text(referenced_chapter_text, referenced_paragraph)
    if not referenced_paragraph_match:
        return None, None

    return referenced_paragraph_match[0][0], referenced_chapter_bracket_id


def find_most_similar_paragraph(similar_paragraphs):
    max_i = 0
    max_ratio = 0
    for i in range(len(similar_paragraphs)):
        if similar_paragraphs[i][2] > max_ratio:
            max_i = i
            max_ratio = similar_paragraphs[i][2]

    return similar_paragraphs[max_i]


def target_revision_find_paragraph_id(target_revision_chapters, paragraph_text, threshold, referenced_revision_tag,
                                      referenced_section):
    if referenced_section[0] == "12.1" and referenced_section[1] == "4.8":
        x = 0
    similar_paragraphs = []
    for chapter in target_revision_chapters:
        if chapter[0] == "class.default.ctor":
            x = 0
        target_chapter_paragraphs = re.findall(PARAGRAPH_PARSING_REGEX, chapter[1], re.M)
        # TODO match paragraphs correctly if they're split by new page
        ratios = []

        for paragraph in target_chapter_paragraphs:

            matcher = difflib.SequenceMatcher(None, paragraph_text, paragraph[1], autojunk=False)
            ratio1 = matcher.ratio()
            # ratio2 = matcher.quick_ratio()
            # ratio3 = matcher.real_quick_ratio()
            ratios.append(ratio1)

            if ratio1 > threshold:
                similar_paragraphs.append((chapter[0], paragraph, ratio1))
            # if ratio2 > 0.9:
                # similar_paragraphs.append((c[0], paragraph, ratio2))

    if similar_paragraphs:
        most_similar = find_most_similar_paragraph(similar_paragraphs)
        return most_similar

    # if no similar paragraph was found, retry with lower ratio threshold
    # if threshold > DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD:
    #     print("\tCouldn't match referenced paragraph, retrying with lower match ratio (%s)\n\tReference:\n\t%s %s:%s"
    #           % (round(threshold - DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, 2), referenced_revision_tag,
    #              referenced_section[0],
    #              referenced_section[1]))
    #     return target_revision_find_paragraph_id(target_revision_chapters, paragraph_text,
    #                                              round(threshold - DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, 2),
    #                                              referenced_revision_tag, referenced_section)
    #
    # print("\tFailed to match referenced paragraph with minimum allowed match ratio (%s)\n\tReference: %s %s:%s" %
    #       (DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD, referenced_revision_tag, referenced_section[0],
    #        referenced_section[1]))
    return ""


def target_revision_find_section_id(target_revision_chapters, referenced_paragraph_text, referenced_chapter_id,
                                    referenced_revision_tag, referenced_section):
    presumed_target_text_chapter = None
    for chapter_id, chapter_contents in target_revision_chapters.items():
        if chapter_id == "D.16":
            x = 0
        if chapter_contents[0] == referenced_chapter_id:
            presumed_target_text_chapter = (chapter_id, chapter_contents[1])
            break
    if presumed_target_text_chapter:
        chapters = [presumed_target_text_chapter]
    else:
        cc = referenced_chapter_id.split(".")
        chapters = []
        if len(cc) > 1: # no point in searching if it was already a full chapter
            for chapter_id, chapter_contents in target_revision_chapters.items():
                if chapter_contents[0].split(".")[0] == cc[0]:
                    chapters.append((chapter_id, chapter_contents[1]))

        print("Error new %s:%s" % (referenced_section[0], referenced_section[1]))

    return target_revision_find_paragraph_id(chapters, referenced_paragraph_text,
                                             DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD, referenced_revision_tag,
                                             referenced_section)


def is_valid_section_format(referenced_section):
    return referenced_section is not None and len(referenced_section) == 2


def found_referenced_paragraph(referenced_paragraph_text, referenced_chapter_bracket_id):
    return referenced_paragraph_text is not None and referenced_chapter_bracket_id is not None


def process_reference_error(reference, ref_errors, msg):
    reference["error"] = msg
    ref_errors.append(reference)


def map_reference_same_revision(reference):
    reference["similarity"] = 1.0
    reference["error"] = ""


def map_reference_different_revision(reference, target_revision_chapters, target_revision_tag, referenced_paragraph_text,
                                     referenced_chapter_bracket_id, referenced_revision_tag, referenced_section,
                                     ref_errors):
    target_revision_section_id = target_revision_find_section_id(target_revision_chapters,
                                                                 referenced_paragraph_text,
                                                                 referenced_chapter_bracket_id,
                                                                 referenced_revision_tag, referenced_section)
    if target_revision_section_id:
        reference["document"]["section"] = target_revision_section_id[0] + ":" + target_revision_section_id[1][0]
        reference["similarity"] = target_revision_section_id[2]
        reference["error"] = ""
    else:
        process_reference_error(reference, ref_errors, "Failed to locate referenced section in target"
                                                       " revision (%s)" % target_revision_tag)


def map_reference(reference, revision_text_dict_chapters, target_revision_tag, ref_errors):
    referenced_revision_tag = reference["document"]["document"].lower()
    referenced_section = re.split("[:/]", reference["document"]["section"])

    if not is_valid_section_format(referenced_section):
        process_reference_error(reference, ref_errors, "Unsupported section format")
        return

    referenced_paragraph_text, referenced_chapter_bracket_id = extract_paragraph_from_referenced_revision(
        revision_text_dict_chapters[referenced_revision_tag], referenced_section)
    if not found_referenced_paragraph(referenced_paragraph_text, referenced_chapter_bracket_id):
        process_reference_error(reference, ref_errors, "Failed to locate referenced section in referenced"
                                                       " revision (%s)" % referenced_revision_tag)
        return

    if referenced_revision_tag == target_revision_tag:
        map_reference_same_revision(reference)
    else:
        map_reference_different_revision(reference, revision_text_dict_chapters[target_revision_tag], target_revision_tag, referenced_paragraph_text,
                                         referenced_chapter_bracket_id, referenced_revision_tag, referenced_section,
                                         ref_errors)


def get_chapters(revision_text_dict):
    print("Splitting revision texts into chapters")
    revision_chapters_dict = {}
    for revision_tag, revision_text in revision_text_dict.items():
        referenced_chapters = re.findall(CHAPTER_PARSING_REGEX, revision_text, re.M)
        chapter_dict = {}
        for entry in referenced_chapters:
            chapter_dict[entry[0]] = (entry[1], entry[2])
        revision_chapters_dict[revision_tag] = chapter_dict

    return revision_chapters_dict


def map_referenced_paragraphs(references, revision_text_dict_chapters, target_revision_tag, ref_errors):
    print("Mapping references to %s" % target_revision_tag)
    i = 1
    for reference in references:
        print("reference no.%s" % i)
        i += 1
        map_reference(reference, revision_text_dict_chapters, target_revision_tag, ref_errors)


def process_references(references, revision_text_dict, target_revision_tag):
    with open("referenceErrors.json", 'w') as ref_error_json:
        ref_errors = []
        revision_text_dict_chapters = get_chapters(revision_text_dict)
        map_referenced_paragraphs(references, revision_text_dict_chapters, target_revision_tag, ref_errors)
        if ref_errors:
            print("Some references could not be mapped, for details, check referenceErrors.json")
            json.dump(ref_errors, ref_error_json, indent=4)


def save_mapped_references(target_revision_tag, references):
    with open("references_mapped_%s.json" % target_revision_tag, "w") as mapped_references:
        print("Saving mapped references")
        json.dump(references, mapped_references, indent=4)


def map_paragraphs_to_target_revision(target_revision_tag, port_num):
    references = chapter_mapping.load_references()

    revision_set = set()
    revision_set.add(target_revision_tag)
    chapter_mapping.find_referenced_revision_tags(references, revision_set)

    revision_text_dict = load_txt_revisions(revision_set, port_num)

    process_references(references, revision_text_dict, target_revision_tag)
    save_mapped_references(target_revision_tag,references)

    return references


def main(argv):
    try:
        # TODO optional port num arg
        references = map_paragraphs_to_target_revision(sys.argv[1], sys.argv[2])  # TODO argparse lib, progressbar?
    except (IndexError, FileNotFoundError, URLError):
        print("Usage: \"paragraphMapping.py <tag> <port number>\"\ne.g. \"paragraphMapping.py n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
