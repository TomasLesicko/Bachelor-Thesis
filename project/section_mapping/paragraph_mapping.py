import sys
import re
import json
import difflib
from urllib.error import URLError
import chapter_mapping
import time
import os

from chapter_mapping import map_sections

from tools.revision_PDF_to_txt import read_referenced_revision

DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.7

PARAGRAPH_PARSING_REGEX = r"(?:^—?\(?(\d+(?:\.\d+)*)\)?) ([\s\S]+?)(?=(?:^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"
PARAGRAPH_PARSING_REGEX_NUM_ID = r"(\d+(?:\.\d+)*)"

CHAPTER_PARSING_REGEX = r"^(?:Annex )?([A-Z0-9](?:\d)*(?:\.\d+)*)(?: (?:.+\n){0,3}?.*\[(\D\S+)\]$([\s\S]+?))(?=(?:^(?:Annex )?[A-Z0-9](?:\d)*(?:\.\d+)* (?:.+\n){0,3}?.*\[\D\S+\]$)|\Z)"
CHAPTER_PARSING_REGEX_NUM_ID = r"[A-Z0-9](?:\d)*(?:\.\d+)*"


def load_txt_revisions(revision_set, port_num):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        try:
            txt_revision = open("%s.txt" % revision_tag, "r")
            print("\tLoading %s" % revision_tag)
            revisions_text_dict[revision_tag] = txt_revision.read()
        except FileNotFoundError:
            try:
                revisions_text_dict[revision_tag] = read_referenced_revision(revision_tag, port_num)
            except:
                print(
                    "[Error] Missing %s.txt, make sure tika server is running with correct port number" % revision_tag)

    return revisions_text_dict


def find_target_chapter(revision_text, referenced):
    t = revision_text
    for section_id in referenced:
        try:
            t = t[section_id]
        except KeyError:
            return None
    return t["contents"]


def extract_paragraph_from_referenced_revision(revision_text_chapters, referenced_section):
    referenced_chapter = referenced_section[0].split(".")
    referenced_paragraph = referenced_section[1].split(".")

    referenced_chapter_match = find_target_chapter(revision_text_chapters, referenced_chapter)
    if not referenced_chapter_match:
        return None

    referenced_paragraph_match = find_target_chapter(referenced_chapter_match, referenced_paragraph)
    if not referenced_paragraph_match:
        return None

    return referenced_paragraph_match


def find_most_similar_paragraph(similar_paragraphs):
    max_i = 0
    max_ratio = 0
    for i in range(len(similar_paragraphs)):
        if similar_paragraphs[i][2] > max_ratio:
            max_i = i
            max_ratio = similar_paragraphs[i][2]

    return similar_paragraphs[max_i]


def get_paragraph_contents(target_revision_paragraphs, paragraphs, full_id=""):
    for paragraph_id, paragraph_contents in target_revision_paragraphs.items():
        if paragraph_id == "contents":
            paragraphs[full_id] = paragraph_contents
        else:
            if full_id and full_id[-1] != ".":
                full_id += "."
            get_paragraph_contents(paragraph_contents, paragraphs, full_id + paragraph_id)


def target_revision_find_paragraph_id(target_revision_paragraphs, referenced_paragraph_text, threshold,
                                      referenced_revision_tag,
                                      referenced_section, target_section):
    similar_paragraphs = []
    ratios = []

    paragraphs = {}
    get_paragraph_contents(target_revision_paragraphs, paragraphs)

    for paragraph_id, paragraph in paragraphs.items():

        matcher = difflib.SequenceMatcher(None, referenced_paragraph_text, paragraph, autojunk=False)
        ratio1 = matcher.ratio()
        # ratio2 = matcher.quick_ratio()
        # ratio3 = matcher.real_quick_ratio()
        ratios.append(ratio1)

        if ratio1 > threshold:
            similar_paragraphs.append((paragraph_id, paragraph, ratio1))
        # if ratio2 > 0.9:
        # similar_paragraphs.append((c[0], paragraph, ratio2))

    if similar_paragraphs:
        most_similar = find_most_similar_paragraph(similar_paragraphs)
        return most_similar

    return None


def is_in_mapping_cache(referenced_revision_tag, referenced_section, mapping_cache):
    s = ":".join(referenced_section) ## a.b/c ?
    if referenced_revision_tag in mapping_cache and s in mapping_cache[referenced_revision_tag]:
        return mapping_cache[referenced_revision_tag][s]

    return None


