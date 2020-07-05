(function() {
    "use strict";

    const sectionNamesProcessingRegex = /:\s|\s-\s/;

    function processLine(line, dict, regex) {
        let splitLine = line.split(regex);
        dict[splitLine[0]] = splitLine[1];
    }

    function processSectionNames(sectionNamesFile) {
        /*
        sectionNamesFile is in the following format:
        "chapter.subchapter: html.name - Name\n" e.g.:
        "5.12: lex.operators - Operators and punctuators\n"

        returns a dict with k=chapters, v=html names, full names are redundant
         */

        let sectionNamesDict = {};
        let lines = sectionNamesFile.split("\n");

        lines.forEach((line) =>
            processLine(line, sectionNamesDict, sectionNamesProcessingRegex)
        );

        return sectionNamesDict;
    }

    function fetchFiles() {
        if(sessionStorage.getItem("references") === null){
            jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
                "Bachelor-Thesis/master/project/JS/references_mapped_n4820.json",
                function(data) {
                    sessionStorage.setItem("references", data);
                });
        }

        if(sessionStorage.getItem("dictionary") === null){
            jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
                "Bachelor-Thesis/master/project/JS/section_names_" +
                "n4820.txt",
                function(data) {
                    sessionStorage.setItem("dictionary",
                        JSON.stringify(processSectionNames(data)));
                });
        }

        if(sessionStorage.getItem("mapping") === null){
            jQuery.get("https://raw.githubusercontent.com/TomasLesicko/" +
                "Bachelor-Thesis/master/project/JS/" +
                "section_mapping_to_n4820.json",
                function(data) {
                    sessionStorage.setItem("mapping", data);
                });
        }
    }


    fetchFiles();
}());
