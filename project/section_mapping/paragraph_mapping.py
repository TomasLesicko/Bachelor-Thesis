#!/usr/bin/env python3

import sys
import re
import json
import difflib
from urllib.error import URLError
from requests.exceptions import ConnectionError
import chapter_mapping
import os
from tools.revision_PDF_to_txt import read_referenced_revision

# Any paragraph with less than the value is too different
# to be considered a match. 0.0 = 0%, 1.0 = 100%
DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.7

# Used to remove unwanted text from paragraphs when parsing them
# to revision_dict
PAGE_SPLIT_REGEX = r"(?:^(?:\d{1,3}\)[\s\S]+?)?" \
                   r"§ [\d\.]+ \d{1,4}\s+" \
                   r"[c©]{1,2}\s*ISO\/IEC N\d{1,4}\s+)?"


def load_txt_revisions(revision_set, port_num):
    """ Loads text versions of referenced revisions into memory.
    If the text versions are not present, attempts to create them
    via revision_PDF_to_txt.py, requires tika server and correct
    port number as an argument.
    """
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        try:
            txt_revision = open("tools/%s.txt" % revision_tag, "r")
            print("\tLoading %s.txt" % revision_tag)
            revisions_text_dict[revision_tag] = txt_revision.read()
        except FileNotFoundError:
            print("Couldn't find {0}.txt, attempting to create from "
                  "{0}.pdf".format(revision_tag))
            try:
                if port_num:
                    txt_revision = read_referenced_revision(revision_tag,
                                                            port_num,
                                                            "tools/")
                    if txt_revision:
                        revisions_text_dict[revision_tag] = txt_revision
                else:
                    print("Failed to load %s.txt, make sure tika server is "
                          "running and rerun the script with the correct port "
                          "number as second argument" % revision_tag)
            except ConnectionError:
                print(
                    "[Error] Missing %s.txt, make sure tika server is running "
                    "with correct port number" % revision_tag)

    return revisions_text_dict


def find_target_chapter(revision_dict, referenced):
    t = revision_dict
    for section_id in referenced:
        try:
            t = t[section_id]
        except KeyError:
            return None
    return t["contents"]


def extract_paragraph_from_referenced_revision(revision_dict,
                                               referenced_section):
    """ Searches for text of the referenced revision in
    revision_dict and returns it if found
    """
    referenced_chapter = referenced_section[0].split(".")
    referenced_paragraph = referenced_section[1].split(".")

    referenced_chapter_match = find_target_chapter(revision_dict,
                                                   referenced_chapter)
    if not referenced_chapter_match:
        return None

    referenced_paragraph_match = find_target_chapter(referenced_chapter_match,
                                                     referenced_paragraph)
    if not referenced_paragraph_match:
        return None

    return referenced_paragraph_match


def find_most_similar_paragraph(similar_paragraphs):
    """ Some paragraphs in the C++ started are worded very similarly.
    Sometimes, multiple paragraphs may be marked as similar. This function
    picks the paragraph with the highest similarity ratio.
    """
    max_i = 0
    max_ratio = 0
    for i in range(len(similar_paragraphs)):
        if similar_paragraphs[i][2] > max_ratio:
            max_i = i
            max_ratio = similar_paragraphs[i][2]

    return similar_paragraphs[max_i]


def get_paragraph_contents(target_chapter, paragraphs,
                           full_id=""):
    """ Flattens the structure within the target chapter since
    sometimes, paragraphs may contain subparagraphs of their own.
    """
    for paragraph_id, paragraph_contents \
            in target_chapter.items():
        if paragraph_id == "contents":
            paragraphs[full_id] = paragraph_contents
        else:
            if full_id and full_id[-1] != ".":
                full_id += "."
            get_paragraph_contents(paragraph_contents, paragraphs,
                                   full_id + paragraph_id)


