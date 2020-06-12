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


#REVISION_PARAGRAPH_REGEX = [r"(^—?\(?", r"\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"]
PARAGRAPH_PARSING_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?|\Z))"
PARAGRAPH_PARSING_REGEX_NUM_ID = r"(\d+(?:\.\d+)*)"


# REVISION_PARAGRAPH_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=\1)"

# CHAPTER_PARSING_REGEX = r"(^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)[\s\S]+?(?=(^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"


#CHAPTER_PARSING_REGEX = r" .+ \[(.+)\]$([\s\S]+?)(?=(?:^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"
CHAPTER_PARSING_REGEX = r"(^[A-Z0-9](?:\d)*(?:\.\d+)*) .+ \[(.+)\]$([\s\S]+?)(?=(?:^[A-Z0-9](?:\d)*(?:\.\d+)* .+ \[.+\]$)|\Z)"
CHAPTER_PARSING_REGEX_NUM_ID = r"^[A-Z0-9](?:\d)*(?:\.\d+)*"
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


def read_target_revision_sections(regex_expr, current):
    with open("section_names_" + CURRENT_REVISION_TAG + ".txt", 'r') as sections_text:
        matches = re.findall(regex_expr, sections_text.read())
        for tuple in matches:
            current[tuple[1]] = tuple[0]


def map_revision_sections(regex_expr, revision_set, current, older_revision_sections):
    for revision_tag in revision_set:
        with open("section_names_" + revision_tag + ".txt", 'r') as sections_text:
            r = re.findall(regex_expr, sections_text.read())
            this_revision_sections = {}
            for tuple in r:
                maps_to = current.get(tuple[1])
                this_revision_sections[tuple[0]] = maps_to
            older_revision_sections[revision_tag] = this_revision_sections


def search_paragraph_by_section_id(section_id, contents):
    regex = re.escape(section_id.split(":")[0])
    # result = re.findall(regex, contents) # need to search by except.handle etc, connect with
    # chapter_mapping
    result = re.findall("except\.handle", contents)
    result = re.findall(re.escape("13.3 Handling an exception [except.handle]"))
    x = 4


def map_paragraphs_to_target_revision(references, target_tag):
    for reference in references:
        referenced_tag = reference["document"]["document"]
        if referenced_tag.lower() != target_tag.lower():
            path = os.path.join(os.path.dirname(__file__), referenced_tag.lower() + ".pdf")
            contents = parser.from_file(path)["content"]  # can't do this too inefficient
            # perhaps find tags, then create a dictionary containing loaded contents of all revisions
            search_paragraph_by_section_id(reference["document"]["section"], contents)


def read_referenced_revisions(revision_set):
    revisions_text_dict = {}
    print("Loading text versions of referenced revisions")

    for revision_tag in revision_set:
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            revision_tag.lower() + ".pdf")
        print("\t%s" % revision_tag)
        try:
            contents = parser.from_file(path)["content"]
            revisions_text_dict[revision_tag] = contents
        except FileNotFoundError as fnfe:
            print(fnfe)
            print("\t[WARNING] Could not find revision %s in draft/papers" % revision_tag)

    return revisions_text_dict

# # r"\[" + re.escape(identifier) + r"\][\s\S]+?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
# def extract_chapter_text(revision_text, identifier, paragraph_id):
#     # regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?\n—?\(?"\
#     #         + re.escape(paragraph_id) + "\)?([\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]" # spaces instead of newlines near the end, the title is always in one line
#     regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?(?:[\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
#     # regex2 = r"(?:—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"
#     regex2 = r"(?:—?\(?((?:^|\(|\—)" + re.escape(paragraph_id) + r")\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"
#
#     result = re.findall(regex, revision_text) # TODO check edge cases (EOF...)
#     result2 = re.findall(regex2, result[0], re.M)
#     if result is None or len(result) != 1:
#         handleTHIS = "TODO"
#
#     return result2[0]


