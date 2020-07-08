import sys
import re
import json
import difflib
from urllib.error import URLError
from requests.exceptions import ConnectionError
import chapter_mapping
import os
import time
from random import randint
from tools.revision_PDF_to_txt import read_referenced_revision

DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.7

PAGE_SPLIT_REGEX = r"(?:^(?:\d{1,3}\)[\s\S]+?)?§ [\d\.]+ \d{1,4}\s+[c©]{1,2}\s*ISO\/IEC N\d{1,4}\s+)?"


def load_txt_revisions(revision_set, port_num):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        try:
            txt_revision = open("tools/%s.txt" % revision_tag, "r")
            print("\tLoading %s.txt" % revision_tag)
            revisions_text_dict[revision_tag] = txt_revision.read()
        except FileNotFoundError:
            print("Couldn't find {0}.txt, attempting to create from {0}.pdf".format(revision_tag))
            try:
                if port_num:
                    txt_revision = read_referenced_revision(revision_tag, port_num, "tools/")
                    if txt_revision:
                        revisions_text_dict[revision_tag] = txt_revision
                else:
                    print("Failed to load %s.txt, make sure tika server is running and rerun the script "
                          "with the correct port number as second argument" % revision_tag)
            except ConnectionError:
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


def target_revision_find_paragraph_id(target_revision_paragraphs, referenced_paragraph_text, threshold):
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
    s1 = ":".join(referenced_section)
    s2 = "/".join(referenced_section)
    if referenced_revision_tag in mapping_cache:
        cache_tag = mapping_cache[referenced_revision_tag]
        if s1 in cache_tag:
            return cache_tag[s1]
        if s2 in cache_tag:
            return cache_tag[s2]

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
            return target_section, target_revision_find_paragraph_id(target_chapter, referenced_paragraph_text,
                                                                     DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD)

    return None, None


def is_valid_section_format(referenced_section):
    return referenced_section is not None and len(referenced_section) == 2


def found_referenced_paragraph(referenced_paragraph_text):
    return referenced_paragraph_text is not None


def process_reference_error(reference, ref_errors, msg):
    reference["error"] = msg
    ref_errors.append(reference)


def map_reference_same_revision(reference, coverage_dict, referenced_section):
    reference["similarity"] = 1.0
    reference["error"] = ""
    update_coverage_dict(coverage_dict, referenced_section[0].split("."), referenced_section[1].split("."))


def save_to_cache(reference_revision_tag, referenced_section, target_section, mapping_cache):
    if reference_revision_tag in mapping_cache:
        mapping_cache[reference_revision_tag][referenced_section] = target_section
    else:
        mapping_cache[reference_revision_tag] = {}
        mapping_cache[reference_revision_tag][referenced_section] = target_section


def find_covered_section(coverage_dict, chapter_ids, paragraph_ids):
    referenced_section = coverage_dict

    if chapter_ids[0]:  # empty string is passed when annotating the document
        for chapter_id in chapter_ids:
            referenced_section = referenced_section[str(chapter_id)]

        referenced_section = referenced_section["contents"]

    chapter_covered = referenced_section

    if paragraph_ids[0]:  # empty string is passed when annotating the document
        for paragraph_id in paragraph_ids:
            referenced_section = referenced_section[str(paragraph_id)]

    return referenced_section, chapter_covered


def update_coverage_dict(coverage_dict, chapter_ids, paragraph_ids):
    referenced_section, chapter_covered = find_covered_section(coverage_dict, chapter_ids, paragraph_ids)

    if not referenced_section["contents"]:
        referenced_section["contents"] = True
        coverage_dict["covered"] += 1
        chapter_covered["covered"] += 1


