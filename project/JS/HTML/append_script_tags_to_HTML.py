#!/usr/bin/env python

import os
import sys
from bs4 import BeautifulSoup


def append_new_tag(soup, script_tag, src=None, string=""):
    if src:
        new_tag = soup.new_tag(script_tag, src=src)
    else:
        new_tag = soup.new_tag(script_tag)

    soup.body.append(new_tag)
    if string:
        new_tag.string = string


def append_tags_to_index_html(script_tag, directory):
    if not directory:
        directory = os.getcwd()
    fname = os.path.join(directory, "index.html")
    print("appending to index")

    with open(fname, 'r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

        append_new_tag(soup, script_tag, "https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js")
        append_new_tag(soup, script_tag, "processRefs.js")

    with open(fname, 'w') as f:
        f.write(str(soup))


def append_tags_to_html_files(script_tag, directory):
    if not directory:
        directory = os.getcwd()
    html_page_exceptions = ['index.html']

    for filename in os.listdir(directory):
        if filename.endswith('.html') and filename not in html_page_exceptions:
            fname = os.path.join(directory, filename)
            print("appending to %s" % filename)
            with open(fname, 'r') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')

                append_new_tag(soup, script_tag, "script.js")
                append_new_tag(soup, script_tag, string="colorReferencedBlocks()")

            with open(fname, 'w') as f:
                f.write(str(soup))


def main(argv):
    script_tag = 'script'
    if len(argv) > 1:
        path = argv[1]
    else:
        path = ""

    append_tags_to_index_html(script_tag, path)
    append_tags_to_html_files(script_tag, path)


if __name__ == "__main__":
    main(sys.argv)
