#!/bin/bash
cd section_mapping
if ! [ -e ../../draft/source/sections.out ]
then
    echo "compiling sections.cpp"
    g++ ../../draft/tools/sections.cpp -o ../../draft/source/sections.out
fi
if [ -e references.json ]
then
    python3.6 chapter_mapping.py "$1"
    python3.6 annotatePDF.py "$@"
else
    echo Could not find references.json, attempting to extract references from semantics
    if  ! [ -e referenceExtractor.out ]
    then
        echo "compiling referenceExtractor.cpp"
        g++ referenceExtractor.cpp -std=c++17 -lstdc++fs -o referenceExtractor.out
    fi
    ./referenceExtractor.out ../../c-semantics/semantics/cpp
    python3.6 annotatePDF.py "$@"
fi
cd ..
mv section_mapping/$1_annotated.pdf .
