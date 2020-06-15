import os.path
import sys
import re
from tika import parser
import json
import difflib

import chapter_extractor
import chapter_mapping

SECTIONS_LINE_REGEX = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'
# REVISION_PARAGRAPH_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"


# REVISION_PARAGRAPH_REGEX = [r"(^—?\(?", r"\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"]
PARAGRAPH_PARSING_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"
PARAGRAPH_PARSING_REGEX_NUM_ID = r"(\d+(?:\.\d+)*)"

# REVISION_PARAGRAPH_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=\1)"

# CHAPTER_PARSING_REGEX = r"(^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)[\s\S]+?(?=(^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"


# CHAPTER_PARSING_REGEX = r" .+ \[(.+)\]$([\s\S]+?)(?=(?:^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"
CHAPTER_PARSING_REGEX = r"(^[A-Z0-9](?:\d)*(?:\.\d+)*) .+ \[(.+)\]$([\s\S]+?)(?=(?:^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"
CHAPTER_PARSING_REGEX_NUM_ID = r"[A-Z0-9](?:\d)*(?:\.\d+)*"
CHAPTER_PARSING_REGEX_BRACKET_ID = r"(.+)"

"""
- find all tags in refs + target ref tag, then open the contents in tika and save it in a dictionary
- go through ref sections, find chapter.name.id via section id, if chapter names file doesn't
    exist, create it via chapter extractor
- edit the entry a bit so it fits regex
- use regex to find the chapter and extract it with regex like
    "13.3 Handling an exception \[except.handle\][\s\S]*\d+\.\d+ (\w+ )+\[\w+\.\w+\]" .* re.DOTALL should work nstead [\s\S]
    the second part could just be the chapter that follows, should be easy to find from chapter
    names file
- now another regex that finds the referenced paragraph from section id, extracts it
- now use the extracted text as a regex to search target standard
- if there's a match, simple to map from here
- no match - wording has changed
    slight change - could somehow "soften" the regex so it matches
    large change - just show error, possibly not desirable to highlight a severely changed paragraph
- use difflib library to compare the strings? SequenceMatcher.ratio() should compute similarity
    index between two strings, pretty much what i need, just worrying about scalability
"""


def read_referenced_revisions(revision_set):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            revision_tag.lower() + ".pdf")
        print("\tLoading %s" % revision_tag)
        try:
            contents = parser.from_file(path)["content"]  # TODO retrieval bugfix on fresh start
            revisions_text_dict[revision_tag] = contents
        except FileNotFoundError as fnfe:
            print(fnfe)
            print("[WARNING] Could not find revision %s in draft/papers" % revision_tag)

    return revisions_text_dict


def extract_paragraph_text(revision_text, referenced_section):
    referenced_chapter = referenced_section[0]
    referenced_paragraph = referenced_section[1]

    referenced_chapter_regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_NUM_ID,
                                                             re.escape(referenced_chapter), 1)
    referenced_chapter_text = re.findall(referenced_chapter_regex, revision_text,
                                         re.M)  # TODO exclude chapter title from the match, reason: chapter id can be same as paragraph id especally in the first few chapters, could cause problems when matching paragraph
    referenced_chapter_bracket_id = referenced_chapter_text[0][1]

    referenced_paragraph_regex = PARAGRAPH_PARSING_REGEX.replace(PARAGRAPH_PARSING_REGEX_NUM_ID,
                                                                 re.escape(referenced_paragraph), 1)
    referenced_paragraph_text = re.findall(referenced_paragraph_regex, referenced_chapter_text[0][2], re.M)
    # TODO paragraph regex matches everything until next identifier, may cause issues

    return referenced_paragraph_text, referenced_chapter_bracket_id


