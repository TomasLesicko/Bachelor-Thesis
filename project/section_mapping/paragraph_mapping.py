import os.path
import sys
import re
from tika import parser
import json

import chapter_extractor
import chapter_mapping

SECTIONS_LINE_REGEX = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'
REVISION_PARAGRAPH_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(^—?\(?(\d+(?:\.\d+)*)\)?))"
# REVISION_PARAGRAPH_REGEX = r"(^—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=\1)"

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
-not sure what to do if the paragraph was moved to a different chapter
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

    for revision_tag in revision_set:
        path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'draft/papers/',
                            revision_tag.lower() + ".pdf")
        try:
            contents = parser.from_file(path)["content"]
            revisions_text_dict[revision_tag] = contents
        except FileNotFoundError as fnfe:
            print(fnfe)
            print("Could not find revision %s in draft/papers" % revision_tag)

    return revisions_text_dict

# r"\[" + re.escape(identifier) + r"\][\s\S]+?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
def extract_chapter_text(revision_text, identifier, paragraph_id):
    # regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?\n—?\(?"\
    #         + re.escape(paragraph_id) + "\)?([\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]" # spaces instead of newlines near the end, the title is always in one line
    regex = r"\[" + re.escape(identifier) + r"\][\s\S]+?(?:[\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]"
    # regex2 = r"(?:—?\(?(\d+(?:\.\d+)*)\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"
    regex2 = r"(?:—?\(?((?:^|\(|\—)" + re.escape(paragraph_id) + r")\)?)([\s\S]+?)(?=(?:—?\(?(?:\d+(?:\.\d+)*)\)?))"

    result = re.findall(regex, revision_text) # TODO check edge cases (EOF...)
    result2 = re.findall(regex2, result[0], re.M)
    if result is None or len(result) != 1:
        handleTHIS = "TODO"

    return result2[0]


def find_referenced_text(revision_text, referenced_revision_tag,
                         referenced_chapter, referenced_paragraph):
    try:
        with open("%s%s.txt" % (chapter_extractor.SECTION_FILE_SHARED_NAME, referenced_revision_tag), 'r') as f:
            regex = re.escape(referenced_chapter) + r": (\S+) - (.+)"
            referenced_section_identifiers = re.search(regex, f.read())
            if referenced_section_identifiers:
                return extract_chapter_text(revision_text, referenced_section_identifiers[1], referenced_paragraph)
            else:
                return
                # TODO error handling
    except:
        return
        # TODO error handling


def target_revision_find_paragraph_id(target_revision_tag, target_revision_text, referenced_text):
    regex = REVISION_PARAGRAPH_REGEX
    result = re.findall(re.escape(referenced_text[1]), target_revision_text, re.M) # re.M makes ^$ match after and before line breaks in the subject string

    if result is None or len(result) != 1:
        handleTHIS = "TODO"
    else:
        x = 4

def process_referenced_paragraphs(references, revisions_text_dict, target_revision_tag):
    for reference in references:
        referenced_revision_tag = reference["document"]["document"].lower()
        referenced_section = reference["document"]["section"].split(':')
        if referenced_section is None or len(referenced_section) != 2:
            print("Faulty reference")  # TODO error
        referenced_chapter = referenced_section[0]
        referenced_paragraph = referenced_section[1]

        referenced_text = find_referenced_text(revisions_text_dict[referenced_revision_tag], referenced_revision_tag,
                                               referenced_chapter, referenced_paragraph)
        target_revision_find_paragraph_id(target_revision_tag, revisions_text_dict[target_revision_tag], referenced_text)


"""
(^—?\(?(\d+(?:\.\d+)*)\)?)[\s\S]+?(?=(^—?\(?(\d+(?:\.\d+)*)\)?))


^.*\[except\.handle\][\s\S]*?\n—?\(?3\.1\)?([\s\S]+?)\n\n[\s\S]*?[A-Z0-9]+(?:\.\d+)* .+? \[.+?\]

—?\(?(\d+(?:\.\d+)*)\)?[\s\S]+?\n
"""
def main(argv):
    try:
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
