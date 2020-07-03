(function() {
    "use strict";

    const currentRevisionTag = "n4820";

    let chapterNameDict = JSON.parse(sessionStorage.getItem('dictionary'));
    let references = JSON.parse(sessionStorage.getItem('references'));
    let chapterMapping = JSON.parse(sessionStorage.getItem('mapping'));

    let thisHTMLPageName = location.pathname.split("/").slice(-1)[0];
    let faultyReferenceFormatCounter = 0;


    function colorSection(similarityRatio, section) {
        document.getElementById(section).style.backgroundColor =
                getHighlightColor(similarityRatio);
    }

    function annotateSection(reference, section) {
        document.getElementById(section).title = getAnnotation(reference);
    }

    function getHighlightColor(similarityRatio) {
        let r, b;
        r = b = "00";
        let g = (Math.round(similarityRatio * 255)).toString(16);

        return "#" + r + g + b;

    }

    function getAnnotation(reference) {
        let similarityPercentage = Math.round((10000*reference.similarity))/100;
        let annot = reference.semantics.file;
        if (reference.document.TODO === "true") {
            annot += "\nMarked as TODO";
        }

        annot += "\n" + JSON.stringify(reference.semantics.lines) + "\n" +
            (similarityPercentage).toString() +
            "% match with paragraph in referenced revision ("
            + reference.document.document + ")";

        return annot;
    }

    function handleFaultyReferences() {
        if (faultyReferenceFormatCounter > 0) {
            alert(faultyReferenceFormatCounter +
                " faulty reference formats found.")
        }
    }

    function highlightReferencedSections() {
        references.forEach((reference) => {
            highlightRelevantSection(reference);
        });

        handleFaultyReferences();
    }

    function highlightRelevantSection(reference) {
        // supports 1.2:3 and 1.2/3
        let section = reference.document.section.split(/[:\/]+/);

        let chapter = section[0];
        let HTMLPageName;

        if (!isValidReference(section)) {
            ++faultyReferenceFormatCounter;
            return;
        }

        HTMLPageName = chapterNameDict[chapter]+".html";

        if (HTMLPageName === thisHTMLPageName) {
            let paragraph = section[1];
            colorSection(reference.similarity, paragraph);
            annotateSection(reference, paragraph);
        }
    }

    function isValidReference(chapterAndSection) {
        /*
        section must be a valid value and consist of a chapter index
        and at least one section id
         */
        return chapterAndSection && chapterAndSection.length >= 2;
    }

    // Chapters and paragraphs are now mapped by paragraph_mapping.py
    // script.js already receives mapped references
    function mapChapterToCurrentRevision(revisionTag, chapter) {
        return (revisionTag === currentRevisionTag) ?
            chapter : chapterMapping[revisionTag.toLowerCase()][chapter];
    }


    highlightReferencedSections();
}());