def calculate_cached_text_similarity(cache, target_revision_chapters, referenced_paragraph_text):
    target_section = cache.split(":")
    chapters = find_target_chapter(target_revision_chapters, target_section[0].split("."))
    target_paragraph_text = find_target_chapter(chapters, target_section[1].split("."))
    matcher = difflib.SequenceMatcher(None, referenced_paragraph_text, target_paragraph_text,
                                      autojunk=False)
    ratio1 = matcher.ratio()
    return target_section[0], (target_section[1], target_paragraph_text, ratio1)


def map_paragraph_to_target_revision(target_revision_chapters, referenced_paragraph_text,
                                     referenced_revision_tag, referenced_section, section_mapping, mapping_cache):
    cache = is_in_mapping_cache(referenced_revision_tag, referenced_section, mapping_cache)
    if cache:
        print("cached")
        return calculate_cached_text_similarity(cache, target_revision_chapters, referenced_paragraph_text)

    if referenced_revision_tag in section_mapping and referenced_section[0] in section_mapping[referenced_revision_tag]:
        target_section = section_mapping[referenced_revision_tag][referenced_section[0]]
    else:
        print("Could not find %s %s in section mapping, make sure it's up to date" %
              (referenced_revision_tag, referenced_section[0]))
        target_section = None

    if target_section:
        target_chapter = find_target_chapter(target_revision_chapters, target_section.split("."))
        if target_chapter:
            print("not cached")
            return target_section, target_revision_find_paragraph_id(target_chapter, referenced_paragraph_text,
                                                                     DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD,
                                                                     referenced_revision_tag,
                                                                     referenced_section, target_section)

    return None, None


def is_valid_section_format(referenced_section):
    return referenced_section is not None and len(referenced_section) == 2


def found_referenced_paragraph(referenced_paragraph_text):
    return referenced_paragraph_text is not None


def process_reference_error(reference, ref_errors, msg):
    reference["error"] = msg
    ref_errors.append(reference)


def map_reference_same_revision(reference):
    reference["similarity"] = 1.0
    reference["error"] = ""


def save_to_cache(reference_revision_tag, referenced_section, target_section, mapping_cache):
    if reference_revision_tag in mapping_cache:
        mapping_cache[reference_revision_tag][referenced_section] = target_section
    else:
        mapping_cache[reference_revision_tag] = {}
        mapping_cache[reference_revision_tag][referenced_section] = target_section


def map_reference_different_revision(reference, target_revision_chapters, target_revision_tag,
                                     referenced_paragraph_text,
                                     referenced_revision_tag, referenced_section,
                                     ref_errors, section_mapping, mapping_cache):
    target_chapter_id, mapped_reference_results = map_paragraph_to_target_revision(target_revision_chapters,
                                                                                   referenced_paragraph_text,
                                                                                   referenced_revision_tag,
                                                                                   referenced_section,
                                                                                   section_mapping, mapping_cache)
    if mapped_reference_results:
        section = target_chapter_id + ":" + mapped_reference_results[0]
        reference["document"]["section"] = section
        reference["similarity"] = mapped_reference_results[2]
        reference["error"] = ""
        save_to_cache(referenced_revision_tag, ":".join(referenced_section), section, mapping_cache)
    else:
        print("erronous")
        process_reference_error(reference, ref_errors, "Failed to locate referenced section in target"
                                                       " revision (%s)" % target_revision_tag)


def map_reference(reference, revision_text_dict_chapters, target_revision_tag, ref_errors, section_mapping,
                  mapping_cache):
    referenced_revision_tag = reference["document"]["document"].lower()
    referenced_section = re.split("[:/]", reference["document"]["section"])

    if not is_valid_section_format(referenced_section):
        process_reference_error(reference, ref_errors, "Unsupported section format")
        return

    referenced_paragraph_text = extract_paragraph_from_referenced_revision(
        revision_text_dict_chapters[referenced_revision_tag], referenced_section)
    if not found_referenced_paragraph(referenced_paragraph_text):
        process_reference_error(reference, ref_errors, "Failed to locate referenced section in referenced"
                                                       " revision (%s)" % referenced_revision_tag)
        return

    if referenced_revision_tag == target_revision_tag:
        print("same rev")
        map_reference_same_revision(reference)
    else:
        map_reference_different_revision(reference, revision_text_dict_chapters[target_revision_tag],
                                         target_revision_tag, referenced_paragraph_text,
                                         referenced_revision_tag, referenced_section,
                                         ref_errors, section_mapping, mapping_cache)