def target_revision_find_paragraph_id(target_chapter,
                                      referenced_paragraph_text, threshold):
    """ Iterates through all paragraphs in the target chapter
    and computes similarity of those paragraphs to the referenced
    paragraph using an extended version of Ratcliff and Obershelp
     algorithm. Any paragraph passing a certain similarity threshold
    defined in a global constant is considered similar. After all
    paragraphs are compared, the most similar is chosen.
    """
    similar_paragraphs = []
    paragraphs = {}
    get_paragraph_contents(target_chapter, paragraphs)

    for paragraph_id, paragraph in paragraphs.items():

        matcher = difflib.SequenceMatcher(None, referenced_paragraph_text,
                                          paragraph, autojunk=False)
        ratio1 = matcher.ratio()
        # These allow for faster matching, but are less accurate
        # ratio2 = matcher.quick_ratio()
        # ratio3 = matcher.real_quick_ratio()

        if ratio1 > threshold:
            similar_paragraphs.append((paragraph_id, paragraph, ratio1))

    if similar_paragraphs:
        most_similar = find_most_similar_paragraph(similar_paragraphs)
        return most_similar

    return None


def is_in_mapping_cache(referenced_revision_tag, referenced_section,
                        mapping_cache):
    """ Checks if the referenced section is in the mapping cache
    Supports both entry formats (1.2:3.4 and 1.2/3.4)
    """

    s1 = ":".join(referenced_section)
    s2 = "/".join(referenced_section)
    if referenced_revision_tag in mapping_cache:
        cache_tag = mapping_cache[referenced_revision_tag]
        if s1 in cache_tag:
            return cache_tag[s1]
        if s2 in cache_tag:
            return cache_tag[s2]

    return None


def calculate_cached_text_similarity(cache, target_revision_chapters,
                                     referenced_paragraph_text):
    """ Calculates text similarity between the referenced paragraph
    and the target paragraph using an extended version of Ratcliff
    and Obershelp algorithm, for cached entries.
    """

    target_section = cache.split(":")
    chapters = find_target_chapter(target_revision_chapters,
                                   target_section[0].split("."))
    target_paragraph_text = find_target_chapter(chapters,
                                                target_section[1].split("."))
    matcher = difflib.SequenceMatcher(None, referenced_paragraph_text,
                                      target_paragraph_text, autojunk=False)
    ratio1 = matcher.ratio()
    return target_section[0], (target_section[1], target_paragraph_text,
                               ratio1)


def map_paragraph_to_target_revision(target_revision_chapters,
                                     referenced_paragraph_text,
                                     referenced_revision_tag,
                                     referenced_section, section_mapping,
                                     mapping_cache):
    """ Checks the cache for an entry, if the mapping is cached, only
    text similarity has to be computed (not stored in cache to keep it
    easy to understand and add entries manually if needed).

    Otherwise, section_mapping is checked to find the referenced chapter
    equivalent in the target revision. If found, the paragraphs in the
    chapter are searched and compared to the referenced text based on
    similarity. A match (or None) is returned.
    """
    cache = is_in_mapping_cache(referenced_revision_tag, referenced_section,
                                mapping_cache)
    if cache:
        return calculate_cached_text_similarity(cache,
                                                target_revision_chapters,
                                                referenced_paragraph_text)

    if referenced_revision_tag in section_mapping and referenced_section[0] \
            in section_mapping[referenced_revision_tag]:
        target_section = section_mapping[referenced_revision_tag][
            referenced_section[0]]
    else:
        print("Could not find %s %s in section mapping, make sure it's up to "
              "date" % (referenced_revision_tag, referenced_section[0]))
        target_section = None

    if target_section:
        target_chapter = find_target_chapter(target_revision_chapters,
                                             target_section.split("."))
        if target_chapter:
            return target_section, target_revision_find_paragraph_id(
                target_chapter, referenced_paragraph_text,
                DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD)

    return None, None


def is_valid_section_format(referenced_section):
    """ referenced_section - a list containing referenced chapter
    and paragraph.
    """
    return referenced_section is not None and len(referenced_section) == 2


def found_referenced_paragraph(referenced_paragraph_text):
    return referenced_paragraph_text is not None


def process_reference_error(reference, ref_errors, msg):
    """ Adds an error message to an erroneous reference
    and appends the reference to ref_errors
    """
    reference["error"] = msg
    ref_errors.append(reference)


def map_reference_same_revision(reference, coverage_dict, referenced_section):
    """ If the referenced revision is the same as the target revision,
    text comparison is skipped, as there is nothing to map.
    """
    reference["similarity"] = 1.0
    reference["error"] = ""
    update_coverage_dict(coverage_dict, referenced_section[0].split("."),
                         referenced_section[1].split("."))


