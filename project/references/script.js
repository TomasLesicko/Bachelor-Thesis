(function() {
    "use strict";

    const currentRevisionTag = "n4820";

    const currentRevisionTagColor = "#009933";
    const differentRevisionTagColor = "#66ff66";

    let chapterNameDict = JSON.parse(sessionStorage.getItem('dictionary'));
    let references = JSON.parse(sessionStorage.getItem('references'));
    let chapterMapping = JSON.parse(sessionStorage.getItem('mapping'));

    let thisHTMLPageName = location.pathname.split("/").slice(-1)[0];
    let faultyReferenceFormatCounter = 0;


    function colorRelevantSections(revisionTag, sectionsToColor) {
        sectionsToColor.forEach((section) =>
            document.getElementById(section).style.backgroundColor =
                getHighlightColor(revisionTag));
    }

    function displaySemanticsComments(semantics, commentedSections) {
        commentedSections.forEach((section) =>
            document.getElementById(section).title =
                getReferenceComment(semantics));
    }

    function getHighlightColor(revisionTag) {
        return (revisionTag === currentRevisionTag) ?
            currentRevisionTagColor : differentRevisionTagColor;
    }

    function getReferenceComment(semantics) {
        return semantics.file + ", line: " + semantics.line;
    }

    function handleFaultyReferences() {
        //TODO different alerts for different problems
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
        let chapterAndSections = reference.document.section.split(/[:\/]+/);

        let currentRevisionChapter;
        let HTMLPageName;

        if (!isValidReference(chapterAndSections)) {
            ++faultyReferenceFormatCounter;
            return;
        }

        currentRevisionChapter = mapChapterToCurrentRevision(
            reference.document.document, chapterAndSections[0]);
        HTMLPageName = chapterNameDict[currentRevisionChapter]+".html";

        if (HTMLPageName === thisHTMLPageName) {
            let sections = chapterAndSections[1].split("-");

            colorRelevantSections(reference.document.document, sections);
            displaySemanticsComments(reference.semantics, sections);
        }
    }

    function isValidReference(chapterAndSection) {
        /*
        section must be a valid value and consist of a chapter index
        and at least one section id
         */
        return chapterAndSection && chapterAndSection.length >= 2;
    }

    function mapChapterToCurrentRevision(revisionTag, chapter) {
        return (revisionTag === currentRevisionTag) ?
            chapter : chapterMapping[revisionTag.toLowerCase()][chapter];
    }


    highlightReferencedSections();
}());