# r"\[" + re.escape(identifier) + r"\][\s\S]+?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
def extract_chapter_text(referenced_text, referenced_section):
    referenced_chapter = referenced_section[0]
    referenced_paragraph = referenced_section[1]

    referenced_chapter_regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_NUM_ID, re.escape(referenced_chapter), 1)
    referenced_chapter_text = re.findall(referenced_chapter_regex, referenced_text, re.M) #TODO exclude chapter title from the match, reason: chapter id can be same as paragraph id especally in the first few chapters, could cause problems when matching paragraph
    referenced_chapter_bracket_id = referenced_chapter_text[0][1]

    # referenced_paragraph_regex = REVISION_PARAGRAPH_REGEX[0] + re.escape(referenced_paragraph) + REVISION_PARAGRAPH_REGEX[1]
    referenced_paragraph_regex = PARAGRAPH_PARSING_REGEX.replace(PARAGRAPH_PARSING_REGEX_NUM_ID, re.escape(referenced_paragraph), 1)
    referenced_paragraph_text = re.findall(referenced_paragraph_regex, referenced_chapter_text[0][2], re.M)
    # TODO paragraph regex matches everything until next identifier, may cause issues
    debug = 0

    return referenced_paragraph_text, referenced_chapter_bracket_id





    # regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?\n—?\(?"\
    #         + re.escape(paragraph_id) + "\)?([\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]" # spaces instead of newlines near the end, the title is always in one line


    # regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?(?:[\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
    # # regex2 = r"(?:—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"
    # regex2 = r"(?:—?\(?((?:^|\(|\—)" + re.escape(paragraph_id) + r")\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"
    #
    # result = re.findall(regex, revision_text) # TODO check edge cases (EOF...)
    # result2 = re.findall(regex2, result[0], re.M)
    # if result is None or len(result) != 1:
    #     handleTHIS = "TODO"
    #
    # return result2[0]

# def find_referenced_text(revision_text, referenced_revision_tag,
#                          referenced_chapter, referenced_paragraph):
#     try:
#         with open("%s%s.txt" % (chapter_extractor.SECTION_FILE_SHARED_NAME, referenced_revision_tag), 'r') as f:
#             regex = re.escape(referenced_chapter) + r": (\S+) - (.+)"
#             referenced_section_identifiers = re.search(regex, f.read())
#             if referenced_section_identifiers:
#                 return extract_chapter_text(revision_text, referenced_section_identifiers[1], referenced_paragraph)
#             else:
#                 return
#                 # TODO error handling
#     except:
#         return
#         # TODO error handling


def find_referenced_text(revision_text, revision_tag, references, target_text):
    for reference in references:
        if reference["document"]["document"] == revision_tag:
            referenced_section = re.split("[:/]", reference["document"]["section"]) # TODO other variations
            if referenced_section is None or len(referenced_section) != 2:
                print("Faulty reference")  # TODO error

            referenced_text, referenced_chapter_id = extract_chapter_text(revision_text, referenced_section)
            reference["document"]["section"] = target_revision_find_paragraph_id(target_text,
                                                                                 referenced_text,
                                                                                 referenced_section,
                                                                                 referenced_chapter_id)


# def find_referenced_text(revision_text, referenced_revision_tag,
#                          referenced_chapter, referenced_paragraph):
#     try:
#         with open("%s%s.txt" % (chapter_extractor.SECTION_FILE_SHARED_NAME, referenced_revision_tag), 'r') as f:
#             regex = re.escape(referenced_chapter) + r": (\S+) - (.+)"
#             referenced_section_identifiers = re.search(regex, f.read())
#             if referenced_section_identifiers:
#                 return extract_chapter_text(revision_text, referenced_section_identifiers[1], referenced_paragraph)
#             else:
#                 return
#                 # TODO error handling
#     except:
#         return
#         # TODO error handling


# def target_revision_find_paragraph_id(target_revision_tag, target_revision_text, referenced_text):
#     regex = REVISION_PARAGRAPH_REGEX
#     result = re.findall(regex, target_revision_text, re.M) # re.M makes ^$ match after and before line breaks in the subject string
#
#     if result is None:
#         handleTHIS = "TODO"
#     else:
#         for t in result:
#             if t[2] == referenced_text[1]: #difflib
#                 return t[1] # TODO regex match whole chapter first to be able to find both chapter
#                             # and paragraph id
#             else:
#                 handleTHIS = "TODO"
#
#     return "err"

def func(r1a):
    max_i = 0
    max_r = 0
    for i in range(len(r1a)):
        if r1a[i][1] > max_r:
            max_i = i

    return r1a[max_i]


