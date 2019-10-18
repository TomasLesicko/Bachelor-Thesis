import json
import re
from urllib.request import urlopen

CURRENT_REVISION_TAG = "n4820"


def extract_revision_tag_list_from_references(revision_set):
    with urlopen("https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/references.json") as url:
        references = json.loads(url.read())
        for reference in references:
            revision_set.add(reference['document']['document'].lower())


def read_current_revision_sections(regex_expr, current):
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


def write_mapping(older_revision_sections):
    with open("section_mapping_to_" + CURRENT_REVISION_TAG + ".json", 'w') as sm:
        json.dump(older_revision_sections, sm, indent = 4)


def main():
    revision_set = set()
    current = {}
    older_revision_sections = {}
    
    regex_expr = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'

    extract_revision_tag_list_from_references(revision_set)
    read_current_revision_sections(regex_expr, current)
    map_revision_sections(regex_expr, revision_set, current, older_revision_sections)
    write_mapping(older_revision_sections)


if __name__ == "__main__":
    main()
