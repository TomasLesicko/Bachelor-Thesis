import os.path
import sys
import re
from tika import parser, tika
import json
import difflib

import chapter_mapping

DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.4
DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD = 0.3
DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE = 0.05

SECTIONS_LINE_REGEX = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'

PARAGRAPH_PARSING_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"
PARAGRAPH_PARSING_REGEX_NUM_ID = r"(\d+(?:\.\d+)*)"

CHAPTER_PARSING_REGEX = r"(^[A-Z0-9](?:\d)*(?:\.\d+)*) .+ \[(.+)\]$([\s\S]+?)(?=(?:^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"
CHAPTER_PARSING_REGEX_NUM_ID = r"[A-Z0-9](?:\d)*(?:\.\d+)*"
CHAPTER_PARSING_REGEX_BRACKET_ID = r"(.+)"


def read_referenced_revisions(revision_set):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            revision_tag.lower() + ".pdf")
        print("\tLoading %s" % revision_tag)
        try:
            tika.TikaClientOnly = True
            contents = parser.from_file(path, "http://localhost:9997/")["content"]  # TODO retrieval bugfix on fresh start
            revisions_text_dict[revision_tag] = contents
        except FileNotFoundError as fnfe:
            print(fnfe)
            print("Could not find revision %s in draft/papers" % revision_tag)
            raise fnfe

    return revisions_text_dict


def find_referenced_chapter_text(revision_text, referenced_chapter):
    referenced_chapter_regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_NUM_ID,
                                                             re.escape(referenced_chapter), 1)
    referenced_chapter_text = re.findall(referenced_chapter_regex, revision_text,
                                         re.M)  # TODO exclude chapter title from the match, reason: chapter id can be same as paragraph id especally in the first few chapters, could cause problems when matching paragraph
    return referenced_chapter_text


def find_referenced_paragraph_text(referenced_chapter_text, referenced_paragraph):
    referenced_paragraph_regex = PARAGRAPH_PARSING_REGEX.replace(PARAGRAPH_PARSING_REGEX_NUM_ID,
                                                                 re.escape(referenced_paragraph), 1)
    referenced_paragraph_text = re.findall(referenced_paragraph_regex, referenced_chapter_text, re.M)
    # TODO paragraph regex matches everything until next identifier, may cause issues
    return referenced_paragraph_text


def extract_paragraph_text(revision_text, referenced_section):
    referenced_chapter = referenced_section[0]
    referenced_paragraph = referenced_section[1]

    referenced_chapter_match = find_referenced_chapter_text(revision_text, referenced_chapter)

    if not referenced_chapter_match:
        return None, None

    referenced_chapter_bracket_id = referenced_chapter_match[0][1]
    referenced_chapter_text = referenced_chapter_match[0][2]

    referenced_paragraph_match = find_referenced_paragraph_text(referenced_chapter_text, referenced_paragraph)
    if not referenced_paragraph_match:
        return None, None

    return referenced_paragraph_match[0][1], referenced_chapter_bracket_id


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
    similar_paragraphs = []
    for chapter in target_revision_chapters:
        target_chapter_paragraphs = re.findall(PARAGRAPH_PARSING_REGEX, chapter[2], re.M)
        # TODO match paragraphs correctly if they're split by new page

        for paragraph in target_chapter_paragraphs:

            matcher = difflib.SequenceMatcher(None, paragraph_text, paragraph[2])
            ratio1 = matcher.ratio()
            # ratio2 = matcher.quick_ratio()
            # ratio3 = matcher.real_quick_ratio()

            if ratio1 > threshold: similar_paragraphs.append((chapter[0], paragraph, ratio1))
            # if ratio2 > 0.9: similar_paragraphs.append((c[0], paragraph, ratio2))
        # TODO try to obtain the diff text in readable format and display the diff in annotation

    if similar_paragraphs:
        most_similar = find_most_similar_paragraph(similar_paragraphs)
        return most_similar[0] + ":" + most_similar[1][1]

    # if no similar paragraph was found, retry with lower ratio threshold
    if threshold > DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD:
        print("\tCouldn't match referenced paragraph, retrying with lower match ratio (%s)\n\tReference:\n\t%s %s:%s"
              % (round(threshold - DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, 2), referenced_revision_tag, referenced_section[0],
                 referenced_section[1]))
        return target_revision_find_paragraph_id(target_revision_chapters, paragraph_text,
                                                 round(threshold - DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, 2),
                                                 referenced_revision_tag, referenced_section)

    print("\tFailed to match referenced paragraph with minimum allowed match ratio (%s)\n\tReference:\n\t%s %s:%s" %
          (DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD, referenced_revision_tag, referenced_section[0],
           referenced_section[1]))
    return ""


