#include <experimental/filesystem>
#include <fstream>
#include <optional>
#include <regex>
#include <stdexcept>
#include <string>
#include <vector>
#include <iostream>

namespace fs = std::experimental::filesystem;


struct Lines {
    int from;
    int to;
};


std::ostream & operator<<(std::ostream &o, std::vector<Lines> const &lines) {
    bool first = true;
    for(Lines l : lines) {
        if(!first)
            o << ", ";
        o << R"({ "from": ")" << l.from;
        o << R"(", "to": ")" << l.to << R"(" })";
        first = false;
    }

    return o;
}


std::ostream & operator<<(std::ostream &o, Lines const &lines) {
        o << R"({ "from": ")" << lines.from;
        o << R"(", "to": ")" << lines.to << R"(" })";

        return o;
}


struct FileContext {
	std::string fileName;
	std::vector<Lines> lineNumbers;
};


std::ostream & operator<<(std::ostream &o, FileContext const &fc) {
	o << R"({ "file": ")" << fc.fileName;
	o << R"(", "lines": ")" << /*fc.lineNumber*/fc.lineNumbers << "\" }";
	return o;
}

struct DocumentRef {
	std::string document;
	std::string section;
	bool isTodo;
};


std::ostream & operator<<(std::ostream &o, DocumentRef const &ref) {
	o << R"({ "document": ")" << ref.document << '"';
	o << R"(, "section": ")" << ref.section << "\"";
	o << R"(, "TODO": ")" << std::boolalpha << ref.isTodo << "\" }";
	return o;
}


struct Entry {
	FileContext fileContext;
	DocumentRef documentRef;
};


std::ostream & operator<<(std::ostream &o, Entry const &entry) {
	o << "{\n    \"document\": " << entry.documentRef << ",\n";
	o << "    \"semantics\": " << entry.fileContext << "\n  }";
	return o;
}


using Entries = std::vector<Entry>;

std::ostream & operator<<(std::ostream &o, Entries const &entries) {
	if (entries.empty()) {
		o << "[]";
		return o;
	}

	o << "[\n";
	for (size_t i = 0; i < entries.size(); i++) {
		o << "  " << entries[i];
		if (i < entries.size() - 1)
			o << ",\n";
	}
	o << "\n]\n";

	return o;
}


std::vector<std::string> splitRefSections(const std::string& s) {
    std::vector<std::string> sections;

    static const std::regex regex(R"((.*)([:\/])([\d\.]+)*(\d+)(?:-([\d\.]+)*(\d+))?)");
    std::smatch result;
    if (std::regex_search(s, result, regex)) {
        // example 1.2:3.1-3.4
        std::string chapter = result[1]; // 1.2
        std::string delim = result[2]; // :
        std::string paragraphFromPrefix = result[3]; // 3.
        std::string paragraphFrom = result[4]; // 1
        std::string paragraphToPrefix = result[5]; // 3.
        std::string paragraphTo = result[6]; // 4

        int from = std::stoi(paragraphFrom);
        int to = paragraphTo.empty() ? from : std::stoi(paragraphTo);
        for (; from <= to; ++from) {
            std::string section;
            section.append(chapter).append(delim).append(paragraphFromPrefix).append(std::to_string(from));
            sections.emplace_back(section);
        }
    }

    return sections;
}


void splitRefTags(const std::smatch& result, std::vector<DocumentRef>& refs) {
    std::vector<std::string> sections = splitRefSections(result[4]);
    for (const std::string& section : sections) {
        if (result[2] != "") {
            refs.emplace_back(DocumentRef{result[2], section, result[1] != ""});
        }
        refs.emplace_back(DocumentRef{result[3], section, result[1] != ""});
    }
}


std::vector<DocumentRef> refsFromLine(const std::string& line) {
    static const std::regex regex(R"((TODO)?(?:\S*)? (?:@ref )?(N\d{4})?(?:-)?(N\d{4}) ([A-Z0-9][\.\d]*[:\/][\d-\.]+))",
                                  std::regex_constants::icase);
    std::vector<DocumentRef> refs;

/*
 * Capture groups
 * 1 "TODO" - if not empty, reference was marked as TODO
 * 2 Secondary tag revision group - if not empty, 2 revision tags in reference
 * 3 Primary tag revision group - can not be empty
 * 4 Section group - can not be empty
 */
    std::smatch result;
    auto start = line.cbegin();
    while (std::regex_search(start, line.cend(), result, regex)) {
        splitRefTags(result, refs);
        start = result.suffix().first;
    }

    return refs;
}


bool lineContainsComment(const std::string& line) {
    static const std::regex regex(R"(//)");
    std::smatch result;
    return std::regex_search(line, result, regex);
}


void print(std::optional<DocumentRef> ref) {
	if (ref)
		std::cout << ref.value();
	else
		std::cout << "empty";
}


