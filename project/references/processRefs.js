'use strict';

var processRefs = function() {

    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/references.json', function(data) {
        sessionStorage.setItem('references', data);
    });

    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/section_names_n4820.txt', function(data) {
        var sectionNamesDict = {};
        var lines = data.split('\n');

        for(var i = 0; i < lines.length; i++) {
            var splitLine = lines[i].split(/:\s|\s-\s/);
            sectionNamesDict[splitLine[0]] = splitLine[1];

            //var splitLine = lines[i].split(" ");
            //sectionNamesDict[splitLine[0].slice(0, -1)] = splitLine[1];
        }
        sessionStorage.setItem('dictionary', JSON.stringify(sectionNamesDict));
    });

    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/section_mapping/section_mapping_to_n4820.json', function(data) {
        sessionStorage.setItem('mapping', data);
    });
};