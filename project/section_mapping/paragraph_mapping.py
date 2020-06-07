import os.path
import sys
import re
from tika import parser
import json

import chapter_extractor
import chapter_mapping


"""
- find all tags in refs + target ref tag, then open the contents in tika and save it in a dictionary
- go through ref sections, find chapter.name.id via section id, if chapter names file doesn't
    exist, create it via chapter extractor
- edit the entry a bit so it fits regex
- use regex to find the chapter and extract it with regex like
    "13.3 Handling an exception \[except.handle\][\s\S]*\d+\.\d+ (\w+ )+\[\w+\.\w+\]"
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
        if  referenced_tag.lower() != target_tag.lower():
            path = os.path.join(os.path.dirname(__file__), referenced_tag.lower() + ".pdf")
            contents = parser.from_file(path)["content"] #can't do this too inefficient
            #perhaps find tags, then create a dictionary containing loaded contents of all revisions
            search_paragraph_by_section_id(reference["document"]["section"], contents)


def main(argv):
    try:
        revision_set = set()
        revision_set.add(argv[1])

        chapter_mapping.extract_revision_tag_list_from_references(revision_set)



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
        print("Usage: \"annotatePDF.py <tag>\"\ne.g. \"annotatePDF.py n4296\"")


if __name__ == "__main__":
    main(sys.argv)