void addRefsToEntries(std::vector<Entry>& refs, Entries& entries) {
    auto it = std::next(refs.begin(), refs.size());
    std::move(refs.begin(), it, std::back_inserter(entries));
    refs.erase(refs.begin(), it);
}


void processLineReferences(std::vector<Entry>& commentBlockRefs, Entries& entries,
        const std::string& path, int lineNumber, std::vector<DocumentRef>& refs) {
    for (auto& ref : refs) {
        commentBlockRefs.push_back(Entry{FileContext{path, {Lines{lineNumber, lineNumber}}},
                                         std::move(ref)});
    }
}


bool previousLineIsComment(const std::vector<Entry>& commentBlockRefs, int lineNumber) {
    return commentBlockRefs.back().fileContext.lineNumbers.back().to + 1 != lineNumber;
}


void updateCommentBlockRefLines(std::vector<Entry>& commentBlockRefs, int lineNumber) {
    if (!commentBlockRefs.empty()) {
        if (previousLineIsComment(commentBlockRefs, lineNumber)) {
            std::for_each(commentBlockRefs.begin(), commentBlockRefs.end(), [&lineNumber](Entry& e) {
                e.fileContext.lineNumbers.emplace_back(Lines{lineNumber, lineNumber});
            });
        }
        else {
            std::for_each(commentBlockRefs.begin(), commentBlockRefs.end(), [&lineNumber](Entry& e) {
                e.fileContext.lineNumbers.back().to = lineNumber;
            });
        }
    }
}


void processCommentLine(const std::string& line, std::vector<Entry>& commentBlockRefs,
        Entries& entries, const std::string& path, int lineNumber) {
    std::vector<DocumentRef> refs = refsFromLine(line);
    if (!refs.empty()) {
        processLineReferences(commentBlockRefs, entries, path, lineNumber, refs);
    }
    else {
        updateCommentBlockRefLines(commentBlockRefs, lineNumber);
    }
}


void processNonCommentLine(const std::string& line, std::vector<Entry>& commentBlockRefs, Entries & entries) {
    ;
}


bool lineIsWhiteSpace(const std::string& line) {
    for (int c : line) {
        if (!isspace(c)) {
            return false;
        }
    }

    return true;
}


// assumes there's always a space between comment blocks and commentblocks start
// with a reference
void addEntriesFromIstream(Entries & entries, const std::string& path, std::istream & is) {
    int lineNumber = 1;
    std::vector<Entry> commentBlockRefs;

    std::string line;

    while(std::getline(is, line)) {
        if (lineIsWhiteSpace(line)) {
            addRefsToEntries(commentBlockRefs, entries);
        }
        else if(lineContainsComment(line)) {
            processCommentLine(line, commentBlockRefs, entries, path, lineNumber);
        }
        else {
            processNonCommentLine(line, commentBlockRefs, entries);
        }
        ++lineNumber;
    }

    addRefsToEntries(commentBlockRefs, entries);
}


// expects "// @ref[...]" format
bool isReference(const std::string& comment) {
    return comment.substr(0, 4) == "@ref";
}


void addEntry(Entries & entries, FileContext & fc, DocumentRef & dr) {
    entries.push_back(Entry{fc, dr});
}


DocumentRef createRef(const std::string& comment) {
    static const std::regex regex(R"(@ref (\S+) (\S+))");
    std::smatch result;
    if (std::regex_search(comment, result, regex)) {
        return DocumentRef{result[1], result[2]};
    }

    return {};
}


void addEntriesFromRegularFile(Entries & entries, const fs::path& filepath) {
	// Ignore files not matching '*.k'
	if (filepath.extension() != ".k" && filepath.extension() != ".C")
		return;

	std::ifstream is(filepath);
	if (!is.is_open())
		throw std::runtime_error(std::string("Cannot read file: ") + filepath.string());
	addEntriesFromIstream(entries, filepath.string(), is);
}


void addEntriesFromDirectory(Entries & entries, const fs::path& dirpath) {
	for(auto& current: fs::recursive_directory_iterator(dirpath)) {
		addEntriesFromRegularFile(entries, current);
	}
}


void addEntriesFromPath(Entries & entries, const fs::path& p) {
	if (fs::is_regular_file(p))
		return addEntriesFromRegularFile(entries, p);

	if (fs::is_directory(p))
		return addEntriesFromDirectory(entries, p);
}


Entries entriesFromPath(const fs::path& path) {
	Entries entries;
	addEntriesFromPath(entries, path);
	return entries;
}


int main(int argc, char *argv[]) {
	if (argc != 2) {
		std::cerr << "Usage: " << argv[0] << " <path>\n";
		return 1;
	}
	try {
	    std::ofstream  references ("references.json");
		references << entriesFromPath(argv[1]);
	} catch (std::exception const &e) {
		std::cerr << "Error: " << e.what() << '\n';
	}
}