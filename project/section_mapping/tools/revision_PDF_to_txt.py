#!/usr/bin/env python3

import sys
import re
import os
from tika import tika, parser
from requests.exceptions import ConnectionError


def handle_error(e, msg):
    print(e)
    print(msg)


def save_txt_revision(txt_revision, revision_tag, save_to=""):
    try:
        with open("%s%s.txt" % (save_to, revision_tag), 'x') as f:
            print("\tWriting to %s.txt" % revision_tag)
            f.write(txt_revision)
    except FileExistsError:
        print("[Error] File with name %s.txt already exists" % revision_tag)
        print("Move or delete the file and rerun the script")


def is_valid_arg(arg):
    tag_regex = re.compile(r"^n\d{4}(?:\.pdf)?$", re.IGNORECASE)
    return tag_regex.match(arg)


def read_referenced_revisions(revision_set, port_num):
    for revision_tag in revision_set:
        read_referenced_revision(revision_tag, port_num)


def read_referenced_revision(revision_tag, port_num, save_to=""):
    """ Uses tika module to obtain a .txt version of a PDF
    Requires tika server to run, and correct port number
    as an argument.
    """
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir,
                        os.pardir, 'draft/papers/',
                        revision_tag.lower() + ".pdf")
    print("\tLoading %s.txt" % revision_tag)

    try:
        tika.TikaClientOnly = True
        contents = parser.from_file(path, "http://localhost:"
                                    + port_num + "/")["content"]
        save_txt_revision(contents, revision_tag, save_to)
        return contents
    except FileNotFoundError as fnfe:
        handle_error(fnfe, "[Error] Could not find revision %s.pdf in "
                           "draft/papers" % revision_tag)
    except ConnectionError as ce:
        handle_error(ce, "[Error] Wrong port number: %s, make sure tika server"
                         " is running with correct port number" % port_num)


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
        read_referenced_revisions(revision_set, argv[1])


if __name__ == "__main__":
    main(sys.argv)
