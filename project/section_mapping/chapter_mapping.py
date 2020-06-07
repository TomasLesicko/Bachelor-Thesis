import json
import re
from urllib.request import urlopen

import chapter_extractor

SECTIONS_LINE_PARSING_REGEX = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'
FILE_SHARED_NAME = "secton_names_"

def extract_revision_tag_list_from_references(revision_set):
    """Store all revision tags from references to revision_set.

    The references in references.json are extracted from different C++ 
    standard revisions (e.g. n.4140, n4296...). This function finds all
    used tags and stores them to revision_set.
    revision_set -- set containing all revision tags from references
    """
    with urlopen("https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/references.json") as url:
        references = json.loads(url.read())
        for reference in references:
            revision_set.add(reference['document']['document'].lower())


def read_target_revision_sections(target_tag, regex, current, allow_recursion=True):
    try:
        with open(FILE_SHARED_NAME + target_tag + ".txt", 'r') as sections_text:
            matches = re.findall(regex, sections_text.read())
            for tuple in matches:
                current[tuple[1]] = tuple[0]
    except FileNotFoundError:
        if allow_recursion:
            print("Could not find file " + FILE_SHARED_NAME + target_tag + ".txt, attempting to create it")
            tag_dict = {target_tag}
            chapter_extractor.extract_relevant_revision_sections(tag_dict)
            read_target_revision_sections(target_tag, regex, current, False)
            
            
def map_revision_sections(revision_set, current, older_revision_sections, allow_recursion=True):
    for revision_tag in revision_set:
        try:
            with open(FILE_SHARED_NAME + revision_tag + ".txt", 'r') as sections_text:
                regex_results = re.findall(SECTIONS_LINE_PARSING_REGEX, sections_text.read())
                this_revision_sections = {}
                for tuple in regex_results:
                    maps_to = current.get(tuple[1])
                    this_revision_sections[tuple[0]] = maps_to
                older_revision_sections[revision_tag] = this_revision_sections
        except FileNotFoundError:
            if allow_recursion:
                print("One or more section_names files could not be found, attempting to create them")
                chapter_extractor.extract_relevant_revision_sections(revision_set)
                map_revision_sections(revision_set, current, older_revision_sections, False)


def write_mapping(older_revision_sections, target_tag):
    with open("section_mapping_to_" + target_tag + ".json", 'w') as sm:
        json.dump(older_revision_sections, sm, indent = 4)


def main(argv):
    revision_set = set()
    current = {}
    older_revision_sections = {}

    extract_revision_tag_list_from_references(revision_set)
    read_target_revision_sections(SECTIONS_LINE_PARSING_REGEX, current)
    map_revision_sections(revision_set, current, older_revision_sections)
    write_mapping(older_revision_sections)


if __name__ == "__main__":
    main(argv)
