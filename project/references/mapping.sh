#!/bin/bash
if [ -e references.json ]
then
    python3.6 annotatePDF.py "$@"
else
    echo Could not find references.json, attempting to extract references from semantics
    if  ! [ -e referenceExtractor.out ]
    then
        g++ referenceExtractor.cpp -std=c++17 -lstdc++fs -o referenceExtractor.out
    fi
    ./referenceExtractor.out ../../c-semantics/semantics/cpp
    python3.6 annotatePDF.py "$@"
fi