def save_to_cache(reference_revision_tag, referenced_section, target_section,
                  mapping_cache):
    """ Saves the mapping in a cache so it doesn't have to be
    computed again in the future.
    """
    if reference_revision_tag in mapping_cache:
        mapping_cache[reference_revision_tag][
            referenced_section] = target_section
    else:
        mapping_cache[reference_revision_tag] = {}
        mapping_cache[reference_revision_tag][
            referenced_section] = target_section


def find_covered_section(coverage_dict, chapter_ids, paragraph_ids):
    referenced_section = coverage_dict

    # empty string is passed when annotating the document
    if chapter_ids[0]:
        for chapter_id in chapter_ids:
            referenced_section = referenced_section[str(chapter_id)]

        referenced_section = referenced_section["contents"]

    chapter_covered = referenced_section

    # empty string is passed when annotating the document
    if paragraph_ids[0]:
        for paragraph_id in paragraph_ids:
            referenced_section = referenced_section[str(paragraph_id)]

    return referenced_section, chapter_covered


def update_coverage_dict(coverage_dict, chapter_ids, paragraph_ids):
    referenced_section, chapter_covered = find_covered_section(coverage_dict,
                                                               chapter_ids,
                                                               paragraph_ids)
    """ Increases to total number of covered paragraphs, if the paragraph
    was not referenced in a previous reference.
    """

    if not referenced_section["contents"]:
        referenced_section["contents"] = True
        coverage_dict["covered"] += 1
        chapter_covered["covered"] += 1


def map_reference_different_revision(reference, target_revision_chapters,
                                     target_revision_tag,
                                     referenced_paragraph_text,
                                     referenced_revision_tag,
                                     referenced_section,
                                     ref_errors, section_mapping,
                                     mapping_cache, coverage_dict):
    """ Attempts to map the reference, if successful, updates,
    the reference by adding the similarity ratio of the text
    in the target revision compared to text in the referenced
    revision. Saves the mapping in the cache and updates coverage
    data. If mapping was not successful, the error is processed.
    """
    target_chapter_id, mapped_reference_results = \
        map_paragraph_to_target_revision(target_revision_chapters,
                                         referenced_paragraph_text,
                                         referenced_revision_tag,
                                         referenced_section,
                                         section_mapping, mapping_cache)

    if mapped_reference_results:
        section = target_chapter_id + ":" + mapped_reference_results[0]
        reference["document"]["section"] = section
        reference["similarity"] = mapped_reference_results[2]
        reference["error"] = ""
        save_to_cache(referenced_revision_tag, ":".join(referenced_section),
                      section, mapping_cache)
        update_coverage_dict(coverage_dict, target_chapter_id.split("."),
                             mapped_reference_results[0].split("."))

    else:
        if referenced_revision_tag \
                in section_mapping and referenced_section[0] \
                in section_mapping[referenced_revision_tag]:
            process_reference_error(reference, ref_errors,
                                    "Failed to locate referenced paragraph in"
                                    " target revision (%s) chapter %s" %
                                    (target_revision_tag,
                                     section_mapping[referenced_revision_tag][
                                         referenced_section[0]]))
        else:
            process_reference_error(reference, ref_errors,
                                    "Failed to locate referenced chapter in "
                                    "target revision (%s)"
                                    % target_revision_tag)


def map_reference(reference, revision_dict, target_revision_tag,
                  ref_errors, section_mapping, mapping_cache, coverage_dict):
    """ Checks if the reference has valid format, Finds reference text in the
    referenced revision, then maps it to the target revision.
    If reference format is wrong or referenced text couldn't be found in the
    referenced revision, the error is processed.
    """
    referenced_revision_tag = reference["document"]["document"].lower()
    referenced_section = re.split("[:/]", reference["document"]["section"])

    if not is_valid_section_format(referenced_section):
        process_reference_error(reference, ref_errors,
                                "Unsupported section format")
        return

    referenced_paragraph_text = extract_paragraph_from_referenced_revision(
        revision_dict[referenced_revision_tag], referenced_section)
    if not found_referenced_paragraph(referenced_paragraph_text):
        process_reference_error(reference,
                                ref_errors,
                                "Failed to locate referenced section in"
                                " referenced revision (%s)"
                                % referenced_revision_tag)
        return

    if referenced_revision_tag == target_revision_tag:
        map_reference_same_revision(reference, coverage_dict,
                                    referenced_section)
    else:
        map_reference_different_revision(reference,
                                         revision_dict[target_revision_tag],
                                         target_revision_tag,
                                         referenced_paragraph_text,
                                         referenced_revision_tag,
                                         referenced_section,
                                         ref_errors, section_mapping,
                                         mapping_cache, coverage_dict)