def map_reference_different_revision(reference, target_revision_chapters, target_revision_tag,
                                     referenced_paragraph_text,
                                     referenced_revision_tag, referenced_section,
                                     ref_errors, section_mapping, mapping_cache, coverage_dict):
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
        update_coverage_dict(coverage_dict, target_chapter_id.split("."), mapped_reference_results[0].split("."))

    else:
        if referenced_revision_tag in section_mapping \
                and referenced_section[0] in section_mapping[referenced_revision_tag]:
            process_reference_error(reference, ref_errors, "Failed to locate referenced paragraph in target"
                                                           " revision (%s) chapter %s" % (target_revision_tag,
                                                                                          section_mapping[
                                                                                              referenced_revision_tag]
                                                                                          [referenced_section[0]]))
        else:
            process_reference_error(reference, ref_errors, "Failed to locate referenced chapter in target"
                                                           " revision (%s)" % target_revision_tag)


def map_reference(reference, revision_text_dict_chapters, target_revision_tag, ref_errors, section_mapping,
                  mapping_cache, coverage_dict):
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
        map_reference_same_revision(reference, coverage_dict, referenced_section)
    else:
        map_reference_different_revision(reference, revision_text_dict_chapters[target_revision_tag],
                                         target_revision_tag, referenced_paragraph_text,
                                         referenced_revision_tag, referenced_section,
                                         ref_errors, section_mapping, mapping_cache, coverage_dict)


def set_regex_parentheses(parent_paragraph_id):
    par_open = r""
    par_close = r""
    if parent_paragraph_id:
        par_open += r"—\("
        par_close += r"\)"

    return par_open, par_close


def parse_subparagraph_contents(parent_paragraph_id, paragraph_id, subparagraph_id, text):
    subparagraph = parent_paragraph_id + paragraph_id + r"\." + str(subparagraph_id)
    next_subparagraph = parent_paragraph_id + paragraph_id + r"\." + str(subparagraph_id + 1)
    r = r"(^—\(" + subparagraph + r"\) [\s\S]+?)" + PAGE_SPLIT_REGEX + r"(?=^—\(" + \
        next_subparagraph + r"\) |\Z)"

    return re.match(r, text, re.M)


def parse_this_paragraph_contents(parent_paragraph_id, paragraph_id, text):
    par_open, par_close = set_regex_parentheses(parent_paragraph_id)
    r = r"(^" + par_open + parent_paragraph_id + str(paragraph_id) + par_close + r" [\s\S]+?)" + \
        PAGE_SPLIT_REGEX + r"(?=^—\(" + parent_paragraph_id + str(paragraph_id) + r"\.1\) |\Z)"

    return re.match(r, text, re.M)


def split_paragraphs_rec(revision_text_dict, parent_paragraph_id=""):
    for paragraph_id, text in revision_text_dict.items():
        if not paragraph_id == "contents":
            revision_text_dict[paragraph_id] = {}
            subparagraph_id = 1

            res = parse_this_paragraph_contents(parent_paragraph_id, paragraph_id, text)
            revision_text_dict[paragraph_id]["contents"] = res[1]
            text = text[res.end():]

            if text:
                res = parse_subparagraph_contents(parent_paragraph_id, paragraph_id, subparagraph_id, text)
                while res:
                    revision_text_dict[paragraph_id][str(subparagraph_id)] = res[1]
                    text = text[res.end():]
                    subparagraph_id += 1
                    res = parse_subparagraph_contents(parent_paragraph_id, paragraph_id, subparagraph_id, text)

            split_paragraphs_rec(revision_text_dict[paragraph_id], parent_paragraph_id + paragraph_id + ".")


def parse_paragraph(paragraph_id, text):
    r = r"^" + str(paragraph_id) + r" [\s\S]+?(?=^" + str(paragraph_id + 1) + r" |\Z)"
    return re.match(r, text, re.M)


def split_paragraphs(revision_text_dict, text):
    paragraph_id = 1
    r = r"^[\s\S]*?(?=^1 |\Z)"
    res = re.match(r, text, re.M)
    revision_text_dict["contents"] = res[0]
    text = text[res.end():]

    res = parse_paragraph(paragraph_id, text)

    while res:
        revision_text_dict[str(paragraph_id)] = res[0]
        text = text[res.end():]
        paragraph_id += 1
        res = parse_paragraph(paragraph_id, text)

    if revision_text_dict:
        split_paragraphs_rec(revision_text_dict)


