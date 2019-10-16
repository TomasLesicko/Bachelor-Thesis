'use strict';

// (function() {
// temporary test references, references JSON will likely need to be online, accessing local files
// in JavaScript is apparently very difficult for security reasons


// var references = [
//         {
//             "document": { "document": "n4140", "section": "14.3:3.1" },
//             "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "222" }
//         },
//         {
//             "document": { "document": "n4140", "section": "14.3:3.3" },
//             "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "229" },
//         },
//     {
//         "document": { "document": "n4140", "section": "13.1:4.1" },
//         "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "222" }
//     },
//     {
//         "document": { "document": "n4140", "section": "30.10:3" },
//         "semantics": { "file": "semantics/cpp/language/execution/stmt/try.k", "line": "222" }
//     }];

var sectionNamesDict = {};

var addPair = function(k, v) {
        sectionNamesDict[k] = v;
};

var storeRefsAndNames = function(names) {
        //sessionStorage.setItem('references', JSON.stringify(refs));
        sessionStorage.setItem('dictionary', JSON.stringify(names));
};


// var processRefs = function() {
//         $.get("../section_names.txt", function(data) {
//             var array = data.split('\n');
//
//             for(var i = 0; i < array.length; i++) {
//                 var keyValuePair = array[i].split(" ");
//
//                 addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
//             }
//
//             storeRefsAndNames(references, sectionNamesDict);
//         });
// };

// var processRefs = function() {
//
//     sectionNamesDict[13.3] = "except.handle";
//
//     // $.get("../section_names.txt", function(data) {
//     //     aa = data;
//     //     array = data.split('\n');
//     // });
//
//     for(var i = 0; i < array.length; i++) {
//         var keyValuePair = array[i].split(" ");
//
//         addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
//     }
//     storeRefsAndNames(references, sectionNamesDict);
//
// };

var processRefs = function() {

    //var array1 = ["a"];

    // $.get("/home/tomas/WebstormProjects/test2/section_names.txt", function(data) {
    // // $.get("../section_names.txt", function(data) {
    //     array = data.split('\n');
    // });
    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/references.json', function(data) {
        sessionStorage.setItem('references', data);
    });

    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/references/section_names_n4820.txt', function(data) {
        var array1 = data.split('\n');

        for(var i = 0; i < array1.length; i++) {
            var keyValuePair = array1[i].split(" ");

            addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
        }
        storeRefsAndNames(sectionNamesDict);
    });

    jQuery.get('https://raw.githubusercontent.com/TomasLesicko/Bachelor-Thesis/master/project/section_mapping/section_mapping_to_n4820.json', function(data) {
        sessionStorage.setItem('mapping', data);
    });


    // for(var i = 0; i < array.length; i++) {
    //     var keyValuePair = array[i].split(" ");
    //
    //     addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
    // }
    // storeRefsAndNames(references, sectionNamesDict);
};


var debugPlaceholder = 4;
    // var processRefs = function() {
    //     $.get("../section_names.txt", function(data) {
    //         var array = data.split('\n');
    //
    //         for(var i = 0; i < array.length; i++) {
    //             var keyValuePair = array[i].split(" ");
    //
    //             addPair(keyValuePair[0].slice(0, -1), keyValuePair[1]);
    //         }
    //
    //         $.get("../referencesTest.json", function(data2) {
    //             storeRefsAndNames(data2, sectionNamesDict);
    //         });
    //
    //     });
    // };

//}());