def set_regex_parentheses(parent_paragraph_id):
    """ Adds parentheses if the paragraph has a parent.
    Paragraphs with a parent ( = subparagraphs ) have
    their identifiers wrapped in parentheses and an em dash.
    """
    par_open = r""
    par_close = r""
    if parent_paragraph_id:
        par_open += r"—\("
        par_close += r"\)"

    return par_open, par_close


def parse_subparagraph_contents(parent_paragraph_id, paragraph_id,
                                subparagraph_id, text):
    """ Parses text similarly to parse_this_paragraph_contents, but
    is tailored for subparagraphs, which have a slightly different
    format.
    """
    subparagraph = parent_paragraph_id + paragraph_id + r"\." \
                   + str(subparagraph_id)
    next_subparagraph = parent_paragraph_id + paragraph_id + r"\." + str(
        subparagraph_id + 1)
    r = r"(^—\(" + subparagraph + r"\) [\s\S]+?)" + PAGE_SPLIT_REGEX \
        + r"(?=^—\(" + next_subparagraph + r"\) |\Z)"

    return re.match(r, text, re.M)


def parse_this_paragraph_contents(parent_paragraph_id, paragraph_id, text):
    """ Parses text belonging directly to the paragraph. If the text is
    split between two pages, it will contain unwanted characters which
    may mess the text comparison, such as page number, extra
    whitespace etc. This functions removes it.
    """
    par_open, par_close = set_regex_parentheses(parent_paragraph_id)
    r = r"(^" + par_open + parent_paragraph_id + str(paragraph_id) \
        + par_close + r" [\s\S]+?)" + PAGE_SPLIT_REGEX + r"(?=^—\(" \
        + parent_paragraph_id + str(paragraph_id) + r"\.1\) |\Z)"

    return re.match(r, text, re.M)


def split_paragraphs_rec(revision_text_dict, parent_paragraph_id=""):
    """ Further splits subparagraphs into smaller subparagraphs, if
    possible and parses the paragraph and subparagraph contents.
    Stopping condition - a paragraph contains "contents" key. Paragraphs
    which do not contain any subparagraphs will only have this key
    """
    for paragraph_id, text in revision_text_dict.items():
        if not paragraph_id == "contents":
            revision_text_dict[paragraph_id] = {}
            subparagraph_id = 1

            res = parse_this_paragraph_contents(parent_paragraph_id,
                                                paragraph_id, text)
            revision_text_dict[paragraph_id]["contents"] = res[1]
            text = text[res.end():]

            if text:
                res = parse_subparagraph_contents(parent_paragraph_id,
                                                  paragraph_id,
                                                  subparagraph_id, text)
                while res:
                    revision_text_dict[paragraph_id][
                        str(subparagraph_id)] = res[1]
                    text = text[res.end():]
                    subparagraph_id += 1
                    res = parse_subparagraph_contents(parent_paragraph_id,
                                                      paragraph_id,
                                                      subparagraph_id, text)

            split_paragraphs_rec(revision_text_dict[paragraph_id],
                                 parent_paragraph_id + paragraph_id + ".")


def parse_paragraph(paragraph_id, text):
    r = r"^" + str(paragraph_id) + r" [\s\S]+?(?=^" \
        + str(paragraph_id + 1) + r" |\Z)"
    return re.match(r, text, re.M)


def split_paragraphs(revision_text_dict, text):
    """ Splits paragraphs into subparagraphs, if possible.
    Any text belonging directly to the paragraph doesn't have
    to be split any further.
    """
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
    r = r"^" + parent_chapter_id + str(chapter_id) \
        + r" (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$\n+([\s\S]*?)(?=^" \
        + parent_chapter_id + str(chapter_id) \
        + r"\.1 (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$|\Z)"

    return re.match(r, text, re.M)


def parse_subchapter_contents(parent_chapter_id, chapter_id,
                              subchapter_id, text):
    subchapter = parent_chapter_id + chapter_id + r"\." + str(subchapter_id)
    next_subchapter = parent_chapter_id + chapter_id + r"\." + str(
        subchapter_id + 1)
    r = r"^" + subchapter + r" (?:.*\n){0,2}?.*?\[([^\d\sN].*?)\]$" \
                            r"\n+([\s\S]*?)(?=^" + next_subchapter \
        + r" (?:.*\n){0,2}?.*?\[[^\d\sN].*?\]$|\Z)"

    return re.match(r, text, re.M)