def get_paragraphs_rec(revision_text_dict, parent_paragraph_id=""):
    for paragraph_id, text in revision_text_dict.items():
        if not paragraph_id == "contents":
            revision_text_dict[paragraph_id] = {}
            subparagraph_id = 1

            par_open = r""
            par_close = r""
            if parent_paragraph_id:
                par_open += r"—\("
                par_close += r"\)"

            r = r"^" + par_open + parent_paragraph_id + str(paragraph_id) + par_close + r" [\s\S]+?(?=^—\(" + \
                parent_paragraph_id + str(paragraph_id) + r"\.1\) |\Z)"
            res = re.match(r, text, re.M)
            revision_text_dict[paragraph_id]["contents"] = res[0]
            text = text[res.end():]

            if text:
                subparagraph = paragraph_id + r"\." + str(subparagraph_id)
                next_subparagraph = paragraph_id + r"\." + str(subparagraph_id + 1)
                r = r"^—\(" + parent_paragraph_id + subparagraph + r"\) [\s\S]+?(?=^—\(" + parent_paragraph_id \
                    + next_subparagraph + r"\) |\Z)"
                res = re.match(r, text, re.M)

                while res:
                    revision_text_dict[paragraph_id][str(subparagraph_id)] = res[0]
                    subparagraph_id += 1
                    text = text[res.end():]
                    subparagraph = paragraph_id + r"\." + str(subparagraph_id)
                    next_subparagraph = paragraph_id + r"\." + str(subparagraph_id + 1)
                    r = r"^—\(" + parent_paragraph_id + subparagraph + r"\) [\s\S]+?(?=^—\(" + parent_paragraph_id \
                        + next_subparagraph + r"\) |\Z)"
                    res = re.match(r, text, re.M)

            get_paragraphs_rec(revision_text_dict[paragraph_id], parent_paragraph_id + paragraph_id + ".")


def get_paragraphs(revision_text_dict, text):
    paragraph_id = 1
    r = r"^[\s\S]*?(?=^1 |\Z)"
    res = re.match(r, text, re.M)
    revision_text_dict["contents"] = res[0]
    text = text[res.end():]

    if res:
        r = r"^" + str(paragraph_id) + r" [\s\S]+?(?=^" + str(paragraph_id + 1) + r" |\Z)"
        res = re.match(r, text, re.M)
    while res:
        revision_text_dict[str(paragraph_id)] = res[0]
        paragraph_id += 1
        text = text[res.end():]

        r = r"^" + str(paragraph_id) + r" [\s\S]+?(?=^" + str(paragraph_id + 1) + r" |\Z)"
        res = re.match(r, text, re.M)

    if revision_text_dict:
        get_paragraphs_rec(revision_text_dict)


def split_chapters_rec(revision_text_dict, parent_chapter_id=""):
    for chapter_id, text in revision_text_dict.items():
        revision_text_dict[chapter_id] = {}
        subchapter_id = 1

        if not chapter_id == "contents":
            r = r"(?:^" + parent_chapter_id + str(chapter_id) + r" (?:.+\n){0,2}?.*?\[[^\dN].*?\]$)\n+([\s\S]*?)(?=^" + \
                parent_chapter_id + str(chapter_id) + r"\.1 (?:.+\n){0,2}?.*?\[[^\dN].*?\]$|\Z)"
            res = re.match(r, text, re.M)
            revision_text_dict[chapter_id]["contents"] = res[1]
            text = text[res.end():]

            if text:
                subchapter = chapter_id + r"\." + str(subchapter_id)
                next = chapter_id + r"\." + str(subchapter_id + 1)
                r = r"^" + parent_chapter_id + subchapter + r" (?:\n.+){0,2}?.*?\[([^\dN].*?)\]$([\s\S]+?)(?=^" + \
                    parent_chapter_id + next + r" (?:\n.+){0,2}?.*?\[[^\dN].*?\]$|\Z)"
                res = re.match(r, text, re.M)

                while res:
                    revision_text_dict[chapter_id][str(subchapter_id)] = res[0]
                    subchapter_id += 1
                    text = text[res.end():]
                    subchapter = chapter_id + r"\." + str(subchapter_id)
                    next = chapter_id + r"\." + str(subchapter_id + 1)
                    r = r"^" + parent_chapter_id + subchapter + r" (?:\n.+){0,2}?.*?\[([^\dN].*?)\]$([\s\S]+?)(?=^" + parent_chapter_id + next + r" .*(?:\n.+){0,2}?.*?\[[^\dN].*?\]$|\Z)"
                    res = re.match(r, text, re.M)

            split_chapters_rec(revision_text_dict[chapter_id], parent_chapter_id + chapter_id + ".")
        elif text:
            get_paragraphs(revision_text_dict[chapter_id], text)


