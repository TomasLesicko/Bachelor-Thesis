'use strict';

(function() {
// temporary test references, references JSON will likely need to be online, accessing local files
// in JavaScript is apparently very difficult for security reasons
    var references = [
        {
            "document": { "document": "n4140", "section": "13.3:3.1" },
            "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "222" }
        },
        {
            "document": { "document": "n4140", "section": "13.3:3.2" },
            "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "229" }
        }];

    var sectionNamesDict = {};

    var addPair = function(k, v) {
        sectionNamesDict[k] = v;
    };

    var storeRefsAndNames = function(refs, names) {
        localStorage.setItem('references', JSON.stringify(refs));
        localStorage.setItem('sectionNamesDict', JSON.stringify(names));
    };

    var processRefs = function() {
        $.get("../section_names.txt", function(data) {
            var array = data.split('\n');

            for(var i = 0; i < array.length; i++) {
                var keyValuePair = array[i].split(" ");

                addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
            }

            storeRefsAndNames(references, sectionNamesDict);
        });
    };


}());