def split_chapters_rec(revision_text_dict, parent_chapter_id=""):
    """ Further splits a chapter into subchapters, if the chapter contains
    any subchapters. Any contents ( = paragraphs ) belonging directly to the
    chapter are located at the start of the chapter, these are further processed
    by split_paragraphs.
    """
    for chapter_id, text in revision_text_dict.items():
        revision_text_dict[chapter_id] = {}
        subchapter_id = 1

        if not chapter_id == "contents":
            res = parse_chapter_contents(parent_chapter_id, chapter_id, text)
            revision_text_dict[chapter_id]["contents"] = res[1]
            text = text[res.end():]

            if text:
                res = parse_subchapter_contents(parent_chapter_id, chapter_id,
                                                subchapter_id, text)
                while res:
                    revision_text_dict[chapter_id][
                        str(subchapter_id)] = res[0]
                    text = text[res.end():]
                    subchapter_id += 1
                    res = parse_subchapter_contents(parent_chapter_id,
                                                    chapter_id, subchapter_id,
                                                    text)

            split_chapters_rec(revision_text_dict[chapter_id],
                               parent_chapter_id + chapter_id + ".")
        elif text:
            split_paragraphs(revision_text_dict[chapter_id], text)


def save_revision_dict(revision_dict, revision_tag):
    with open("cache/revision_dict_%s.json" % revision_tag, "w") as rd:
        json.dump(revision_dict, rd, indent=4)


def parse_chapter(chapter_id, revision_text):
    r = r"^" + str(chapter_id) + r" (?:.*\n){0,2}?.*?\[([^\d\sN].*)\]$" \
                                 r"\n+([\s\S]*?)(?=^" + str(chapter_id + 1) \
        + r" (?:.*\n){0,2}?.*?\[[^\d\sN].*\]$|\Z)"
    return re.search(r, revision_text, re.M)


def split_revisions_into_chapters(revision_text_dict):
    """ Splits each referenced revision into chapters.
    TOC and Annexes are currently ommited.
    """
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


def map_referenced_paragraphs(references, revision_dict, target_revision_tag,
                              ref_errors, section_mapping, mapping_cache,
                              coverage_dict):
    print("Mapping references to %s" % target_revision_tag)
    for reference in references:
        map_reference(reference, revision_dict, target_revision_tag,
                      ref_errors, section_mapping, mapping_cache,
                      coverage_dict)


def load_revision_dict(revision_text_dict):
    """ loads parsed contents of each referenced revision into a dictionary
    if it exists, otherwise it parses the text.
    """
    revision_dict = {}

    for revision_tag in revision_text_dict:
        try:
            with open("cache/revision_dict_%s.json" % revision_tag, "r") \
                    as rev_dict:
                revision_dict[revision_tag] = json.loads(rev_dict.read())
            print("\tLoaded %s dictionary" % revision_tag)
        except FileNotFoundError:
            print("\t%s dictionary not found, attempting to create from text"
                  " version" % revision_tag)
            rd = split_revisions_into_chapters(
                {revision_tag: revision_text_dict[revision_tag]})
            revision_dict[revision_tag] = rd[revision_tag]

    return revision_dict


def write_errors(ref_errors):
    with open("referenceErrors.json", "w") as ref_error_json:
        if ref_errors:
            print("Some references could not be mapped, for details, "
                  "check referenceErrors.json")
            json.dump(ref_errors, ref_error_json, indent=4)


def write_cache(mapping_cache, target_revision_tag):
    with open("cache/mapping_cache_%s.json" % target_revision_tag, "w") \
            as cache:
        if mapping_cache:
            json.dump(mapping_cache, cache, indent=4)


def process_references(references, revision_dict, target_revision_tag,
                       section_mapping, mapping_cache, coverage_dict):
    ref_errors = []
    map_referenced_paragraphs(references, revision_dict, target_revision_tag,
                              ref_errors, section_mapping, mapping_cache,
                              coverage_dict)
    write_errors(ref_errors)
    write_cache(mapping_cache, target_revision_tag)


