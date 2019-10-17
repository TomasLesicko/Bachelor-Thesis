

var colorReferencedBlocks = function() {

    // var dictionaryStr = sessionStorage.getItem('dictionary');
    // var referencesStr = sessionStorage.getItem('references');
    var dictionary = JSON.parse(sessionStorage.getItem('dictionary'));
    var references = JSON.parse(sessionStorage.getItem('references'));
    var mapping = JSON.parse(sessionStorage.getItem('mapping'));

    // for(var i = 0; i < references.length; i++) {
    //     var deb = typeof(references);
    //         var sectionInfo = references[i].document.section.split(':');
    //
    //         var HTMLpage = dictionary[sectionInfo[0]]+".html";
    //         var thisPage = location.pathname.split("/").slice(-1);
    //
    //         if(HTMLpage === thisPage[0]) {
    //             if(references[i].document.document === "n4820") {
    //                 document.getElementById(sectionInfo[1]).style.backgroundColor = "#009933";
    //             } else {
    //                 var mappedSectionInfo = mapping[references[i].document.document][sectionInfo[0]];
    //
    //                 document.getElemefindntById(sectionInfo[1]).style.backgroundColor = "#66ff66";
    //             }
    //
    //         }
    // }

    var faultyReferenceFormatCounter = 0;
    for(var i = 0; i < references.length; i++) {
        var sectionInfo = references[i].document.section.split(/[:\/]+/); // supports 1.2:3 and 1.2/3

        if (typeof(sectionInfo) == 'undefined' || sectionInfo.length < 2) {
            ++faultyReferenceFormatCounter;
            continue;
        }

        var thisPage = location.pathname.split("/").slice(-1);
        var mappedSectionInfo;
        var color;

        if(references[i].document.document !== "n4820") {
            mappedSectionInfo = mapping[references[i].document.document.toLowerCase()][sectionInfo[0]];
            color = "#66ff66"
        } else {
            mappedSectionInfo = sectionInfo[0];
            color = "#009933";
        }

        var HTMLpage = dictionary[mappedSectionInfo]+".html";


        if(HTMLpage === thisPage[0]) {
            var blocks = sectionInfo[1].split('-');
            for (var j = 0; j < blocks.length; ++j) {
                document.getElementById(blocks[j]).style.backgroundColor = color;
            }

            // document.getElementById(sectionInfo[1]).style.backgroundColor = color;
        }
    }

    if (faultyReferenceFormatCounter > 0) {
        alert(faultyReferenceFormatCounter + " faulty reference formats found.")
    }

};
