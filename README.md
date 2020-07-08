# Bachelor-Thesis

C++14 - mapping between the standard document and a 
formal semantics

The mapping extracts references from comments of C++ semantics, 
maps the referenced sections to the target revision if possible, 
and highlights the referenced sections in the target revision. 
The resulting revision is in PDF, though highlighting the mapped 
references is also possible in HTML format if HTML files for 
target revision are provided.
Tested on Xubuntu 18.04


Cloning

  Either:
  git clone --recurse-submodules https://github.com/TomasLesicko/Bachelor-Thesis.git

  or if main repository is already cloned:
  git submodule update --init --recursive


Prerequisites

  - Git
  - g++
  - Java (default-jre) - required to run tika server
  - tika server jar file (downloadable using script in project/tika_server)
    or on http://tika.apache.org/download.html
  - Python 3 (and pip3)
    - required libraries can be installed using "pip3 install -r requirements.txt"
      or separately:
      - GitPython (pip3 install gitpython)
      - Beautiful Soup (pip3 install bs4)
      - tika-python (pip3 install tika)
      - PyMuPDF (https://github.com/pymupdf/PyMuPDF/wiki/Ubuntu-Installation-Experience)
  - For HTML revisions only, all prerequisites listed on https://github.com/Eelis/cxxdraft-htmlgen

If running for the first time or when a new reference from a previously 
unreferenced revision is added, the mapping has to generate new files, 
which may take a few minutes.
If a .txt format of a referenced revision is not present, it is necessary 
to run tika server (located in project/tika_server if downloaded using 
the provided script):

  java -jar tika_server_file.jar --port port_number
  e.g. java -jar tika-server-1.24.1.jar --port 9997

If all referenced revision .txt files were previously generated, there 
is no need to run tika server.

To generate an annotated PDF revision, run mapping.sh in project directory,
with port_number argument only being necessary if new .txt files have to
be generated:

  ./mapping.sh revision_tag [port_number]


Output:

  - annotated version of target revision in PDF format in project directory
  - referenceErrors.json in project/section_mapping, listing references that
    couldn't be mapped
  - mapping cache in project/section_mapping/cache, used to speed up mapping
    to the same revision in the future. Any references that cannot be mapped
    automatically for any reason can still be added to the cache manually


HTML versions first require HTML files of the revision, which can be
generated using https://github.com/Eelis/cxxdraft-htmlgen, then they need 
to be placed in the same folder as files in project/JS/HTML. Currently, 
only one revision at the time is supported. The current supported revision 
is n4861.