def target_revision_find_section_id(target_revision_text, referenced_paragraph_text, referenced_chapter_id,
                                    referenced_revision_tag, referenced_section):
    regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_BRACKET_ID,
                                          r"(" + re.escape(referenced_chapter_id) + r")", 1)

    presumed_target_text_chapter = re.findall(regex, target_revision_text, re.M)
    if presumed_target_text_chapter:
        chapters = presumed_target_text_chapter
    else:
        chapters = re.findall(CHAPTER_PARSING_REGEX, target_revision_text, re.M)

    return target_revision_find_paragraph_id(chapters, referenced_paragraph_text,
                                             DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD, referenced_revision_tag,
                                             referenced_section)


def process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag, ref_errors):
    print("Mapping references to %s" % target_revision_tag)
    target_text = revisions_text_dict[target_revision_tag]

    for reference in references:
        referenced_revision_tag = reference["document"]["document"].lower()

        if referenced_revision_tag != target_revision_tag:

            referenced_section = re.split("[:/]", reference["document"]["section"])  # TODO other variations
            if referenced_section is None or len(referenced_section) != 2:
                reference["error"] = "Unsupported section format"
                ref_errors.append(reference)
                continue

            referenced_paragraph_text, referenced_chapter_bracket_id = extract_paragraph_text(
                revisions_text_dict[referenced_revision_tag], referenced_section)
            if referenced_paragraph_text is None:
                reference["error"] = "Failed to locate referenced section in referenced revision (%s)" \
                                     % referenced_revision_tag
                ref_errors.append(reference)
                continue

            target_revision_section_id = target_revision_find_section_id(target_text,
                                                                         referenced_paragraph_text,
                                                                         referenced_chapter_bracket_id,
                                                                         referenced_revision_tag, referenced_section)
            if target_revision_section_id:
                reference["document"]["section"] = target_revision_section_id
            else:
                reference["error"] = "Failed to locate referenced section in target revision (%s)" \
                                     % target_revision_tag
                ref_errors.append(reference)


def map_paragraphs_to_target_revision(target_revision_tag):
    # TODO add option to use local references by providing path
    revision_set = set()
    revision_set.add(target_revision_tag)

    references = chapter_mapping.load_references()
    #with open("../references/references.json", 'r') as referencesf:
        #references = json.load(referencesf)
    chapter_mapping.extract_revision_tag_list_from_references(references, revision_set)

    revisions_text_dict = read_referenced_revisions(revision_set)
    with open("referenceErrors.json", 'w') as ref_error_json:
        ref_errors = []
        process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag, ref_errors)
        if ref_errors:
            json.dump(ref_errors, ref_error_json, indent=4)
    return references


def main(argv):
    try:
        references = map_paragraphs_to_target_revision(sys.argv[1])  # TODO argparse lib, progressbar?
        x = 0
    except (IndexError, FileNotFoundError) as e:
        print("Usage: \"paragraphMapping.py <tag>\"\ne.g. \"paragraphMapping.py n4296\"")

    # try:

    # except (RuntimeError, IndexError, FileNotFoundError) as e:
    #     print(e)
    #     print("Usage: \"paragraphMapping.py <tag>\"\ne.g. \"paragraphMapping.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