def parse_chapter_contents(parent_chapter_id, chapter_id, text):
    r = r"^" + parent_chapter_id + str(chapter_id) + r" (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$\n+([\s\S]*?)(?=^" \
        + parent_chapter_id + str(chapter_id) + r"\.1 (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$|\Z)"

    return re.match(r, text, re.M)


def parse_subchapter_contents(parent_chapter_id, chapter_id, subchapter_id, text):
    subchapter = parent_chapter_id + chapter_id + r"\." + str(subchapter_id)
    next_subchapter = parent_chapter_id + chapter_id + r"\." + str(subchapter_id + 1)
    r = r"^" + subchapter + r" (?:.*\n){0,2}?.*?\[([^\d\sN].*?)\]$\n+([\s\S]*?)(?=^" + next_subchapter + \
        r" (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$|\Z)"

    return re.match(r, text, re.M)


def split_chapters_rec(revision_text_dict, parent_chapter_id=""):
    for chapter_id, text in revision_text_dict.items():
        revision_text_dict[chapter_id] = {}
        subchapter_id = 1

        if not chapter_id == "contents":
            res = parse_chapter_contents(parent_chapter_id, chapter_id, text)
            revision_text_dict[chapter_id]["contents"] = res[1]
            text = text[res.end():]

            if text:
                res = parse_subchapter_contents(parent_chapter_id, chapter_id, subchapter_id, text)
                while res:
                    revision_text_dict[chapter_id][str(subchapter_id)] = res[0]
                    text = text[res.end():]
                    subchapter_id += 1
                    res = parse_subchapter_contents(parent_chapter_id, chapter_id, subchapter_id, text)

            split_chapters_rec(revision_text_dict[chapter_id], parent_chapter_id + chapter_id + ".")
        elif text:
            split_paragraphs(revision_text_dict[chapter_id], text)


def save_revision_dict(revision_dict, revision_tag):
    with open("cache/revision_dict_%s.json" % revision_tag, "w") as rd:
        json.dump(revision_dict, rd, indent=4)


def parse_chapter(chapter_id, revision_text):
    r = r"^" + str(chapter_id) + r" (?:.*\n){0,2}?.*?\[([^\d\sN].*)\]$\n+([\s\S]*?)" \
                                 r"(?=^" + str(chapter_id + 1) + r" (?:.*\n){0,2}?.*?\[[^\d\sN].*\]$|\Z)"
    return re.search(r, revision_text, re.M)


def split_revisions_into_chapters(revision_text_dict):
    for revision_tag, revision_text in revision_text_dict.items():
        print("\tSplitting %s text into chapters" % revision_tag)
        revision_text_dict[revision_tag] = {}
        chapter_id = 1
        res = parse_chapter(chapter_id, revision_text)

        while res:
            revision_text_dict[revision_tag][str(chapter_id)] = res[0]
            revision_text = revision_text[res.end():]
            chapter_id += 1
            res = parse_chapter(chapter_id, revision_text)

        split_chapters_rec(revision_text_dict[revision_tag])
        save_revision_dict(revision_text_dict[revision_tag], revision_tag)

    return revision_text_dict


def map_referenced_paragraphs(references, revision_dict, target_revision_tag, ref_errors, section_mapping,
                              mapping_cache, coverage_dict):
    print("Mapping references to %s" % target_revision_tag)
    for reference in references:
        map_reference(reference, revision_dict, target_revision_tag, ref_errors, section_mapping, mapping_cache,
                      coverage_dict)


def load_revision_dict(revision_text_dict):
    revision_dict = {}

    for revision_tag in revision_text_dict:
        try:
            with open("cache/revision_dict_%s.json" % revision_tag, "r") as rev_dict:
                revision_dict[revision_tag] = json.loads(rev_dict.read())
            print("\tLoaded %s dictionary" % revision_tag)
        except FileNotFoundError:
            print("\t%s dictionary not found, attempting to create from text version" % revision_tag)
            rd = split_revisions_into_chapters({revision_tag: revision_text_dict[revision_tag]})
            revision_dict[revision_tag] = rd[revision_tag]

    return revision_dict


