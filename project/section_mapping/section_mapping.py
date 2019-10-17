import json
import re
from urllib.request import urlopen


def extract_revision_tag_list_from_references(revision_set):
    with urlopen("https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/references.json") as url:
        references = json.loads(url.read())
        for reference in references:
            revision_set.add(reference['document']['document'].lower())


def read_current_revision_sections(regex_text_section_line, current):
    with open("section_names_n4820.txt", 'r') as sections_text:
        text = sections_text.read()
        matches = re.findall(regex_text_section_line, text)
        for tuple in matches:
            current[tuple[1]] = tuple[0]
            
def map_revision_sections(regex_text_section_line, revision_set, current, older_revision_sections):
    file_name = "section_names_"
    file_suffix = ".txt"
    
    for revision_tag in revision_set:
        
        with open(file_name + revision_tag + file_suffix, 'r') as sections_text:
            text = sections_text.read()
            r = re.findall(regex_text_section_line, text)
            this_revision_sections = {}
            for tuple in r:
                maps_to = current.get(tuple[1])
                this_revision_sections[tuple[0]] = maps_to
            older_revision_sections[revision_tag] = this_revision_sections


def write_mapping(older_revision_sections):
    with open("section_mapping_to_n4820.json", 'w') as sm:
        json.dump(older_revision_sections, sm, indent = 4)


def main():
    revision_set = set()
    current = {}
    older_revision_sections = {}
    
    regex_text_section_line = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'

    extract_revision_tag_list_from_references(revision_set)
    read_current_revision_sections(regex_text_section_line, current)
    map_revision_sections(regex_text_section_line, revision_set, current, older_revision_sections)
    write_mapping(older_revision_sections)

if __name__ == "__main__":
    main()
