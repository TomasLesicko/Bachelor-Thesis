import json
import re
import sys
import chapter_extractor
import os

SECTIONS_LINE_PARSING_REGEX = r'([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:.+)\n'
SECTION_MAPPING_SHARED_NAME = "section_mapping_to_"


def load_references():
    try:
        print("Opening references.json")
        with open("references.json", 'r') as references:
            references_json = json.loads(references.read())
            return references_json
    except FileNotFoundError as fnfe:
        print(fnfe)
        print("Failed to find references.json, attempting to extract references from semantics")

        return {}


def find_referenced_revision_tags(references, revision_set):
    """Store all revision tags from references to revision_set.

    The references in references.json are extracted from different C++ 
    standard revisions (e.g. n.4140, n4296...). This function finds all
    used tags and stores them to revision_set.
    revision_set -- set containing all revision tags from references
    """
    print("Searching for revision tags in references")
    for reference in references:
        revision_set.add(reference['document']['document'].lower())


def read_target_revision_sections(target_tag, current, allow_recursion=True):
    try:
        with open("%s%s.txt" % (chapter_extractor.SECTION_FILE_SHARED_NAME, target_tag), 'r') as sections_text:
            matches = re.findall(SECTIONS_LINE_PARSING_REGEX, sections_text.read())
            for section_tuple in matches:
                current[section_tuple[1]] = section_tuple[0]
    except FileNotFoundError:
        if allow_recursion:
            print("Could not find file %s%s.txt, attempting to create it" % (
                chapter_extractor.SECTION_FILE_SHARED_NAME, target_tag))
            chapter_extractor.extract_relevant_revision_sections({target_tag})
            read_target_revision_sections(target_tag, current, False)


def map_revision_sections(revision_set, current, older_revision_sections, allow_recursion=True):
    for revision_tag in revision_set:
        try:
            with open("%s%s.txt" % (chapter_extractor.SECTION_FILE_SHARED_NAME, revision_tag), 'r') as sections_text:
                regex_results = re.findall(SECTIONS_LINE_PARSING_REGEX, sections_text.read())
                this_revision_sections = {}
                for section_tuple in regex_results:
                    maps_to = current.get(section_tuple[1])
                    this_revision_sections[section_tuple[0]] = maps_to
                older_revision_sections[revision_tag] = this_revision_sections
        except FileNotFoundError:
            if allow_recursion:
                print("One or more section_names files could not be found, attempting to create them")
                chapter_extractor.extract_relevant_revision_sections({revision_tag})
                map_revision_sections({revision_tag}, current, older_revision_sections, False)


def write_mapping(older_revision_sections, target_tag):
    with open("%s%s.json" % (SECTION_MAPPING_SHARED_NAME, target_tag), 'w') as sm:
        json.dump(older_revision_sections, sm, indent=4)


def is_valid_revision(name):
    valid = r"^n\d{4}$"
    return re.search(valid, name.lower())


def map_sections(tag, references=None):
    revision_set = set()
    current = {}
    older_revision_sections = {}
    if not references:
        references = load_references()

    find_referenced_revision_tags(references, revision_set)
    read_target_revision_sections(tag, current)
    map_revision_sections(revision_set, current, older_revision_sections)
    write_mapping(older_revision_sections, tag)


def main(argv):
    if len(argv) != 2 or not is_valid_revision(argv[1]):
        print("Usage: \"chapter_mapping.py <tag>\"\ne.g. \"chapter_mapping.py n4296\"")
    else:
        map_sections(argv[1])


if __name__ == "__main__":
    main(sys.argv)
