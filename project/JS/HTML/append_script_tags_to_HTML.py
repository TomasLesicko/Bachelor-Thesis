#!/usr/bin/env python3

import os
import sys
from bs4 import BeautifulSoup

SCRIPT_TAG = "script"
JQUERY_ADDRESS = "https://ajax.googleapis.com/ajax/libs/" \
                 "jquery/3.4.1/jquery.min.js"
INDEX_HTML_SCRIPT_NAME = "processRefs.js"
OTHER_HTML_SCRIPT_NAME = "script.js"
OTHER_HTML_FUNC_CALL = "colorReferencedBlocks()"


def append_new_tag(soup, script_tag, src=None, string=""):
    if src:
        new_tag = soup.new_tag(script_tag, src=src)
    else:
        new_tag = soup.new_tag(script_tag)

    soup.body.append(new_tag)
    if string:
        new_tag.string = string


def append_tags_to_html_files(script_tag, directory):
    if not directory:
        directory = os.getcwd()

    for filename in os.listdir(directory):
        if filename.endswith('.html'):
            fname = os.path.join(directory, filename)
            print("appending to %s" % filename)

            with open(fname, 'r') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                if filename == "index.html":
                    append_new_tag(soup, script_tag, JQUERY_ADDRESS)
                    append_new_tag(soup, script_tag, INDEX_HTML_SCRIPT_NAME)
                else:
                    append_new_tag(soup, script_tag, OTHER_HTML_SCRIPT_NAME)
                    append_new_tag(soup, script_tag,
                                   string=OTHER_HTML_FUNC_CALL)

            with open(fname, 'w') as f:
                f.write(str(soup))


def main(argv):

    if len(argv) > 1:
        path = argv[1]
    else:
        path = ""

    append_tags_to_html_files(SCRIPT_TAG, path)


if __name__ == "__main__":
    main(sys.argv)
