// need to get rid of these global variables
var dictionaryStr = localStorage.getItem('dictionary');
var referencesStr = localStorage.getItem('references');
var dictionary = JSON.parse(dictionaryStr);
var references = JSON.parse(referencesStr);

var colorReferencedBlocks = function() {
    for(var i = 0; i < references.length; i++) {
            var sectionInfo = references[i].document.section.split(':');

            var HTMLpage = dictionary[sectionInfo[0]]+".html";
            var thisPage = location.pathname.split("/").slice(-1);

            if(HTMLpage === thisPage[0]) {
                document.getElementById(sectionInfo[1]).style.backgroundColor = "green";
            }
    }
};
