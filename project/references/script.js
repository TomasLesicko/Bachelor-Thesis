'use strict';

var colorReferencedBlocks = function() {

    var dictionary = JSON.parse(sessionStorage.getItem('dictionary'));
    var references = JSON.parse(sessionStorage.getItem('references'));
    var mapping = JSON.parse(sessionStorage.getItem('mapping'));

    var thisPage = location.pathname.split("/").slice(-1);

    var faultyReferenceFormatCounter = 0;
    for(var i = 0; i < references.length; i++) {
        var section = references[i].document.section.split(/[:\/]+/); // supports 1.2:3 and 1.2/3

        if (typeof(section) == 'undefined' || section.length < 2) {
            ++faultyReferenceFormatCounter;
            continue;
        }

        var mappedSectionInfo;
        var color;

        if(references[i].document.document !== "n4820") {
            mappedSectionInfo = mapping[references[i].document.document.toLowerCase()][section[0]];
            color = "#66ff66";
        } else {
            mappedSectionInfo = section[0];
            color = "#009933";
        }

        var HTMLpage = dictionary[mappedSectionInfo]+".html";


        if(HTMLpage === thisPage[0]) {
            var blocks = section[1].split('-');
            for (var j = 0; j < blocks.length; ++j) {
                document.getElementById(blocks[j]).style.backgroundColor = color;

                //semantics comments
                document.getElementById(blocks[j]).setAttribute('title', "file: " +
                    references[i].semantics.file + " ,line: " + references[i].semantics.line);
            }
        }

        if (i === references.length - 2) {
            var xyz = 4;
        }
    }

    if (faultyReferenceFormatCounter > 0) {
        alert(faultyReferenceFormatCounter + " faulty reference formats found.")
    }

};
