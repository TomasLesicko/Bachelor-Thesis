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
	//int lineNumber;
	//std::vector<Lines> lineNumbers;
	Lines lineNumbers;
};

std::ostream & operator<<(std::ostream &o, FileContext const &fc) {
	o << "{ \"file\": \"" << fc.fileName;
	o << "\", \"lines\": \"" << /*fc.lineNumber*/fc.lineNumbers << "\" }";
	return o;
}

struct DocumentRef {
	std::string document;
	std::string section;
};

std::ostream & operator<<(std::ostream &o, DocumentRef const &ref) {
	o << "{ \"document\": \"" << ref.document << '"';
	o << ", \"section\": \"" << ref.section << "\" }";
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


std::optional<DocumentRef> refFromLine(std::string line) {
//    static const std::regex regex(R"(@ref (\S+) (\S+))");
//should support everything except  // @ref N4926 1.2:3, N4800 3.4/5, ...
// this regex could support above, but needs more changes in the way refs are stored
// ((^| )(TODO\S*|@ref))+ (N[^\s,]+) ([^\s,]+)(, ([^\s,]+) ([^\s,]+))*
// case insensitive to support TODO|todo n4296|N4296
    static const std::regex regex(R"(((^| )(TODO\S*|@ref))+ (N\S+) (\S+))",
            std::regex_constants::icase);
    std::smatch result;
    if (std::regex_search(line, result, regex)) {
        // this never happens with 2 group regex, it just won't match
        // can refs even be in this format?
        if (result.size() == 2)
            return {DocumentRef{result[1], ""}};
        if (result.size() == 6)
            return {DocumentRef{result[4], result[5]}};
    }
    return {};
}

bool lineContainsComment(std::string line) {
    static const std::regex regex(R"(//)");
    std::smatch result;
    return std::regex_search(line, result, regex);
}

//std::optional<DocumentRef> refFromLine(std::string line) {
//    static const std::regex regex(R"(@ref (\S+) (\S+))");
//    std::smatch result;
//    if (std::regex_search(line, result, regex)) {
//        if (result.size() == 2)
//            return {DocumentRef{result[1], ""}};
//        if (result.size() == 3)
//            return {DocumentRef{result[1], result[2]}};
//    }
//    return {};
//}

void print(std::optional<DocumentRef> ref) {
	if (ref)
		std::cout << ref.value();
	else
		std::cout << "empty";
}


//void addEntriesFromIstream(Entries & entries, std::string path, std::istream & is) {
//	FileContext fc {path, 1};
//	std::string line;
//	while(std::getline(is, line)) {
//		//std::cout << lineNumber << ": " << line << '\n';
//		std::optional<DocumentRef> ref = refFromLine(line);
//		//print(ref);
//		//std::cout << '\n';
//		if (ref)
//			entries.push_back(Entry{fc, std::move(ref.value())});
//
//		fc.lineNumber++;
//	}
//};

void addEntriesFromIstream(Entries & entries, std::string path, std::istream & is) {
	FileContext fc {path, {1, 1}};
	int lineNumber = 1;
	std::string line;
	bool commentBlock = false;

	while(std::getline(is, line)) {
		std::optional<DocumentRef> ref = refFromLine(line);
		if (ref) {
		    fc.lineNumbers.from = lineNumber;
		    fc.lineNumbers.to = lineNumber;
            entries.push_back(Entry{fc, std::move(ref.value())});
            commentBlock = true;
		}
		else if(lineContainsComment(line) && commentBlock) {
		    if(!entries.empty()) {
                entries.back().fileContext.lineNumbers.to++;
		    }
		    else {
		        std::cerr << "Error, in a commentBlock with empty entries\n";
		    }
		}
		else {
		    commentBlock = false;
		}

		lineNumber++;
	}
};

// expects "// @ref[...]" format
bool isReference(std::string comment) {
    return comment.substr(0, 4) == "@ref";
}

void addEntry(Entries & entries, FileContext & fc, DocumentRef & dr) {
    entries.push_back(Entry{fc, dr});
}

DocumentRef createRef(std::string comment) {
    static const std::regex regex(R"(@ref (\S+) (\S+))");
    std::smatch result;
    if (std::regex_search(comment, result, regex)) {
        return DocumentRef{result[1], result[2]};
    }

    return {};
}


void addEntriesFromRegularFile(Entries & entries, fs::path filepath) {
	// Ignore files not matching '*.k'
	if (filepath.extension() != ".k" && filepath.extension() != ".C")
		return;

	std::ifstream is(filepath);
	if (!is.is_open())
		throw std::runtime_error(std::string("Cannot read file: ") + filepath.string());
	addEntriesFromIstream(entries, filepath.string(), is);
}

void addEntriesFromDirectory(Entries & entries, fs::path dirpath) {
	for(auto& current: fs::recursive_directory_iterator(dirpath)) {
		addEntriesFromRegularFile(entries, current);
	}

}


void addEntriesFromPath(Entries & entries, fs::path p) {
	if (fs::is_regular_file(p))
		return addEntriesFromRegularFile(entries, p);

	if (fs::is_directory(p))
		return addEntriesFromDirectory(entries, p);
}

Entries entriesFromPath(fs::path path) {
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
		std::cout << entriesFromPath(argv[1]);
	} catch (std::exception const &e) {
		std::cerr << "Error: " << e.what() << '\n';
	}
}