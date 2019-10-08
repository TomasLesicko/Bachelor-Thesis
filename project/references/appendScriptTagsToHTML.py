#!/usr/bin/env python

import os
from bs4 import BeautifulSoup

directory = os.getcwd()
scriptTag = 'script'
HTMLPageExceptions = ['index.html']

for filename in os.listdir(directory):
    if filename.endswith('.html') and filename not in HTMLPageExceptions:
        fname = os.path.join(directory,filename)
        with open(fname, 'r') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

            newtag = soup.new_tag(scriptTag, src="script.js")
            soup.body.append(newtag)

            newtag = soup.new_tag(scriptTag)
            soup.body.append(newtag)
            newtag.string = "colorReferencedBlocks()"

        with open(fname, 'w') as f:
            f.write(str(soup))

# TODO add script tags for index.html