def target_revision_find_paragraph_id(target_revision_text, referenced_paragraph_text, referenced_section, referenced_chapter_id):
    # Find the same chapter (either via section mapping or regex)
    # Attempt to match paragraph with difflib
    # If no results, extend search to all chapters and repeat
    # return chapter:paragraph

    regex = CHAPTER_PARSING_REGEX.replace(CHAPTER_PARSING_REGEX_BRACKET_ID, re.escape(referenced_chapter_id), 1)
    id = ""

    presumed_target_text_chapter = re.findall(regex, target_revision_text, re.M)
    if presumed_target_text_chapter:
        id += presumed_target_text_chapter[0][0]
    else:
        t = 0
        # traverse whole document

    target_chapter_paragraphs = re.findall(PARAGRAPH_PARSING_REGEX, presumed_target_text_chapter[0][1], re.M)
    #TODO match paragraphs correctly if they're split by new page

    r1a = []
    r2a = []
    for paragraph in target_chapter_paragraphs:
        matcher = difflib.SequenceMatcher(None, referenced_paragraph_text[0][1], paragraph[2])
        ratio1 = matcher.ratio()
        ratio2 = matcher.quick_ratio()
        #ratio3 = matcher.real_quick_ratio()

        if ratio1 > 0.3: r1a.append((paragraph, ratio1))
        if ratio2 > 0.9: r2a.append((paragraph, ratio2))
        #opcodes = matcher.get_opcodes()
        #matcher = difflib.get_close_matches(referenced_paragraph_text[0][1], paragraph, 1, 0.9)

    m = func(r1a)
    id += ":"
    id += m[0][0]
    return id
    debug = 0

    target_text_paragraph = re.findall(re.escape(referenced_paragraph_text[0][1]), presumed_target_text_chapter[0][1], re.M)





    referenced_chapter = referenced_section[0]
    referenced_paragraph = referenced_section[1]

    referenced_chapter_regex = r"^" + re.escape(referenced_chapter) + CHAPTER_PARSING_REGEX
    referenced_chapter_text = re.findall(referenced_chapter_regex, referenced_text, re.M) #TODO exclude chapter title from the match, reason: chapter id can be same as paragraph id especally in the first few chapters, could cause problems when matching paragraph

    referenced_paragraph_regex = REVISION_PARAGRAPH_REGEX[0] + re.escape(referenced_paragraph) + REVISION_PARAGRAPH_REGEX[1]
    referenced_paragraph_text = re.findall(referenced_paragraph_regex, referenced_chapter_text[0], re.M)
    # TODO paragraph regex matches everything until next identifier, may cause issues
    debug = 0

    return referenced_paragraph_text









    regex = REVISION_PARAGRAPH_REGEX
    result = re.findall(regex, target_revision_text, re.M) # re.M makes ^$ match after and before line breaks in the subject string

    if result is None:
        handleTHIS = "TODO"
    else:
        for t in result:
            if t[2] == referenced_text[1]: #difflib
                return t[1] # TODO regex match whole chapter first to be able to find both chapter
                            # and paragraph id
            else:
                handleTHIS = "TODO"

    return "err"

def process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag):
    debug = 0

    print("Mappng references to %s" % target_revision_tag)
    target_text = revisions_text_dict[target_revision_tag]
    for tag, revision_text in revisions_text_dict.items():
        if tag != target_revision_tag:
            referenced_text = find_referenced_text(revision_text, tag, references, target_text)




    for reference in references:
        referenced_revision_tag = reference["document"]["document"].lower()
        referenced_section = reference["document"]["section"].split(':')
        if referenced_section is None or len(referenced_section) != 2:
            print("Faulty reference")  # TODO error
        referenced_chapter = referenced_section[0]
        referenced_paragraph = referenced_section[1]

        referenced_text = find_referenced_text(revisions_text_dict[referenced_revision_tag], referenced_revision_tag,
                                               referenced_chapter, referenced_paragraph)
        reference["document"]["section"] = target_revision_find_paragraph_id(target_revision_tag, revisions_text_dict[target_revision_tag], referenced_text)


def main(argv):
    try:
        # TODO add option to use local references by provding path
        revision_set = set()
        revision_set.add(argv[1])  # add target revision tag to the set
        references = chapter_mapping.load_references()

        chapter_mapping.extract_revision_tag_list_from_references(references, revision_set)
        revisions_text_dict = read_referenced_revisions(revision_set)

        process_referenced_paragraphs(references, revisions_text_dict, argv[1])

        # if chapter_mapping_to_target doesn't exist. create it

        path = os.path.join(os.path.dirname(__file__), argv[1])
        # path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/', argv[1])
        # path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'WebstormProjects/PDF/',
        #                     argv[1].lower())
        if path[-4:].lower() != ".pdf":
            path += ".pdf"

        with open("referencesSmall.json") as url:
            references = json.loads(url.read())
            map_paragraphs_to_target_revision(references, argv[1])

    except (RuntimeError, IndexError, FileNotFoundError) as e:
        print(e)
        print("Usage: \"paragraphMapping.py <tag>\"\ne.g. \"paragraphMapping.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)
