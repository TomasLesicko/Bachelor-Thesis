(function() {
    "use strict";

    const currentRevision = "n4820";

    var dictionary = JSON.parse(sessionStorage.getItem('dictionary'));
    var references = JSON.parse(sessionStorage.getItem('references'));
    var mapping = JSON.parse(sessionStorage.getItem('mapping'));

    var thisPage = location.pathname.split("/").slice(-1);
    var faultyReferenceFormatCounter = 0;


    function isValidReference(section) {
        /*
        section must be a valid value and consist of a chapter index
        and at least one section id
         */
        return section && section.length >= 2;
    }

    function getReferenceComment(reference) {
        return reference.semantics.file + ", line: " +
            reference.semantics.line;
    }

    function handleFaultyReferences() {
        //TODO different alerts for diferent problems
        if (faultyReferenceFormatCounter > 0) {
            alert(faultyReferenceFormatCounter + " faulty reference formats found.")
        }
    }

    function highlightReferencedSections() {
        references.forEach((reference) => {
            highlightRelevantSection(reference, dictionary, mapping);
        });

        handleFaultyReferences();
    }

    function highlightRelevantSection(reference, dictionary, mapping) {
        var section = reference.document.section.split(/[:\/]+/); // supports 1.2:3 and 1.2/3

        if (!isValidReference(section)) {
            ++faultyReferenceFormatCounter;
            return;
        }

        var mappedSectionInfo;
        var color;

        if(reference.document.document === currentRevision) {
            mappedSectionInfo = section[0];
            color = "#009933";
        } else {
            mappedSectionInfo = mapping[reference.document.document.toLowerCase()][section[0]];
            color = "#66ff66";
        }

        var HTMLpage = dictionary[mappedSectionInfo]+".html";


        if(HTMLpage === thisPage[0]) {
            var blocks = section[1].split('-');
            for (var j = 0; j < blocks.length; ++j) {
                document.getElementById(blocks[j]).style.backgroundColor = color;

                //semantics comments
                document.getElementById(blocks[j]).title = getReferenceComment(reference);
            }
        }
    }


    highlightReferencedSections();
}());
