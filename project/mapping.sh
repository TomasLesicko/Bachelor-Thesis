#!/bin/bash
cd section_mapping || exit
if ! [ -e ../../draft/source/sections.out ]
then
    echo "compiling sections.cpp"
    g++ ../../draft/tools/sections.cpp -o ../../draft/source/sections.out
fi
if  ! [ -e referenceExtractor.out ]
then
    echo "compiling referenceExtractor.cpp"
    g++ referenceExtractor.cpp -std=c++17 -lstdc++fs -o referenceExtractor.out
fi
./referenceExtractor.out ../../c-semantics/semantics/cpp
python3.6 annotatePDF.py "$@"
cd ..
mv section_mapping/"$1"_annotated.pdf .