def save_mapped_references(target_revision_tag, references):
    with open("references_mapped_%s.json" % target_revision_tag, "w") \
            as mapped_references:
        print("Saving mapped references")
        json.dump(references, mapped_references, indent=4)


def load_section_mapping(target_revision_tag, references, revision_tags):
    """ Calls map_sections from chapter mapping to recreate chapter_mapping
    and loads the resulting JSON
    """
    chapter_mapping.map_sections(target_revision_tag, references,
                                 revision_tags)
    try:
        with open("section_mapping_to_%s.json" % target_revision_tag, "r") \
                as section_mapping_file:
            section_mapping = json.load(section_mapping_file)
    except FileNotFoundError:
        print("Failed to create section mapping to %s" % target_revision_tag)
        raise
    return section_mapping


def load_mapping_cache(target_revision_tag):
    """ Loads mapping cache for the target revision
    Mapping cache serves to make mapping more efficient,
    paragraphs that were successfully mapped previously are
    stored in the cache, so they don't need to be mapped
    again. Instead, mapping cache is checked for each reference,
    element access O(1) on average. Cache can be edited to manually
    map references that cannot be mapped automatically. In case the
    JSON format is broken when manually editing the cache, it is saved
    as old_cache to prevent overwriting it when creating a new cache
    from scratch.
    """
    cache_folder = "cache/"
    cache_name = "mapping_cache_%s.json" % target_revision_tag

    try:
        with open(cache_folder + cache_name, "r") as cache:
            return json.loads(cache.read())
    except FileNotFoundError:
        print("Cache not found, mapping might take slightly longer")
        return {}
    except json.decoder.JSONDecodeError:
        print("Wrong mapping cache format. Make sure all manual changes to "
              "the cache follow the format, check %sold_%s for details"
              % (cache_folder, cache_name))
        os.rename(cache_folder + cache_name, cache_folder + "old_"
                  + cache_name)
        return {}


def initialize_coverage_dict(taget_revision_dict):
    """ Initializes coverage dictionary, containing coverage data
    Currently supported coverage is total document coverage and chapter
    coverage.
    total - computes the total amount of paragraphs in a given section
    ( = chapter, subchapter, document...) and stores it so coverage percentage
    can be computed later.
    """
    coverage_dict = {}
    total = 0

    for section_id, contents in taget_revision_dict.items():
        if not (section_id == "contents" and isinstance(
                taget_revision_dict[section_id], str)):
            coverage_dict[section_id], total_rec = initialize_coverage_dict(
                taget_revision_dict[section_id])
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
    """ Loads necessary data and uses them to map paragraphs
    references - the output from referenceExtractor.cpp
    revision_set - contains all revision tags mentioned in the references
                   as well as the target revision tag
    section_mapping - mapped chapters, output from chapter_mapping.py
    revision_text_dict - all referenced revisions in text form
    mapping_cache - cache for the target revision for faster mapping
    revision_dict - revisions parsed in JSON / dictionary form
    for efficient access (O(1) average)
    coverage_dict - will contain coverage data to be displayed
    """
    references = chapter_mapping.load_references()

    revision_set = set()
    revision_set.add(target_revision_tag)
    chapter_mapping.find_referenced_revision_tags(references, revision_set)

    section_mapping = load_section_mapping(target_revision_tag, references,
                                           revision_set)

    revision_text_dict = load_txt_revisions(revision_set, port_num)
    # references and all revisions loaded correctly
    if references and len(revision_text_dict) == len(revision_set):
        mapping_cache = load_mapping_cache(target_revision_tag)
        revision_dict = load_revision_dict(revision_text_dict)
        coverage_dict, total = initialize_coverage_dict(
            revision_dict[target_revision_tag])

        process_references(references, revision_dict, target_revision_tag,
                           section_mapping, mapping_cache, coverage_dict)
        # necessary for HTML annotator
        save_mapped_references(target_revision_tag, references)

        return references, coverage_dict

    return None, None


def main(argv):
    try:
        if len(sys.argv) > 2:
            port_num = argv[2]
        else:
            port_num = None
        references, coverage_dict = map_paragraphs_to_target_revision(
            sys.argv[1], port_num)
    except (IndexError, FileNotFoundError, URLError):
        print("Usage: \"paragraphMapping.py <tag> <port number>"
              "\"\ne.g. \"paragraphMapping.py n4296 9997\"")


if __name__ == "__main__":
    main(sys.argv)
