#!/usr/bin/env python3

from git import Repo
import os
import subprocess

SECTION_FILE_SHARED_NAME = "section_names_"


def extract_relevant_revision_sections(revision_tags):
    old = os.getcwd()
    os.chdir("../../draft")
    repo = Repo(".").git

    for tag in revision_tags:

        repo.checkout(tag)
        print(repo.status())

        os.chdir("source")

        try:
            subprocess.run("./sections.out std.tex > %s%s.txt" %
                           (SECTION_FILE_SHARED_NAME, tag),
                           shell=True, check=True)

        except subprocess.CalledProcessError as cpe:
            print("sections.cpp has to be compiled in draft/source\n"
                  "in draft/source, \"g++ ../tools/sections.cpp\"")
            subprocess.run("rm -f %s%s.txt" %
                           (SECTION_FILE_SHARED_NAME, tag),
                           shell=True, check=True)
            repo.checkout("master")
            os.chdir(old)
            raise cpe

        subprocess.run("mv %s%s.txt ../../project/section_mapping/" %
                       (SECTION_FILE_SHARED_NAME, tag),
                       shell=True, check=True)
        os.chdir("..")

    repo.checkout("master")
    os.chdir(old)


def main():
    revision_tags = {"n4296", "n4778"}
    extract_relevant_revision_sections(revision_tags)


if __name__ == "__main__":
    main()