def process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag):
    print("Mapping references to %s" % target_revision_tag)
    target_text = revisions_text_dict[target_revision_tag]

    for reference in references:
        referenced_revision_tag = reference["document"]["document"].lower()
        if referenced_revision_tag != target_revision_tag:
            referenced_section = re.split("[:/]", reference["document"]["section"])  # TODO other variations
            if referenced_section is None or len(referenced_section) != 2:
                print("Faulty reference: %s" % referenced_revision_tag)  # TODO error

            referenced_paragraph_text, referenced_chapter_bracket_id = extract_paragraph_text(
                revisions_text_dict[referenced_revision_tag],
                referenced_section)
            reference["document"]["section"] = target_revision_find_paragraph_id(target_text,
                                                                                 referenced_paragraph_text,
                                                                                 referenced_section,
                                                                                 referenced_chapter_bracket_id)


# def find_referenced_text(revision_text, revision_tag, references, target_text):
#     for reference in references:
#         if reference["document"]["document"] == revision_tag:
#             referenced_section = re.split("[:/]", reference["document"]["section"])  # TODO other variations
#             if referenced_section is None or len(referenced_section) != 2:
#                 print("Faulty reference: %s" % reference["document"]["document"])  # TODO error
#
#             referenced_paragraph_text, referenced_chapter_bracket_id = extract_paragraph_text(revision_text,
#                                                                                               referenced_section)
#             reference["document"]["section"] = target_revision_find_paragraph_id(target_text,
#                                                                                  referenced_paragraph_text,
#                                                                                  referenced_section,
#                                                                                  referenced_chapter_bracket_id)


def func(r1a):
    max_i = 0
    max_r = 0
    for i in range(len(r1a)):
        if r1a[i][1] > max_r:
            max_i = i

    return r1a[max_i]


def target_revision_find_paragraph_id(target_revision_text, referenced_paragraph_text, referenced_section,
                                      referenced_chapter_id):
    regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_BRACKET_ID,
                                          re.escape(referenced_chapter_id), 1)
    id = ""

    presumed_target_text_chapter = re.findall(regex, target_revision_text, re.M)
    if presumed_target_text_chapter:
        id += presumed_target_text_chapter[0][0]
    else:
        t = 0
        # TODO traverse whole document

    target_chapter_paragraphs = re.findall(PARAGRAPH_PARSING_REGEX, presumed_target_text_chapter[0][1], re.M)
    # TODO match paragraphs correctly if they're split by new page

    r1a = []
    r2a = []
    i = 0
    for paragraph in target_chapter_paragraphs:

        matcher = difflib.SequenceMatcher(None, referenced_paragraph_text[0][1], paragraph[2])
        ratio1 = matcher.ratio()
        ratio2 = matcher.quick_ratio()
        # ratio3 = matcher.real_quick_ratio()

        if ratio1 > 0.3: r1a.append((paragraph, ratio1))
        if ratio2 > 0.9: r2a.append((paragraph, ratio2))
        # opcodes = matcher.get_opcodes()
        # matcher = difflib.get_close_matches(referenced_paragraph_text[0][1], paragraph, 1, 0.9)
        # TODO try to obtain the diff text in readable format and display the diff in annotation

    if not r1a:
        x = 4 #ref may not exist in target_revision
    m = func(r1a)
    id += ":"
    id += m[0][0]
    return id


def map_paragraphs_to_target_revision(target_revision_tag):
    # TODO add option to use local references by providing path
    revision_set = set()
    revision_set.add(target_revision_tag)

    references = chapter_mapping.load_references()
    chapter_mapping.extract_revision_tag_list_from_references(references, revision_set)

    revisions_text_dict = read_referenced_revisions(revision_set)
    process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag)

    return references


def main(argv):
    references = map_paragraphs_to_target_revision(sys.argv[1])  # TODO argparse lib
    x = 0

    # try:

    # except (RuntimeError, IndexError, FileNotFoundError) as e:
    #     print(e)
    #     print("Usage: \"paragraphMapping.py <tag>\"\ne.g. \"paragraphMapping.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
