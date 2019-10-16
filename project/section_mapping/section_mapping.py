import json
import re

revisions = ["n4296", "n4778"]
regex_text_section_line = '([A-Z0-9](?:\d)*(?:\.\d+)*): (\S+) - (?:[^\n]+)\n'


def read_current_revision_sections(current):
    with open("section_names_n4820.txt", 'r') as sections_text:
        text = sections_text.read()
        matches = re.findall(regex_text_section_line, text)
        for tuple in matches:
            current[tuple[1]] = tuple[0]
            
            
def map_revision_sections(revisions, current, older_revision_sections):
    file_name = "section_names_"
    file_suffix = ".txt"
    
    for revision_tag in revisions:
        
        with open(file_name + revision_tag + file_suffix, 'r') as sections_text:
            text = sections_text.read()
            r = re.findall(regex_text_section_line, text)
            this_revision_sections = {}
            for tuple in r:
                maps_to = current.get(tuple[1])
                this_revision_sections[tuple[0]] = maps_to
            older_revision_sections[revision_tag] = this_revision_sections


# with open("section_names_n4296.txt", 'r') as sections_text:
    # text = sections_text.read()
    # r = re.findall(regex_text_section_line, text)
    # this_revision_sections = {}
    # # for tuple in r:
        # # dicti[tuple[0]] = tuple[1]
    # # rs = json.dumps(dict(r))
    # for tuple in r:
        # maps_to = current_revision_sections.get(tuple[1])
        # print(tuple[1] + " maps to " + (maps_to if maps_to else "None"))
        # this_revision_sections[tuple[0]] = maps_to
    # older_revision_sections["n4296"] = this_revision_sections


#with open("section_names_n4778.txt", 'r') as sections_text:
#    text = sections_text.read()
#    r = re.findall(regex_text_section_line, text)
#    sections_dict["n4778"] = dict(r)


def write_mapping(older_revision_sections):
    with open("section_mapping_to_n4820.json", 'w') as sm:
        json.dump(older_revision_sections, sm, indent = 4)


def main():
    current = {}
    older_revision_sections = {}

    read_current_revision_sections(current)
    map_revision_sections(revisions, current, older_revision_sections)
    write_mapping(older_revision_sections)

if __name__ == "__main__":
    main()
