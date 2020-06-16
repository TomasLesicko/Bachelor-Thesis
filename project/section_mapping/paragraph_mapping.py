import os.path
import sys
import re
from tika import parser
import json
import difflib

import chapter_extractor
import chapter_mapping

DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD = 0.4
DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD = 0.3
DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE = 0.05

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
    # TODO if no match, referenced chapter or paragraph must be wrong for the given revision
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
            target_revision_section_id = target_revision_find_section_id(target_text,
                                                                         referenced_paragraph_text,
                                                                         referenced_chapter_bracket_id, referenced_revision_tag, referenced_section)
            if target_revision_section_id:
                reference["document"]["section"] = target_revision_section_id
            else:
                # TODO mark reference as faulty
                x = 0


def func(r1a):
    max_i = 0
    max_r = 0
    for i in range(len(r1a)):
        if r1a[i][2] > max_r:
            max_i = i
            max_r = r1a[i][2]

    return r1a[max_i]


def target_revision_find_paragraph_id(chapter_text, paragraph_text, threshold, referenced_revision_tag, referenced_section):
    r1a = []
    for c in chapter_text:
        target_chapter_paragraphs = re.findall(PARAGRAPH_PARSING_REGEX, c[2], re.M)
        # TODO match paragraphs correctly if they're split by new page

        for paragraph in target_chapter_paragraphs:

            matcher = difflib.SequenceMatcher(None, paragraph_text, paragraph[2])
            ratio1 = matcher.ratio()
            # ratio2 = matcher.quick_ratio()
            # ratio3 = matcher.real_quick_ratio()

            if ratio1 > threshold: r1a.append((c[0], paragraph, ratio1))
            # if ratio2 > 0.9: r1a.append((c[0], paragraph, ratio2))
        # TODO try to obtain the diff text in readable format and display the diff in annotation

    if r1a:
        m = func(r1a)
        return m[0] + ":" + m[1][1]

    if threshold > DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD:
        print("Couldn't match referenced paragraph, retrying with lower match ratio (%s - %s)\nReference:\n%s %s:%s"
              % (threshold, DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, referenced_revision_tag, referenced_section[0],
                 referenced_section[1]))
        return target_revision_find_paragraph_id(chapter_text, paragraph_text,
                                                 round(threshold - DIFFLIB_MATCHER_RATIO_DECREMENT_VALUE, 2),
                                                 referenced_revision_tag, referenced_section)
    print("Failed to match referenced paragraph with minimum allowed match ratio (%s)\nReference:\n%s %s:%s" %
          (DIFFLIB_MATCHER_RATIO_MINIMUM_THRESHOLD, referenced_revision_tag, referenced_section[0],
           referenced_section[1])) # TODO write failed references to file
    return ""


def target_revision_find_section_id(target_revision_text, referenced_paragraph_text, referenced_chapter_id, referenced_revision_tag, referenced_section):
    regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_BRACKET_ID,
                                          r"(" + re.escape(referenced_chapter_id) + r")", 1)

    presumed_target_text_chapter = re.findall(regex, target_revision_text, re.M)
    if presumed_target_text_chapter:
        section_id = target_revision_find_paragraph_id(presumed_target_text_chapter, referenced_paragraph_text[0][1],
                                                       DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD, referenced_revision_tag, referenced_section)
        if section_id:
            return section_id
    else:
        target_revision_chapters = re.findall(CHAPTER_PARSING_REGEX, target_revision_text, re.M)
        section_id = target_revision_find_paragraph_id(target_revision_chapters,
                                                       referenced_paragraph_text,
                                                       DIFFLIB_MATCHER_RATIO_DEFAULT_THRESHOLD, referenced_revision_tag[0][1], referenced_section)
        if section_id:
            return section_id

    return ""


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
    references = map_paragraphs_to_target_revision(sys.argv[1])  # TODO argparse lib, progressbar?
    x = 0

    # try:

    # except (RuntimeError, IndexError, FileNotFoundError) as e:
    #     print(e)
    #     print("Usage: \"paragraphMapping.py <tag>\"\ne.g. \"paragraphMapping.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