def write_errors(ref_errors):
    with open("referenceErrors.json", "w") as ref_error_json:
        if ref_errors:
            print("Some references could not be mapped, for details, check referenceErrors.json")
            json.dump(ref_errors, ref_error_json, indent=4)


def write_cache(mapping_cache, target_revision_tag):
    with open("cache/mapping_cache_%s.json" % target_revision_tag, "w") as cache:
        if mapping_cache:
            json.dump(mapping_cache, cache, indent=4)


def process_references(references, revision_dict, target_revision_tag, section_mapping, mapping_cache, coverage_dict):
    ref_errors = []
    map_referenced_paragraphs(references, revision_dict, target_revision_tag, ref_errors, section_mapping,
                              mapping_cache, coverage_dict)
    write_errors(ref_errors)
    write_cache(mapping_cache, target_revision_tag)


def save_mapped_references(target_revision_tag, references):
    with open("references_mapped_%s.json" % target_revision_tag, "w") as mapped_references:
        print("Saving mapped references")
        json.dump(references, mapped_references, indent=4)


def load_section_mapping(target_revision_tag, references, revision_tags):
    chapter_mapping.map_sections(target_revision_tag, references, revision_tags)
    try:
        with open("section_mapping_to_%s.json" % target_revision_tag, "r") as section_mapping_file:
            section_mapping = json.load(section_mapping_file)
    except FileNotFoundError:
        print("Failed to create section mapping to %s" % target_revision_tag)
        raise
    return section_mapping


def load_mapping_cache(target_revision_tag):
    cache_folder = "cache/"
    cache_name = "mapping_cache_%s.json" % target_revision_tag

    try:
        with open(cache_folder + cache_name, "r") as cache:
            return json.loads(cache.read())
    except FileNotFoundError:
        print("Cache not found, mapping might take slightly longer")
        return {}
    except json.decoder.JSONDecodeError:
        print("Wrong mapping cache format. Make sure all manual changes to the cache "
              "follow the format, check %sold_%s for details" % (cache_folder, cache_name))
        os.rename(cache_folder + cache_name, cache_folder + "old_" + cache_name)
        return {}


def initialize_coverage_dict(taget_revision_dict):
    coverage_dict = {}
    total = 0

    for section_id, contents in taget_revision_dict.items():
        if not (section_id == "contents" and isinstance(taget_revision_dict[section_id], str)):
            coverage_dict[section_id], total_rec = initialize_coverage_dict(taget_revision_dict[section_id])
            total += total_rec
        elif section_id in taget_revision_dict and \
                taget_revision_dict[section_id] and \
                isinstance(taget_revision_dict[section_id], str):
            coverage_dict[section_id] = False
            total += 1
    coverage_dict["total"] = total
    coverage_dict["covered"] = 0

    return coverage_dict, total


def map_paragraphs_to_target_revision(target_revision_tag, port_num):
    references = chapter_mapping.load_references()

    revision_set = set()
    revision_set.add(target_revision_tag)
    chapter_mapping.find_referenced_revision_tags(references, revision_set)

    section_mapping = load_section_mapping(target_revision_tag, references, revision_set)
    # chapter_mapping.map_sections(target_revision_tag, references, revision_set)
    revision_text_dict = load_txt_revisions(revision_set, port_num)
    if len(revision_text_dict) == len(revision_set):  # all revisions loaded correctly
        mapping_cache = load_mapping_cache(target_revision_tag)
        revision_dict = load_revision_dict(revision_text_dict)
        coverage_dict, total = initialize_coverage_dict(revision_dict[target_revision_tag])

        process_references(references, revision_dict, target_revision_tag, section_mapping, mapping_cache,
                           coverage_dict)
        save_mapped_references(target_revision_tag, references) # debug only, not necessary to save it otherwise

        return references, coverage_dict

    return None


def main(argv):
    try:
        if len(sys.argv) > 2:
            port_num = argv[2]
        else:
            port_num = None
        references, coverage_dict = map_paragraphs_to_target_revision(sys.argv[1], port_num)
    except (IndexError, FileNotFoundError, URLError):
        print("Usage: \"paragraphMapping.py <tag> <port number>\"\ne.g. \"paragraphMapping.py n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