def split_revisions_into_chapters(revision_text_dict):
    print("Splitting revision texts into chapters")

    for revision_tag, revision_text in revision_text_dict.items():
        print("Splitting %s" % revision_tag)
        revision_text_dict[revision_tag] = {}
        chapter_id = 1
        r = r"^" + str(chapter_id) + r" .+(?:\n.+){0,2}?.*\[(\D.*)\]$\n+([\s\S]+?)(?=^" + str(
            chapter_id + 1) + r" .+(?:\n.+){0,2}?.*\[\D.+\]$|\Z)"
        res = re.search(r, revision_text, re.M)

        while res:
            revision_text_dict[revision_tag][str(chapter_id)] = res[0]
            chapter_id += 1
            revision_text = revision_text[res.end():]
            r = r"^" + str(chapter_id) + r" .+(?:\n.+){0,2}?.*\[(\D.*)\]$([\s\S]+?)(?=^" + str(
                chapter_id + 1) + r" .+(?:\n.+){0,2}?.*\[\D.+\]$|\Z)"
            res = re.match(r, revision_text, re.M)

        split_chapters_rec(revision_text_dict[revision_tag])

    with open("revision_dict.json", "w") as rd:
        json.dump(revision_text_dict, rd, indent=4)

    return revision_text_dict


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


def map_referenced_paragraphs(references, revision_dict, target_revision_tag, ref_errors, section_mapping,
                              mapping_cache):
    print("Mapping references to %s" % target_revision_tag)
    for reference in references:
        map_reference(reference, revision_dict, target_revision_tag, ref_errors, section_mapping, mapping_cache)


def load_revision_dict(revision_text_dict):
    try:
        with open("revision_dict.json", "r") as test:
            revision_dict_chapters = json.loads(test.read())
    except FileNotFoundError:
        revision_dict_chapters = split_revisions_into_chapters(revision_text_dict)

    return revision_dict_chapters


def write_errors(ref_errors):
    with open("referenceErrors.json", "w") as ref_error_json:
        if ref_errors:
            print("Some references could not be mapped, for details, check referenceErrors.json")
            json.dump(ref_errors, ref_error_json, indent=4)


def write_cache(mapping_cache, target_revision_tag):
    with open("mapping_cache_%s.json" % target_revision_tag, "w") as cache:
        if mapping_cache:
            json.dump(mapping_cache, cache, indent=4)


def process_references(references, revision_dict, target_revision_tag, section_mapping, mapping_cache):
    ref_errors = []
    map_referenced_paragraphs(references, revision_dict, target_revision_tag, ref_errors, section_mapping,
                              mapping_cache)
    write_errors(ref_errors)
    write_cache(mapping_cache, target_revision_tag)


def save_mapped_references(target_revision_tag, references):
    with open("references_mapped_%s.json" % target_revision_tag, "w") as mapped_references:
        print("Saving mapped references")
        json.dump(references, mapped_references, indent=4)


def load_section_mapping(target_revision_tag, references):
    try:
        with open("section_mapping_to_%s.json" % target_revision_tag, "r") as section_mapping_file:
            section_mapping = json.load(section_mapping_file)
    except FileNotFoundError:
        print("Couldn't find section mapping to %s, attempting to create it" % target_revision_tag)
        map_sections(target_revision_tag, references)
        try:
            with open("section_mapping_to_%s.json" % target_revision_tag, "r") as section_mapping_file:
                section_mapping = json.load(section_mapping_file)
        except FileNotFoundError:
            print("Failed to create section mapping to %s" % target_revision_tag)
            raise
    return section_mapping


def load_mapping_cache(target_revision_tag):
    try:
        with open("mapping_cache_%s.json" % target_revision_tag, "r") as cache:
            return json.loads(cache.read())
    except FileNotFoundError:
        return {}


def map_paragraphs_to_target_revision(target_revision_tag, port_num):
    references = chapter_mapping.load_references()

    revision_set = set()
    revision_set.add(target_revision_tag)
    chapter_mapping.find_referenced_revision_tags(references, revision_set)

    section_mapping = load_section_mapping(target_revision_tag, references)
    map_sections(target_revision_tag, references)
    revision_text_dict = load_txt_revisions(revision_set, port_num)
    if len(revision_text_dict) == len(revision_set):  # all revisions loaded correctly
        mapping_cache = load_mapping_cache(target_revision_tag)
        revision_dict = load_revision_dict(revision_text_dict)

        if len(revision_dict) != len(revision_set):
            revision_dict = split_revisions_into_chapters(revision_text_dict)

        process_references(references, revision_dict, target_revision_tag, section_mapping, mapping_cache)
        save_mapped_references(target_revision_tag, references)

        return references

    return None


def main(argv):
    try:
        if len(sys.argv) > 2:
            port_num = argv[2]
        else:
            port_num = None
        references = map_paragraphs_to_target_revision(sys.argv[1], port_num)
    except (IndexError, FileNotFoundError, URLError):
        print("Usage: \"paragraphMapping.py <tag> <port number>\"\ne.g. \"paragraphMapping.py n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
