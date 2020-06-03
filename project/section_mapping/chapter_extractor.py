from contextlib import contextmanager
from git import Repo
import os
import subprocess


# @contextmanager
# def cd(newdir):
    # print(os.getcwd())
    # prevdir = os.getcwd()
    # os.chdir(os.path.expanduser(newdir))
    # try:
        # yield
        # print(os.getcwd())
    # finally:
        # print(os.getcwd())
        # os.chdir(prevdir)
        
def extract_relevant_revision_sections(revision_tags):
    
    old = os.getcwd()
    os.chdir("../../draft")
    repo = Repo(".").git
    
    for tag in revision_tags:

        repo.checkout(tag)
        print(repo.status())
        
        os.chdir("source")
        #subprocess.run("git checkout tags/"+tag, shell=True, check=True)
        
        subprocess.run("./a.out std.tex > section_names_"+tag+".txt", shell=True, check=True)
        subprocess.run("mv section_names_"+tag+".txt ../../project/section_mapping/", shell=True, check=True)
        os.chdir("..")
        
    repo.checkout("master")
    os.chdir(old)
    
#TODO extract most recent revision sections
#TODO remove section_names files except most recent revision from directory


def main():
    revision_tags = {"n4296", "n4778"}

    extract_relevant_revision_sections(revision_tags)
    # repo = Repo("../../draft").git
    # repo.checkout("tags/n4778")
    # old = os.getcwd()
    # print(old)
    # os.chdir('../../draft/source')
    # print(os.getcwd())
    # os.chdir(old)
    # print(os.getcwd())
    
    
if __name__ == "__main__":
    main()