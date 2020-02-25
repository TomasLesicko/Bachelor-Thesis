//TODO section names file and section mapping file names will change depending on revision, fetching needs to work regardless of current revision

var processRefs = function() {
    "use strict";

    function processLine(line, dict, regex){
        var splitLine = line.split(regex);
        dict[splitLine[0]] = splitLine[1];
    }

    function getProcessedSectionNames(sectionNamesFile){
        /*
        sectionNamesFile is in the following format:
        "chapter.subchapter: html.name - Name\n" e.g.:
        "5.12: lex.operators - Operators and punctuators\n"

        returns a dict with k=chapters, v=html names, full names are redundant
         */

        var sectionNamesDict = {};
        var lines = sectionNamesFile.split("\n");

        lines.forEach((line) =>
            processLine(line, sectionNamesDict, /:\s|\s-\s/)
        );

        return sectionNamesDict;
    }

    function fetchFiles() {
        jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
            "Bachelor-Thesis/master/project/references/references.json",
            function(data) {
            sessionStorage.setItem("references", data);
        });

        jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
            "Bachelor-Thesis/master/project/references/section_names_n4820.txt",
            function(data) {
            sessionStorage.setItem("dictionary",
                JSON.stringify(getProcessedSectionNames(data)));
        });

        jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
            "Bachelor-Thesis/master/project/section_mapping/" +
            "section_mapping_to_n4820.json",
            function(data) {
            sessionStorage.setItem("mapping", data);
        });
    }


    fetchFiles();
};