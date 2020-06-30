import sys
import re
sys.path.append("../section_mapping")
from paragraph_mapping import read_referenced_revisions


def save_txt_revisions(txt_revisions):
    for tag, text in txt_revisions.items():
        try:
            with open("%s.txt" % tag, 'x') as f:
                print("\tWriting to %s.txt" % tag)
                f.write(text)
        except FileExistsError as fee:
            print(fee)
            print("Move or delete the file and rerun the script")


def is_valid_arg(arg):
    tag_regex = re.compile(r"^n\d{4}(?:\.pdf)?$", re.IGNORECASE)
    return tag_regex.match(arg)


def main(argv):
    revision_set = set()

    for i in range(2, len(argv)):
        if not is_valid_arg(argv[i]):
            print("Invalid tag: %s" % argv[i])
        else:
            revision_set.add(argv[i].lower().split(".")[0])

    if not revision_set:
        print("Usage: revision_PDF_to_text.py <port number> [revision tags]\n"
              " e.g. \"revision_PDF_to_text.py 9997 n4140 N4296 n4800.pdf\"")
    else:
        txt_revisions = read_referenced_revisions(revision_set, argv[1])
        save_txt_revisions(txt_revisions)


if __name__ == "__main__":
    main(sys.argv)
